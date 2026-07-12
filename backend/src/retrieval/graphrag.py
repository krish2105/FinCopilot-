"""GraphRAG relationship route (Phase 4).

Answers relationship/multi-hop-over-entities questions ("which companies share
this risk?", "what risks do AAPL and MSFT have in common?") by traversing the
entity graph, then hydrating the backing chunks from the store so the answer is
cited exactly like every other route.
"""

from __future__ import annotations

import logging

from src.retrieval.citations import assign_citations
from src.retrieval.graph import EntityGraph
from src.retrieval.store import VectorStore
from src.retrieval.types import RetrievalResult, RetrievedChunk

logger = logging.getLogger(__name__)

# Tickers mentioned by name in a query -> resolve via the graph's company set.
_NAME_TO_TICKER = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "tesla": "TSLA",
    "jpmorgan": "JPM",
    "nvidia": "NVDA",
    "meta": "META",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "emaar": "EMAAR.AE",
}


def _tickers_in_query(query: str, graph: EntityGraph) -> list[str]:
    q = query.lower()
    found = []
    companies = set(graph.companies())
    for name, tk in _NAME_TO_TICKER.items():
        if name in q and tk in companies:
            found.append(tk)
    for tk in companies:
        if tk.lower() in q and tk not in found:
            found.append(tk)
    return found


def graphrag_retrieve(
    graph: EntityGraph,
    store: VectorStore,
    query: str,
    tickers: list[str] | None = None,
    top_k: int = 8,
) -> RetrievalResult:
    risks = graph.match_risk(query)
    mentioned = _tickers_in_query(query, graph)
    scope = tickers or (mentioned or None)

    evidence_ids: list[str] = []
    summary_parts: list[str] = []
    wants_subsidiaries = "subsidiar" in query.lower()

    if wants_subsidiaries and mentioned:
        # "what subsidiaries does X have?" -> Exhibit 21 traversal.
        c = mentioned[0]
        subs = graph.subsidiaries_of(c)
        shown = subs[:25]
        more = f" (+{len(subs) - len(shown)} more)" if len(subs) > len(shown) else ""
        summary_parts.append(
            f"{c} subsidiaries: {', '.join(shown) or 'none found in Exhibit 21'}{more}."
        )
        evidence_ids += [e["chunk_id"] for e in graph.relation_evidence(c, "has_subsidiary")]
    elif len(mentioned) >= 2:
        # "what do A and B have in common" -> shared risks between two companies.
        a, b = mentioned[0], mentioned[1]
        shared = graph.shared_risks(a, b)
        summary_parts.append(
            f"{a} and {b} share these disclosed risks: {', '.join(shared) or 'none found'}."
        )
        for topic in shared:
            for company in (a, b):
                evidence_ids += [e["chunk_id"] for e in graph.edge_evidence(company, topic)]
    elif risks:
        # "which companies share this risk?" -> companies connected to the risk node.
        for topic in risks:
            companies = graph.companies_facing_risk(topic, tickers=scope)
            summary_parts.append(
                f"Companies disclosing {topic} risk: {', '.join(companies) or 'none found'}."
            )
            for company in companies:
                evidence_ids += [e["chunk_id"] for e in graph.edge_evidence(company, topic)]
    elif mentioned:
        # single company -> enumerate its risks.
        c = mentioned[0]
        c_risks = graph.risks_for_company(c)
        summary_parts.append(f"{c} discloses these risks: {', '.join(c_risks) or 'none found'}.")
        for topic in c_risks:
            evidence_ids += [e["chunk_id"] for e in graph.edge_evidence(c, topic)]

    chunks = _hydrate(store, evidence_ids, top_k)
    citations = assign_citations(chunks)
    answer = " ".join(summary_parts) if summary_parts else ""
    if chunks and answer:
        answer += " " + " ".join(c.marker for c in chunks[: min(3, len(chunks))])

    logger.info("graphrag | risks=%s | tickers=%s | evidence=%d", risks, mentioned, len(chunks))
    return RetrievalResult(
        query=query,
        route="graphrag",
        chunks=chunks,
        citations=citations,
        answer=answer or "No graph relationships matched this query.",
        reranker="graph-traversal",
        embed_backend="graph",
    )


def _hydrate(store: VectorStore, ids: list[str], top_k: int) -> list[RetrievedChunk]:
    # Preserve first-seen order, dedupe, cap at top_k.
    seen: set[str] = set()
    ordered: list[str] = []
    for cid in ids:
        if cid not in seen:
            seen.add(cid)
            ordered.append(cid)
    ordered = ordered[:top_k]
    by_id = {c.chunk_id: c for c in store.get_by_ids(ordered)}
    out: list[RetrievedChunk] = []
    for cid in ordered:
        c = by_id.get(cid)
        if c is None:
            continue
        out.append(RetrievedChunk(chunk_id=c.chunk_id, text=c.text, metadata=c.metadata))
    return out

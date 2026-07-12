"""NetworkX entity graph for GraphRAG (Phase 4).

Built deterministically from the ingested corpus so it works offline and never
hallucinates relationships. Node kinds:
  * company   — one per ticker
  * risk      — a normalized risk topic (supply chain, FX, competition, ...)
  * executive — named officers detected in filings (best-effort)
Edges:
  * company -[FACES]-> risk   (evidence: the chunk that mentions it)
  * company -[HAS_OFFICER]-> executive
  * subsidiary — a subsidiary parsed from the 10-K Exhibit 21 (source
    "subsidiaries"): company -[HAS_SUBSIDIARY]-> subsidiary
Two companies "share" a risk iff they both connect to the same risk node — the
relationship the GraphRAG route traverses. Every edge stores enough metadata
(chunk_id, ticker, doc_type, page, section, source_url) to build a citation.
"""

from __future__ import annotations

import json
import logging
import os
import re

import networkx as nx

from src.config.settings import get_settings
from src.retrieval.store import VectorStore

logger = logging.getLogger(__name__)

# Risk topic -> trigger phrases. Order-independent; a chunk can hit several.
RISK_TAXONOMY: dict[str, list[str]] = {
    "supply chain": ["supply chain", "supplier", "component shortage", "logistics"],
    "foreign exchange": [
        "foreign exchange",
        "foreign currency",
        "currency fluctuation",
        "exchange rate",
    ],
    "competition": ["competition", "competitive", "competitor"],
    "cybersecurity": [
        "cybersecurity",
        "cyber",
        "security breach",
        "data breach",
        "information security",
    ],
    "litigation": ["litigation", "lawsuit", "legal proceeding"],
    "interest rate": ["interest rate"],
    "regulatory": ["regulation", "regulatory", "antitrust", "compliance requirement"],
    "intellectual property": ["intellectual property", "patent", "infringement"],
    "macroeconomic": ["macroeconomic", "economic conditions", "recession", "inflation"],
    "climate": ["climate", "environmental regulation"],
    "tax": ["tax rate", "taxation", "effective tax"],
    "concentration": ["concentration of", "single supplier", "limited sources"],
}

_OFFICER_RE = re.compile(
    r"([A-Z][a-z]+(?:\s[A-Z]\.)?\s[A-Z][a-z]+),?\s+"
    r"(?:the\s+)?(?:Company'?s?\s+)?(Chief\s+\w+\s+Officer|President|CEO|CFO|COO)"
)


def _risk_id(topic: str) -> str:
    return f"risk:{topic}"


def _exec_id(name: str) -> str:
    return f"exec:{name}"


def _sub_id(name: str) -> str:
    return f"sub:{name.lower()}"


class EntityGraph:
    def __init__(self, graph: nx.MultiDiGraph | None = None):
        self.g = graph if graph is not None else nx.MultiDiGraph()

    # --- build ---
    @classmethod
    def build(cls, store: VectorStore, path: str | None = None) -> EntityGraph:
        eg = cls()
        for chunk in store.iter_all():
            eg._ingest_chunk(chunk)
        if path:
            eg.save(path)
        logger.info(
            "EntityGraph built: %d nodes, %d edges", eg.g.number_of_nodes(), eg.g.number_of_edges()
        )
        return eg

    def _ingest_chunk(self, chunk) -> None:
        m = chunk.metadata
        ticker = m.ticker
        if not self.g.has_node(ticker):
            self.g.add_node(ticker, kind="company", label=ticker)
        text_low = " ".join(chunk.text.split()).lower()
        evidence = {
            "chunk_id": chunk.chunk_id,
            "ticker": ticker,
            "doc_type": str(m.doc_type),
            "page": m.page,
            "section": m.section,
            "source_url": m.source_url,
        }

        for topic, phrases in RISK_TAXONOMY.items():
            if any(p in text_low for p in phrases):
                rid = _risk_id(topic)
                if not self.g.has_node(rid):
                    self.g.add_node(rid, kind="risk", label=topic)
                self.g.add_edge(ticker, rid, relation="faces", **evidence)

        for match in _OFFICER_RE.finditer(chunk.text):
            name = match.group(1).strip()
            eid = _exec_id(name)
            if not self.g.has_node(eid):
                self.g.add_node(eid, kind="executive", label=name)
            self.g.add_edge(ticker, eid, relation="has_officer", **evidence)

        # Exhibit 21 -> subsidiary nodes (company -[has_subsidiary]-> subsidiary).
        if str(m.doc_type) == "subsidiaries":
            from src.retrieval.subsidiaries import parse_subsidiaries

            for name in parse_subsidiaries(chunk.text):
                sid = _sub_id(name)
                if not self.g.has_node(sid):
                    self.g.add_node(sid, kind="subsidiary", label=name)
                self.g.add_edge(ticker, sid, relation="has_subsidiary", **evidence)

    # --- persistence ---
    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        data = nx.node_link_data(self.g, edges="links")
        with open(path, "w") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: str) -> EntityGraph | None:
        if not os.path.exists(path):
            return None
        with open(path) as f:
            data = json.load(f)
        return cls(nx.node_link_graph(data, multigraph=True, directed=True, edges="links"))

    # --- queries ---
    def companies(self) -> list[str]:
        return [n for n, d in self.g.nodes(data=True) if d.get("kind") == "company"]

    def risk_topics(self) -> list[str]:
        return [d["label"] for _, d in self.g.nodes(data=True) if d.get("kind") == "risk"]

    def match_risk(self, query: str) -> list[str]:
        """Risk topics referenced by the query text (by trigger phrase or label)."""
        q = query.lower()
        hits = []
        for topic, phrases in RISK_TAXONOMY.items():
            if topic in q or any(p in q for p in phrases):
                hits.append(topic)
        return hits

    def companies_facing_risk(self, topic: str, tickers: list[str] | None = None) -> list[str]:
        rid = _risk_id(topic)
        if not self.g.has_node(rid):
            return []
        allowed = {t.upper() for t in tickers} if tickers else None
        out = []
        for company in self.g.predecessors(rid):
            if allowed is None or company.upper() in allowed:
                out.append(company)
        return sorted(out)

    def risks_for_company(self, ticker: str) -> list[str]:
        if not self.g.has_node(ticker):
            return []
        out = []
        for _, target, data in self.g.out_edges(ticker, data=True):
            if data.get("relation") == "faces":
                out.append(self.g.nodes[target]["label"])
        return sorted(set(out))

    def shared_risks(self, ticker_a: str, ticker_b: str) -> list[str]:
        return sorted(set(self.risks_for_company(ticker_a)) & set(self.risks_for_company(ticker_b)))

    def subsidiaries_of(self, ticker: str) -> list[str]:
        if not self.g.has_node(ticker):
            return []
        out = [
            self.g.nodes[t]["label"]
            for _, t, data in self.g.out_edges(ticker, data=True)
            if data.get("relation") == "has_subsidiary"
        ]
        return sorted(set(out))

    def edge_evidence(self, company: str, topic: str) -> list[dict]:
        rid = _risk_id(topic)
        if not (self.g.has_node(company) and self.g.has_node(rid)):
            return []
        out = []
        # MultiDiGraph: iterate the parallel edges between company -> rid.
        if self.g.has_edge(company, rid):
            for _key, data in self.g.get_edge_data(company, rid).items():
                out.append({k: v for k, v in data.items() if k != "relation"})
        return out

    def relation_evidence(self, ticker: str, relation: str) -> list[dict]:
        if not self.g.has_node(ticker):
            return []
        out = []
        for _, _, data in self.g.out_edges(ticker, data=True):
            if data.get("relation") == relation:
                out.append({k: v for k, v in data.items() if k != "relation"})
        return out

    def stats(self) -> dict:
        kinds: dict[str, int] = {}
        for _, d in self.g.nodes(data=True):
            kinds[d.get("kind", "?")] = kinds.get(d.get("kind", "?"), 0) + 1
        return {
            "nodes": self.g.number_of_nodes(),
            "edges": self.g.number_of_edges(),
            "by_kind": kinds,
            "risk_topics": self.risk_topics(),
        }


def graph_path() -> str:
    return os.path.join(get_settings().data_dir, "entity_graph.json")

# Architecture

## Diagram

```mermaid
flowchart TD
    U["User query — Next.js workspace (SSE streaming)"] --> ORCH["Orchestrator · LangGraph state machine"]
    ORCH --> CLS{"Complexity classifier — pick RAG route"}
    CLS -->|simple factual| HS["Hybrid search — dense pgvector + BM25 · RRF → cross-encoder rerank"]
    CLS -->|multi-hop| AG["Agentic ReAct loop — query decomposition ≤3 iters"]
    CLS -->|relationship| GR["GraphRAG — NetworkX entity graph"]
    HS --> AGENTS
    AG --> AGENTS
    GR --> AGENTS
    subgraph AGENTS["Specialist agents"]
        direction LR
        R["Researcher"] --> A["Analyst — figures from retrieved evidence only + exact calculator"] --> C["Compliance — flags + can veto"] --> V["Visualization"]
    end
    AGENTS --> GATE{"Self-RAG faithfulness gate — every claim grounded? numbers cited? math correct?"}
    GATE -->|grounded| ANS["Cited answer + charts + provider trace"]
    GATE -->|unsupported| REF["'Insufficient evidence' — honest refusal"]
    ANS --> AUD["Audit log — query · route · sources · provider · latency · cost · verdict"]
    REF --> AUD

    CORP[("Ingestion — real SEC EDGAR + market + news → Contextual Retrieval chunks → pgvector + BM25")] -.grounds.-> HS
    CORP -.builds.-> GR
    LLM["Provider router — Gemini 2.5 → Groq Llama 3.3 → offline stub"] -.powers.-> AGENTS
```

## Request lifecycle

1. **User query** arrives from the Next.js workspace (streaming chat).
2. **Orchestrator** (LangGraph state machine) classifies intent + complexity and picks
   a RAG route.
3. **Adaptive RAG router:**
   - *simple factual* → hybrid search (dense pgvector + BM25) → cross-encoder rerank
   - *multi-hop* → agentic ReAct retrieval loop, capped at 3 iterations, logged
   - *relationship* → GraphRAG over the entity graph
4. **Specialist agents:**
   - **Researcher** — sub-queries, retrieve + rank evidence, attach source metadata
     (ticker, filing type, date, page).
   - **Analyst** — ratios/growth/trends from *retrieved figures only*, citing each
     input line; refuses if a required figure wasn't retrieved.
   - **Compliance** — flags risk-factor / going-concern / restatement / litigation
     language; validates the Analyst's claims; can veto to refusal.
   - **Visualization** — charts/tables from validated figures only.
5. **Self-RAG faithfulness gate** — every claim must be supported by cited context;
   unsupported answers become "insufficient evidence" + what's missing.
6. **Audit log** — query, route, sources, LLM provider used, latency, cost, verdict.

## Component map

| Concern | Module (backend/src) |
| --- | --- |
| Fetch/parse/chunk/embed | `ingestion/` |
| Hybrid search, reranker, GraphRAG, router | `retrieval/` |
| Orchestrator + specialist agents | `agents/` |
| LLM provider fallback router | `providers/` |
| RAGAS harness | `evaluation/` |
| FastAPI app + routes | `api/` |
| Settings + prompts | `config/` |

## Design principle

Complexity is a cost, not a virtue — route the easy ~80% cheaply, reserve
agentic/graph power for the hard ~20%.

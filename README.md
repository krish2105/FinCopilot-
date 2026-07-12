# FinCopilot — Agentic Financial Analyst Copilot

> A multi-agent, adaptive-RAG financial research copilot. A team of specialist AI
> agents reads **real** SEC filings, computes the analysis, checks compliance, and
> returns a **fully cited** answer — or honestly says **"insufficient evidence."**
> Built entirely on free-tier infrastructure.

[![CI](https://github.com/krish2105/FinCopilot-/actions/workflows/ci.yml/badge.svg)](https://github.com/krish2105/FinCopilot-/actions/workflows/ci.yml)

<!-- After deploying (see scripts/deploy.md), replace the two placeholders below. -->
**Live demo:** `https://<your-app>.vercel.app` · **API:** `https://<your-api>.onrender.com`

> Deploy is one-blueprint-per-service and fully wired: **Vercel** (frontend) +
> **Render** (`render.yaml`) + **Supabase** (pgvector). Step-by-step:
> [scripts/deploy.md](scripts/deploy.md).

---

## Why this exists

Analysts waste hours reading 100-page filings to answer questions that repeat every
quarter, and generic LLM chatbots hallucinate numbers — fatal in finance. FinCopilot
orchestrates specialist agents (Researcher, Analyst, Compliance, Visualization) over
an adaptive RAG stack. Every number traces to a real filing; unsupported claims are
refused, not guessed.

## Architecture (at a glance)

```
User query ──► Orchestrator ──► Adaptive RAG router
                                  ├─ simple factual  → hybrid search + reranker
                                  ├─ multi-hop       → agentic ReAct loop (≤3 iters)
                                  └─ relationship    → GraphRAG (entity graph)
             Researcher · Analyst · Compliance · Visualization
                                  │
                     Self-RAG faithfulness gate ──► cited answer  OR  "insufficient evidence"
                                  │
                            Audit log (query · route · sources · provider · verdict)
```

See [docs/architecture.md](docs/architecture.md), [DECISIONS.md](DECISIONS.md), and
[DATA_SOURCES.md](DATA_SOURCES.md).

## Stack (all free tier)

| Layer | Choice |
| --- | --- |
| LLM | Gemini 2.5 Flash-Lite → Flash → Groq Llama 3.3 70B → Groq GPT-OSS 120B (fallback chain) |
| Embeddings | `gemini-embedding-001` + local `bge-small-en-v1.5` fallback |
| Vector DB | Supabase Postgres + pgvector |
| Lexical / rerank | `rank_bm25` + local `ms-marco-MiniLM-L-6-v2` cross-encoder |
| Graph | NetworkX (MVP) → Neo4j AuraDB Free (stretch) |
| Orchestration | LangGraph · FastAPI · Pydantic |
| Frontend | Next.js 14 · Tailwind · shadcn/ui · Recharts |
| Auth | Supabase Auth (email + Google OAuth, row-level security) |
| Hosting | Vercel (frontend) · Render (backend) · Supabase (DB) |

## Quick start (local)

```bash
cp .env.example .env      # fill in free-tier keys
docker compose up         # backend + frontend

# Ingest real filings/market/news (runs fully offline with local embeddings):
cd backend
python -m src.ingestion.run --tickers AAPL MSFT --offline
# then inspect what's searchable:
curl localhost:8000/corpus/stats
```

The ingestion pipeline (`backend/src/ingestion`) fetches **real** SEC EDGAR
filings + yfinance fundamentals + GDELT news, parses them with page/section
tracking, chunks structure-aware (tables kept intact), embeds, and writes to the
vector store (Supabase pgvector, or a local SQLite store when no `DATABASE_URL`)
plus a BM25 index. It is idempotent — re-running an unchanged corpus embeds
nothing new.

The retrieval layer (`backend/src/retrieval`) then answers queries via
**hybrid search** (dense pgvector + BM25, fused with Reciprocal Rank Fusion) → a
local **cross-encoder reranker** (`ms-marco-MiniLM-L-6-v2`, with a deterministic
lexical fallback offline) → **citation formatting**, returning ranked evidence
and an extractive, fully-cited answer. Try it:

```bash
curl -s localhost:8000/retrieve -H 'content-type: application/json' \
  -d '{"query": "What were Apple total net sales by product category?", "tickers": ["AAPL"]}'
```

Every returned chunk carries a `[n]` citation marker tied to a real filing
page/section and source URL.

The agent layer (`backend/src/agents`) runs a **LangGraph** state machine —
`research → analyze → comply → (visualize → synthesize | refuse)` — over a
**multi-provider LLM router** (`backend/src/providers`) that falls through Gemini
2.5 Flash-Lite → Flash → Groq Llama 3.3 70B → Groq GPT-OSS 120B on rate
limits/errors, with backoff, response caching, and a per-request provider trace
for the audit log. Compliance can veto to an honest *"insufficient evidence"*
refusal. It runs **live** with a `GEMINI_API_KEY`/`GROQ_API_KEY`, or fully
**offline** with a deterministic stub (no keys needed for CI/demos). Ask it:

```bash
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"query": "What risk factors does Apple disclose?", "tickers": ["AAPL"]}'
```

The response includes the cited answer, the analyst's cited findings, compliance
flags, chart specs, the verdict, and the provider trace.

**Adaptive routing** (Phase 4): a complexity classifier picks the cheapest
pipeline per query and the orchestrator dispatches accordingly —

| Query shape | Route | Engine |
| --- | --- | --- |
| single factual lookup | `simple` | hybrid search (Phase 2) |
| compound / comparative | `multi_hop` | agentic loop (query decomposition, ≤3 iters) |
| relationship / "share this risk" | `relationship` | **GraphRAG** over a NetworkX entity graph |

The entity graph (`backend/src/retrieval/graph.py`) is built during ingestion —
`company → faces → risk` and `company → has_officer → executive` edges, each
carrying citation metadata — so "which companies share competition risk?"
traverses to the answer with real filing citations. `GET /graph/stats` shows the
graph; every answer reports both its `planned_route` and the actual `route` used
(the UI's route badge).

**Self-RAG faithfulness gate** (Phase 5): after synthesis, a gate
(`backend/src/agents/faithfulness.py`) verifies every claim is grounded in the
cited evidence. An always-on numeric guardrail blocks any figure not present in
the sources ("uncited numbers are blocked"), and a semantic check (LLM when live,
deterministic lexical grounding offline) flags unsupported statements. Ungrounded
answers are turned into an honest *"insufficient evidence"* refusal instead of
being returned.

**Audit log** (Phase 5): every answered query appends a structured record —
query · routes · sources · providers used · verdict · faithfulness score ·
latency — to a JSONL trail (`backend/src/audit/`), readable via `GET /audit`.
This is both the compliance trail and the FinOps story (which provider answered,
how fast).

## Frontend (Phase 6)

A premium **Next.js 14** dashboard (`frontend/`) — Tailwind · Recharts ·
framer-motion · Supabase Auth — with a dark-mode-first, Bloomberg-terminal-meets-
SaaS aesthetic and a smooth light/dark toggle (AA contrast in both). Screens:
landing, login (demo-mode fallback when Supabase isn't configured), the chat
**workspace** (inline citation chips, source panel, RAG route badge, findings,
compliance flags, charts, faithfulness bar, the calm "insufficient evidence" state,
live provider trace), the **ticker dashboard** (corpus + entity-graph analytics),
the **audit log**, and the **evaluation** gauges.

```bash
cd frontend && npm install
npm run dev   # http://localhost:3000  (set NEXT_PUBLIC_API_URL to the backend)
```

## Evaluation (Phase 7)

Measured on **50 real FinanceBench questions across 17 companies** — peer-reviewed,
human-curated open-book QA over real 10-Ks (not self-generated). The eval corpus is
built from each question's real gold evidence passage, so retrieval is a genuine
needle-in-haystack over real filing text. Harness: `backend/src/evaluation`, run
with `python -m src.evaluation.run`; results serve at `GET /eval` and render in the
in-app evaluation dashboard.

Results with the **local semantic stack** (bge-small embeddings + `ms-marco-MiniLM`
cross-encoder reranker, no API key):

| Metric | Score |
| --- | --- |
| Context hit (retrieved the correct gold source) | **100%** |
| Faithfulness (Self-RAG gate pass rate) | **100%** |
| Citation coverage | **100%** |
| Refusal rate | 0% |
| Answer match (offline extractive synthesizer) | 36% |
| Avg latency | ~186 ms |

Retrieval and grounding are strong and fully cited. **Answer match is honestly
gated by the offline extractive synthesizer** — many FinanceBench answers require
multi-step LLM computation (e.g. cash-conversion-cycle), which lifts this metric
substantially once a `GEMINI_API_KEY` is configured. Canonical **RAGAS** metrics
(faithfulness, answer relevancy, context precision/recall) are wired and run when an
LLM key is present; without one the dashboard shows them as pending.

> Full run instructions and real RAGAS evaluation numbers are added as later phases
> land. This README is intentionally a stub during Phase 0.

## Build status

Built phase-by-phase; the commit history tells the story.

- [x] Phase 0 — repo scaffold, config, CI skeleton, GitHub remote
- [x] Phase 1 — ingestion (EDGAR + market + news → pgvector + BM25)
- [x] Phase 2 — advanced RAG (hybrid + reranker + citations)
- [x] Phase 3 — agents (LangGraph orchestrator + specialists + provider router)
- [x] Phase 4 — adaptive routing + GraphRAG
- [x] Phase 5 — Self-RAG gate + refusal + audit log
- [x] Phase 6 — premium frontend + Supabase Auth
- [x] Phase 7 — RAGAS evaluation
- [x] Phase 8 — deploy config (Vercel + Render + Supabase) + green CI

## Disclaimer

FinCopilot is an informational research tool. It is **not** investment advice and does
not execute trades.

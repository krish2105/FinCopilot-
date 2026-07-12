# FinCopilot — Agentic Financial Analyst Copilot

> A multi-agent, adaptive-RAG financial research copilot. A team of specialist AI
> agents reads **real** SEC filings, computes the analysis, checks compliance, and
> returns a **fully cited** answer — or honestly says **"insufficient evidence."**
> Built entirely on free-tier infrastructure.

<!-- Live URLs are added at the end of Phase 8 -->
**Live demo:** _coming in Phase 8_ · **API:** _coming in Phase 8_

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

> Full run instructions and real RAGAS evaluation numbers are added as later phases
> land. This README is intentionally a stub during Phase 0.

## Build status

Built phase-by-phase; the commit history tells the story.

- [x] Phase 0 — repo scaffold, config, CI skeleton, GitHub remote
- [x] Phase 1 — ingestion (EDGAR + market + news → pgvector + BM25)
- [ ] Phase 2 — advanced RAG (hybrid + reranker + citations)
- [ ] Phase 3 — agents (LangGraph orchestrator + specialists + provider router)
- [ ] Phase 4 — adaptive routing + GraphRAG
- [ ] Phase 5 — Self-RAG gate + refusal + audit log
- [ ] Phase 6 — premium frontend + Supabase Auth
- [ ] Phase 7 — RAGAS evaluation
- [ ] Phase 8 — deploy (Vercel + Render + Supabase) + CI

## Disclaimer

FinCopilot is an informational research tool. It is **not** investment advice and does
not execute trades.

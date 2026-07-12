# DECISIONS.md — architecture decisions & rationale

Guiding principle: **complexity is a cost, not a virtue.** Route the easy ~80% of
queries cheaply; reserve agentic/graph power for the hard ~20%.

## Stack decisions

| Layer | Choice | One-line reason |
| --- | --- | --- |
| LLM | Gemini Flash-Lite → Flash → Groq Llama 3.3 70B → Groq GPT-OSS 120B | Free, multi-provider fallback avoids a single point of rate-limit failure |
| Embeddings | Gemini Embedding + local `bge-small-en-v1.5` fallback | Free + reproducible/offline-safe for CI and demos |
| Vector DB | Supabase pgvector | Free, bundles Auth + Storage, enough for <5–10M vectors |
| Lexical | `rank_bm25` (in-process) | No external service, no cost |
| Reranker | local `ms-marco-MiniLM-L-6-v2` cross-encoder | Free, runs locally, no API dependency |
| Graph | NetworkX (MVP) → AuraDB Free (stretch) | Ship fast, upgrade to a managed graph once stable |
| Orchestration | LangGraph + FastAPI + Pydantic | State machine w/ loops + typed structured outputs |
| Frontend | Next.js + Tailwind + shadcn/ui | Premium look, free deploy on Vercel, matches 2026 AI-SaaS norms |
| Hosting | Vercel + Render + Supabase | Zero-cost; each free tier fits this app's shape |

## LLM fallback chain & free-tier limits

Try in order, retry with exponential backoff on 429/error, then fall through:

1. **Gemini 2.5 Flash-Lite** (`gemini-2.5-flash-lite`) — default: routing, simple
   retrieval, summarization.
2. **Gemini 2.5 Flash** — higher-quality synthesis / orchestrator reasoning.
3. **Groq `llama-3.3-70b-versatile`** — fast fallback + latency-sensitive streaming.
4. **Groq `openai/gpt-oss-120b`** — secondary fallback / harder reasoning.

Known free-tier limits **as of July 2026** (per-project for Gemini, per-org for Groq;
these change — always defer to each provider's live docs):

- Gemini Flash-Lite: ~15 RPM · 1,000 RPD · 250K TPM
- Gemini Flash: ~10 RPM · 250 RPD · 250K TPM
- Groq (each model): ~30 RPM · ~1,000 RPD · 8–12K TPM

Every request logs which provider actually answered (audit trail + FinOps story).

## RAG routing decisions

- **Advanced RAG (default):** hybrid dense + BM25 → cross-encoder rerank → top-k.
- **Agentic RAG (hard only):** ReAct loop capped at 3 iterations, every round logged.
- **GraphRAG (relationship only):** entity graph traversal (company → subsidiary →
  risk → executive).
- **Self-RAG gate (always):** relevance + faithfulness checks; unsupported claims are
  discarded and escalate to the "insufficient evidence" refusal.

## Cost governance

- Response cache keyed on `hash(normalized_query + ticker)`.
- Idempotent ingestion — never re-embed an already-stored chunk.
- In-process request queue respecting each provider's RPM so bursts degrade
  gracefully instead of throwing 429s to the UI.
- Local embedding/reranker fallback when all embedding APIs are rate-limited.

## Deferred / stretch

- Neo4j AuraDB Free migration (Phase 9) — MVP runs GraphRAG on NetworkX.
- Stripe billing, usage-metering dashboard, real-time filing webhooks (Phase 9+).

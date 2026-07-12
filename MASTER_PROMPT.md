# FinCopilot — Agentic Financial Analyst Copilot
## Master Prompt & End-to-End Implementation Plan (v2 — Deployment-Ready)

> **Repo:** https://github.com/krish2105/FinCopilot-
> **Type:** Multi-agent, agentic-RAG financial research SaaS — MVP, fully deployed, premium UI, zero-cost stack
> **Author:** Krishna Mathur
> **Status:** Planning / spec only — **no application code in this document**. This is the blueprint Claude Code will execute.
> **How to use this file:**
> 1. Create the empty folder locally, `cd` into it.
> 2. Drop this file in as `MASTER_PROMPT.md`.
> 3. Open Claude Code in that folder and paste **Part 18 (The Distilled Master Prompt)**.
> 4. Claude Code will scaffold, build phase-by-phase, connect to your GitHub remote, commit per phase, and deploy to live free-tier hosting.

---

## What changed from v1 (why this version is different)

v1 was a strong architecture spec but left the stack "fill in the brackets." This version removes every bracket:
- **Premium UI** is now a concrete spec: Next.js 14 + Tailwind + shadcn/ui, dark finance-dashboard aesthetic — not a generic Streamlit demo.
- **Free APIs** are now a concrete, verified (July 2026) provider chain with fallback logic, not "pick one."
- **Real, non-synthetic data** is locked for both ingestion (SEC EDGAR real filings) *and* evaluation (FinQA / TAT-QA / FinanceBench — real, human-curated financial QA benchmarks, not LLM-generated Q&A).
- **Ready to deploy** now means an actual free-tier hosting map with real URLs your repo will produce, plus CI/CD.
- **GitHub push** is now an explicit instruction set for Claude Code, targeting your existing repo.

---

## Table of Contents
1. One-liner & elevator pitch
2. Problem statement
3. Target users, personas & who pays
4. MVP scope vs. full vision
5. Core features
6. System architecture (multi-agent + agentic RAG)
7. **Full tech stack — concrete, free, verified (no brackets)**
8. **Data sources & ingestion — real filings + real eval benchmarks (zero synthetic data)**
9. **Premium UI / design system**
10. Repository structure
11. **Free-tier cost governance & LLM fallback strategy**
12. **Deployment architecture — exact free-tier hosting map**
13. **GitHub workflow & CI/CD**
14. Phased implementation roadmap
15. Evaluation, guardrails & the "insufficient evidence" contract
16. SaaS layer & security
17. Deliverables checklist, portfolio framing & Viva Q&A
18. **The Distilled Master Prompt (paste into Claude Code)**

---

## 1. One-liner & Elevator Pitch

**One-liner:** An AI financial-research copilot where a team of specialist agents reads real company filings, earnings, and news, runs the analysis, checks compliance, and returns a **fully cited** answer — or honestly says *"insufficient evidence."* Live, deployed, free to run.

**Elevator pitch:** Analysts waste hours reading 100-page filings to answer questions that repeat every quarter. FinCopilot replaces that grind with an orchestrated team of AI agents: a *Researcher* retrieves evidence via adaptive RAG, an *Analyst* computes ratios and trends, a *Compliance* agent validates claims and flags risk language, and a *Visualization* agent builds charts. Every number traces to a real SEC filing. FinCopilot uses **GraphRAG** for relationship questions and **Self-RAG** faithfulness gates so it refuses to hallucinate. It ships with a premium dashboard UI, workspace login, and a live deployed URL — a product a wealth desk could actually pilot, built entirely on free-tier infrastructure.

---

## 2. Problem Statement

- Financial research is **slow, repetitive, and expensive** — reading 10-Ks/10-Qs, cross-referencing footnotes, recomputing ratios each quarter.
- Generic LLM chatbots **hallucinate numbers**, which is fatal in finance.
- Simple "vector search over PDFs" fails on **relationship/multi-hop questions**.
- Compliance teams need an **audit trail** — every claim tied to a source, every refusal logged.
- **Consequence:** firms either overpay for junior analyst hours or avoid AI entirely because they can't trust it.

**The gap FinCopilot fills:** trustworthy, cited, relationship-aware financial research at machine speed, with a built-in "I don't know" contract — deployed where anyone can try it.

---

## 3. Target Users, Personas & Who Pays

| Persona | Job-to-be-done | Willingness to pay |
|---|---|---|
| Equity research analyst | Summarize filings, compute ratios, draft notes fast | High |
| Wealth / relationship manager | Answer client questions on holdings with citations | High |
| VC / PE associate | Due-diligence across a portfolio's filings | High |
| Corporate finance / FP&A team | Benchmark competitors, track covenant risk | Medium–High |
| Serious retail investor | Cited answers instead of guesses | Low–Medium (freemium) |

**Monetization model (state this in your README):**
- **Freemium:** N free queries/month, public tickers only.
- **Pro (per-seat):** unlimited queries, private document upload, GraphRAG, export.
- **Team/Enterprise:** multi-tenant workspaces, SSO, audit logs, usage metering.
- **Metering axis:** per-query token cost + per-document ingestion (your FinOps story).

---

## 4. MVP Scope vs. Full Vision

**MVP — build and deploy this (must be a live URL, not a local demo):**
- Ingest **real** public filings + market data + news for **8–10 real tickers** (mix of US + UAE/GCC for local relevance — see Part 8).
- Adaptive RAG: simple lookups → hybrid search; relationship queries → GraphRAG.
- 4 agents (Orchestrator, Researcher, Analyst, Compliance) + Visualization.
- Self-RAG faithfulness gate + **cited answers** with source page references.
- Premium Next.js dashboard UI with login/workspace.
- FastAPI backend, Dockerized.
- RAGAS evaluation on **real benchmark data** (FinQA/TAT-QA/FinanceBench subset).
- **Deployed live** on free-tier hosting (Part 12), pushed to your GitHub repo with CI.

**Full vision (roadmap — describe, don't build yet):**
- Billing (Stripe), usage dashboards, real-time filing webhooks.
- Portfolio-level monitoring & alerting.
- Fine-tuned small model, human-in-the-loop review queue, mobile app.

**Non-goals:**
- Not investment advice; not a trading bot; no order execution.
- No paywalled/scraped proprietary data.
- No guarantee of real-time tick data.

---

## 5. Core Features

1. **Natural-language Q&A** over real filings, financials, and news.
2. **Adaptive routing** — cheapest pipeline that can answer each query.
3. **Cited answers** — every claim links to a source document + page/section.
4. **"Insufficient evidence" contract** — refuses rather than guesses.
5. **Ratio & trend analysis** — liquidity, leverage, profitability, growth.
6. **Relationship/multi-hop reasoning** via GraphRAG.
7. **Compliance flagging** — risk-factor language, going-concern, restatements.
8. **Auto-visualizations** — trend lines, ratio bars, comparison tables.
9. **Evaluation dashboard** — faithfulness, relevance, precision/recall, shown in-app.
10. **Audit log** — every query, route, sources, refusal.
11. **Workspace login** — Supabase Auth; each user's uploaded docs are isolated.
12. **Live, shareable demo URL.**

---

## 6. System Architecture (Multi-Agent + Agentic RAG)

### 6.1 High-level flow
```
User query (via premium web UI)
   │
   ▼
[Orchestrator agent] ── classifies intent & complexity
   │
   ├─► Adaptive RAG Router
   │       ├─ Simple factual  → Hybrid search (dense + BM25) + reranker
   │       ├─ Multi-hop reason → Agentic retrieval loop (ReAct, capped at 3 iters)
   │       └─ Relationship     → GraphRAG (entity/relationship traversal)
   │
   ├─► [Researcher agent]     → gathers & ranks evidence chunks, with citations
   ├─► [Analyst agent]        → computes ratios/trends from retrieved figures
   ├─► [Compliance agent]     → validates claims, flags risk language
   └─► [Visualization agent]  → builds charts/tables
   │
   ▼
[Self-RAG faithfulness gate] ── is every claim supported by cited context?
   │        ├─ Yes → return cited answer + charts to UI
   │        └─ No  → return "insufficient evidence" + what's missing
   ▼
[Audit log] ── query, route, sources, verdict, LLM provider used, latency, cost
```

### 6.2 The agents (roles & contracts)
- **Orchestrator:** owns state, classifies the query, picks the RAG route, delegates, synthesizes the final answer. Never fabricates — only composes verified pieces.
- **Researcher:** turns the query into sub-queries, retrieves & reranks evidence, returns chunks **with source metadata** (ticker, filing type, date, page). Self-terminating loop, hard cap on iterations.
- **Analyst:** computes ratios/growth/trends **only from retrieved numbers**, cites the source line for each input figure. Refuses if a required figure wasn't retrieved.
- **Compliance:** scans for risk factors, going-concern, restatements, litigation; validates the Analyst's claims; can veto to the "insufficient evidence" path.
- **Visualization:** renders trend/comparison charts from validated figures only.

### 6.3 The RAG spectrum (adaptive by design)
- **Advanced RAG (default foundation):** hybrid search (dense + BM25) → cross-encoder reranker → top-k context.
- **Agentic RAG (hard queries only):** ReAct loop, capped at 3 iterations, every round logged.
- **GraphRAG (relationship queries only):** entity graph (company → subsidiary → risk → executive).
- **Self-RAG gate (always):** relevance + faithfulness checks; discard unsupported claims; escalate to refusal.

> **Design principle for DECISIONS.md:** *Complexity is a cost, not a virtue.* Route the easy 80% cheap; reserve agentic/graph power for the hard 20%.

---

## 7. Full Tech Stack — Concrete, Free, Verified (No Brackets)

Every choice below is a **free tier, verified current as of July 2026**. No paid keys required to build or run the MVP.

### 7.1 LLM layer (reasoning) — free multi-provider fallback chain
| Priority | Provider / Model | Free limits (per project/org) | Role |
|---|---|---|---|
| 1st | **Google Gemini 2.5 Flash-Lite** (`gemini-2.5-flash-lite`) | 15 RPM · 1,000 RPD · 250K TPM | Default — routing, simple retrieval, summarization |
| 2nd | **Google Gemini 2.5 Flash** | 10 RPM · 250 RPD · 250K TPM | Higher-quality synthesis, orchestrator reasoning |
| 3rd (fallback) | **Groq `llama-3.3-70b-versatile`** | 30 RPM · ~1,000 RPD · 12K TPM | Fast fallback when Gemini is rate-limited; also used for latency-sensitive UI streaming |
| 4th (fallback) | **Groq `openai/gpt-oss-120b`** | 30 RPM · 1,000 RPD · 8K TPM | Secondary fallback / harder reasoning at no cost |

> Rate limits are per-project (Gemini) / per-org (Groq) — no card required, but both are strict. Build a **provider router with automatic fallback + exponential backoff** (see Part 11). This mirrors the zero-cost pattern used in your ComplianceAgent project (Gemini free + Groq fallback), so you're reusing a proven design.

### 7.2 Embeddings
- **Primary:** `gemini-embedding-001` (Gemini API, free tier — high TPM, generous for a small corpus).
- **Offline/reliability fallback:** local `sentence-transformers` model (e.g. `BAAI/bge-small-en-v1.5`) — 100% free, no API, no rate limit, runs on CPU. Use this for reproducible demo runs and CI so the eval pipeline never depends on a live rate-limited API.

### 7.3 Retrieval
| Component | Choice | Why |
|---|---|---|
| Vector DB | **Supabase Postgres + pgvector** (free tier) | Free managed Postgres with pgvector built in; also gives you Auth + Storage in the same free project |
| Lexical search | **BM25** via `rank_bm25` (in-process) | No external service, no cost |
| Reranker | **Local cross-encoder** (`cross-encoder/ms-marco-MiniLM-L-6-v2` via `sentence-transformers`) | Free, runs locally, no API dependency |
| Graph (GraphRAG) | **Neo4j AuraDB Free** (free forever tier, small graph) — *or* an in-process **NetworkX** graph for MVP simplicity | AuraDB Free gives you a "real" managed graph DB for the portfolio story; NetworkX is the zero-dependency fallback if you want to ship faster. Recommend: build with NetworkX first (Phase 4), migrate to AuraDB Free once stable (Phase 9 stretch) |

### 7.4 Orchestration & backend
- **LangGraph** — multi-agent state machine, loops, human-in-the-loop gates.
- **FastAPI** — async API layer.
- **Pydantic** — typed structured outputs everywhere (no regex parsing).
- **RAGAS** — evaluation harness (faithfulness, relevance, context precision/recall).

### 7.5 Premium frontend (see Part 9 for full design spec)
- **Next.js 14 (App Router) + TypeScript**
- **Tailwind CSS + shadcn/ui** component library
- **Recharts** for financial visualizations
- **Vercel AI SDK** (`useChat`/streaming helpers) for a real streaming chat UX

### 7.6 Auth & multi-tenancy
- **Supabase Auth** (free) — email/password + Google OAuth, row-level security so each workspace only sees its own documents.

### 7.7 Packaging, CI/CD & observability
- **Docker + docker-compose** for local one-command run.
- **GitHub Actions** for lint/test/build on every push (Part 13).
- **Structured JSON logging** to a file/table for the audit log; optional free-tier **Langfuse Cloud** (has a free hobby tier) for agent tracing — mark as optional, not required for MVP.

### DECISIONS.md summary table (write this into the repo)
| Layer | Choice | One-line reason |
|---|---|---|
| LLM | Gemini Flash-Lite → Flash → Groq Llama 3.3 70B → Groq GPT-OSS 120B | Free, multi-provider fallback avoids single point of rate-limit failure |
| Embeddings | Gemini Embedding + local bge-small fallback | Free + reproducible/offline-safe |
| Vector DB | Supabase pgvector | Free, bundles Auth + Storage, enough for <5–10M vectors |
| Graph | NetworkX → AuraDB Free | Ship fast, upgrade to managed graph once stable |
| Frontend | Next.js + Tailwind + shadcn/ui | Premium look, free deploy on Vercel, matches 2026 AI-SaaS UI norms |
| Hosting | Vercel + Render + Supabase | Zero-cost, each platform's free tier is designed for exactly this shape of app |

---

## 8. Data Sources & Ingestion — Real Filings + Real Eval Benchmarks (Zero Synthetic Data)

**No synthetic data anywhere in this project — ingestion or evaluation.**

### 8.1 Ingestion corpus (real, public, free)
- **Filings:** **SEC EDGAR** full-text search + submissions API (free, no key required) — real 10-K/10-Q/8-K filings.
- **Market data / fundamentals:** `yfinance` (free, no key) or **Financial Modeling Prep free tier** (250 requests/day) for prices, ratios, statements.
- **News:** **GDELT** (free, no key) or a free-tier news API (e.g. NewsAPI free dev tier) for recent headlines — respect ToS, public-only.
- **UAE/GCC flavor (optional, for your Dubai-market angle):** DFM/ADX public disclosure PDFs — note free-access limits in `DATA_SOURCES.md`.

**Starting ticker set (real companies, pick 8–10):** e.g. `AAPL, MSFT, TSLA, JPM, AMZN` (US, EDGAR-rich) + 2–3 UAE-listed names with public disclosures for the regional angle.

### 8.2 Evaluation corpus — real, human-curated, not LLM-generated
Use established **public financial-QA benchmarks** built from real filings, so your RAGAS numbers are grounded in genuine, peer-reviewed question sets rather than self-authored or LLM-generated questions:
- **FinQA** — real Q&A pairs requiring numerical reasoning over real earnings reports.
- **TAT-QA** — real hybrid tabular-and-textual financial QA.
- **FinanceBench** — real open-book QA over real public filings, purpose-built for evaluating RAG systems in finance.

Sample a subset (e.g. 50–100 questions) relevant to your ingested tickers, or if your tickers don't overlap, ingest a couple of the benchmark's source filings alongside your primary corpus specifically to run the eval. Document this choice in `DATA_SOURCES.md` — it's a strong, defensible "why I didn't just make up test questions" answer for interviews.

### 8.3 Ingestion pipeline (design)
1. Fetch document → 2. Parse (PDF/HTML → clean text, preserve page numbers) → 3. Structure-aware chunk (keep tables intact) → 4. Embed → 5. Store in pgvector + BM25 index → 6. Extract entities/relationships → build graph → 7. Store source metadata (ticker, doc type, date, page) for citations.

> `DATA_SOURCES.md` must list every source, its license/terms, and confirm no synthetic data was used — this is a compliance-awareness signal that's gold for a finance product.

---

## 9. Premium UI / Design System

This is what makes it look like a **funded fintech startup's product**, not a hackathon demo.

### 9.1 Visual direction
- **Dark-mode-first finance dashboard** aesthetic (think Bloomberg Terminal × modern SaaS, not a generic chatbot).
- Restrained, professional palette: near-black background, one confident accent color (e.g. deep emerald or amber for "verified/cited" states; red for compliance flags), neutral grays for text hierarchy.
- Typography: a clean geometric sans for UI (e.g. Inter) + a monospace for numbers/tickers/citations (numbers should visually feel "precise").
- Avoid default shadcn/ui look-alike spacing — commit to a distinct grid, generous whitespace, subtle motion on data updates (not flashy).

### 9.2 Key pages/screens
1. **Landing/marketing page** — one-liner, live demo CTA, "how it works" 3-step visual, sample cited answer as a hero visual.
2. **Login/workspace** — Supabase Auth email + Google OAuth.
3. **Chat/research workspace** (core screen):
   - Center: streaming chat with the copilot, each answer showing **inline citation chips** (click → source panel).
   - Right panel: **source viewer** (highlighted filing excerpt + page number).
   - Bottom/side: **route indicator** — small badge showing which pipeline answered ("Hybrid Search" / "Agentic Retrieval" / "GraphRAG") — great for demos, shows the adaptive routing working live.
4. **Ticker dashboard** — auto-generated ratio/trend charts (Recharts) per company, refreshed from ingested data.
5. **Compliance/audit log view** — searchable table of past queries, routes, sources, verdicts.
6. **Evaluation dashboard** — RAGAS scores rendered as cards/gauges (faithfulness, relevance, precision/recall) — turns your eval numbers into a visual proof-point recruiters can see in 10 seconds.

### 9.3 Component list (shadcn/ui-based)
`Command`/search palette for ticker lookup, `Sheet` for the source panel, `Badge` for route/compliance flags, `Card` for dashboard tiles, `Table` for audit logs, `Chart` (Recharts wrapper) for trends, `Skeleton` loaders during streaming, `Toast` for refusal/error states.

### 9.4 The "insufficient evidence" UX
This is your differentiator — make the refusal state feel **designed, not broken**: a distinct amber/neutral card (not a red error) explaining *what evidence would be needed*, with a one-click "search wider" or "upload more documents" action.

---

## 10. Repository Structure

```
fincopilot/
├── README.md
├── MASTER_PROMPT.md
├── DECISIONS.md
├── DATA_SOURCES.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── .github/
│   └── workflows/
│       ├── ci.yml              # lint + test on every push
│       └── docker-build.yml    # build & validate image
├── docs/
│   ├── architecture.md
│   └── demo.md                 # 2-min Loom script + screenshots
├── data/                        # ingested docs (gitignored)
├── backend/
│   ├── src/
│   │   ├── ingestion/           # fetch, parse, chunk, embed
│   │   ├── retrieval/           # hybrid search, reranker, graphrag, router
│   │   ├── agents/              # orchestrator, researcher, analyst, compliance, viz
│   │   ├── providers/           # LLM fallback router (Gemini <-> Groq)
│   │   ├── evaluation/          # ragas harness
│   │   ├── api/                 # fastapi app + routes
│   │   └── config/              # settings, prompts
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # shadcn/ui-based components
│   ├── lib/                     # API client, Supabase client
│   ├── package.json
│   └── Dockerfile
├── eval/
│   ├── test_questions.jsonl     # sampled from FinQA / TAT-QA / FinanceBench
│   └── results/                 # eval outputs (your portfolio numbers)
└── scripts/
    └── deploy.md                # exact deployment steps per host
```

---

## 11. Free-Tier Cost Governance & LLM Fallback Strategy

This is the section that proves "engineering judgment," not just model-calling.

**Rules to implement:**
1. **Provider router:** try Gemini Flash-Lite first → on 429/error, retry with backoff → fall back to Gemini Flash → fall back to Groq Llama 3.3 70B → fall back to Groq GPT-OSS 120B. Log which provider answered every request.
2. **Response caching:** cache identical/near-identical queries (hash the normalized query + ticker) to avoid repeat API calls — huge free-tier saver for a demo that recruiters will hit repeatedly.
3. **Embedding cache:** never re-embed a chunk that's already stored; ingestion should be idempotent.
4. **Request queue:** a simple in-process queue respecting each provider's RPM so bursts (e.g. concurrent demo users) degrade gracefully instead of throwing 429s to the UI.
5. **Local reranker/embeddings fallback:** if all embedding APIs are rate-limited, fall back to the local `sentence-transformers` model rather than failing the request.
6. **Budget dashboard (stretch):** the audit log already captures provider + token counts per query — surface this as your "FinOps" story in the evaluation dashboard.

**Document current known limits in `DECISIONS.md`** (Gemini Flash-Lite: 15 RPM/1,000 RPD; Gemini Flash: 10 RPM/250 RPD; Groq: 30 RPM/~1,000 RPD per model) and note these are per-project/org and may change — link to each provider's live docs rather than hardcoding numbers as gospel.

---

## 12. Deployment Architecture — Exact Free-Tier Hosting Map

| Component | Host | Free tier notes |
|---|---|---|
| **Frontend** (Next.js) | **Vercel** (Hobby) | 100GB bandwidth, auto-deploy on push to `main`, preview URLs per PR |
| **Backend API** (FastAPI, Docker) | **Render** (free Web Service) | 512MB RAM; spins down after 15 min idle → 30–60s cold start on first request. Document this in the README as expected behavior, not a bug |
| **Database** (Postgres + pgvector + Auth) | **Supabase** (free project) | Managed Postgres, pgvector built in, Auth + Storage included |
| **Graph DB** (optional, Phase 9) | **Neo4j AuraDB Free** | Small free-forever graph instance; MVP can run GraphRAG on in-process NetworkX instead and skip this until the stretch phase |
| **Demo mirror (optional, recommended)** | **Hugging Face Spaces** (Docker Space) | Single-container fallback demo link — useful because it has no separate frontend/backend split to manage, good for a "click and it just works" link in your resume |

**Environment variables to configure per host (document in `.env.example`):**
`GEMINI_API_KEY`, `GROQ_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `NEXT_PUBLIC_API_URL`, `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` (Phase 9 only).

**Deployment steps (write into `scripts/deploy.md`):**
1. Create free Supabase project → enable `pgvector` extension → copy connection string + keys.
2. Push `backend/` — connect the Render free Web Service directly to the GitHub repo (`backend/` as root), set env vars, auto-deploy on push to `main`.
3. Push `frontend/` — connect Vercel directly to the GitHub repo (`frontend/` as root), set `NEXT_PUBLIC_API_URL` to the Render URL, auto-deploy on push to `main`.
4. (Optional) Mirror to a Hugging Face Docker Space for a zero-cold-start-explanation demo link.
5. Add both live URLs to `README.md` top section.

---

## 13. GitHub Workflow & CI/CD

Claude Code should treat the existing repo as the single source of truth from Phase 0 onward.

**Git setup (Phase 0):**
```
git init                                   # if not already a repo
git remote add origin https://github.com/krish2105/FinCopilot-.git
git branch -M main
```
Commit **once per completed phase** with a clear message (e.g. `feat: ingestion pipeline (Phase 1)`), and push after each phase so the repo history itself tells the build story — a strong signal for anyone reviewing commit history.

**`.github/workflows/ci.yml`** — on every push/PR:
- Install backend deps, run `ruff`/`black --check` + `pytest`.
- Install frontend deps, run `next lint` + `tsc --noEmit`.

**`.github/workflows/docker-build.yml`** — on every push to `main`:
- Build the backend Docker image to confirm it builds cleanly (does not need to push anywhere; Render/Vercel handle actual deploys via their own GitHub integration).

**Branch strategy:** keep it simple for a solo project — commit directly to `main` per phase; optionally use short-lived feature branches + PRs for Phases 6+ (UI/deployment) to have visible PR history, which also reads well to reviewers.

---

## 14. Phased Implementation Roadmap

**Phase 0 — Setup & GitHub (0.5 week):** repo scaffold (Part 10), `.env.example`, `docker-compose.yml` skeleton, connect to `origin`, first commit + push, README stub, pick real tickers.

**Phase 1 — Ingestion (1 week):** EDGAR + market data + news fetch → parse → chunk → embed (Gemini + local fallback) → store in Supabase pgvector + BM25. *Done when:* real documents are searchable.

**Phase 2 — Advanced RAG (1 week):** hybrid search + local reranker + citation formatting. *Done when:* cited answers work for simple factual questions.

**Phase 3 — Agents (1.5 weeks):** LangGraph orchestrator + Researcher + Analyst + Compliance; Pydantic outputs; LLM provider fallback router (Part 11). *Done when:* a query flows through all agents to a composed, cited answer.

**Phase 4 — Adaptive routing + GraphRAG (1.5 weeks):** complexity classifier; NetworkX entity graph; relationship route. *Done when:* "which subsidiaries share this risk?" works.

**Phase 5 — Self-RAG gate + refusal + audit log (0.5 week):** faithfulness/relevance checks; "insufficient evidence" path; structured audit logging.

**Phase 6 — Premium frontend (2 weeks):** Next.js + Tailwind + shadcn/ui build per Part 9 — chat workspace, source panel, ticker dashboard, audit log view, eval dashboard; Supabase Auth login.

**Phase 7 — Evaluation (0.5 week):** RAGAS on FinQA/TAT-QA/FinanceBench subset; publish real numbers in README and the in-app eval dashboard.

**Phase 8 — Deploy (0.5 week):** Vercel (frontend) + Render (backend) + Supabase (DB), connected via GitHub auto-deploy; verify both live URLs work end-to-end; add CI (Part 13).

**Phase 9 (stretch) — SaaS polish:** Neo4j AuraDB Free migration, usage metering dashboard, Stripe billing stub, real-time filing refresh.

---

## 15. Evaluation, Guardrails & the "Insufficient Evidence" Contract

**RAGAS metrics (report real numbers from the real benchmark subset):**
- **Faithfulness** — are claims grounded in retrieved context? (headline metric)
- **Answer relevance** — does the answer address the question?
- **Context precision & recall** — did retrieval fetch the right chunks?

**Guardrails:**
- Every numeric claim must cite a source line; uncited numbers are blocked.
- Self-RAG discards unsupported claims; unsupported answers become **"insufficient evidence"** + what's missing.
- Compliance agent can veto any answer into the refusal path.
- Standing disclaimer: *informational, not investment advice.*
- Every query, route, sources, provider used, and verdict logged (audit trail).

---

## 16. SaaS Layer & Security

- **Auth & multi-tenancy:** Supabase Auth + row-level security — each workspace's uploaded documents are isolated.
- **Usage metering:** log tokens/query and provider used per user — your FinOps dashboard story.
- **Audit logs & basic RBAC:** who asked what, which sources, what verdict.
- **Security:** no secrets in code (`.env` only, gitignored), input validation on all API routes, rate limiting on the public API, never place sensitive data in URLs.

---

## 17. Deliverables Checklist, Portfolio Framing & Viva Q&A

### What to ship
- [ ] Public GitHub repo, clean structure, commit history tells the build story
- [ ] **Live frontend URL** (Vercel) + **live API URL** (Render)
- [ ] `README.md`: problem → architecture diagram → live links → real RAGAS numbers → run instructions
- [ ] `DECISIONS.md`, `DATA_SOURCES.md` (confirms zero synthetic data)
- [ ] 2-minute Loom: show a cited answer, a GraphRAG relationship query, and a refusal
- [ ] RAGAS results in `eval/results/`, also visible in the in-app eval dashboard
- [ ] Dockerized, one-command local run + CI passing badge

### Portfolio framing
- *"Multi-agent, adaptive-RAG financial copilot with a premium Next.js dashboard, deployed live on a fully free-tier stack (Vercel + Render + Supabase)."*
- *"Evaluated on real FinQA/TAT-QA/FinanceBench benchmark questions — not self-generated — with published RAGAS faithfulness scores."*
- *"Multi-provider LLM fallback (Gemini ↔ Groq) with automatic rate-limit handling — zero API cost to run."*

### Viva / interview Q&A
1. **Why multi-agent instead of one big prompt?** Separation of concerns, verifiable sub-steps, specialist control — each agent's output is easy to sanity-check.
2. **Why adaptive routing?** ~80% of queries are simple and shouldn't pay agentic/graph latency and token cost.
3. **When does GraphRAG earn its cost?** Only on cross-document, relationship/multi-hop questions.
4. **How do you stop hallucination?** Hybrid retrieval + reranker, Self-RAG faithfulness gate, mandatory citations, explicit refusal.
5. **Why a multi-provider LLM fallback instead of one API?** Free tiers have tight per-minute/per-day caps; a fallback chain keeps the product usable under load without paying for infrastructure.
6. **Why these eval questions specifically?** FinQA/TAT-QA/FinanceBench are peer-reviewed, human-curated, built from real filings — avoids the circularity of grading yourself with your own generated questions.
7. **Why Supabase over a self-hosted Postgres?** Free managed pgvector + Auth + Storage in one project, appropriate for <5–10M vectors and a solo build.
8. **What makes it SaaS, not a script?** Workspace auth with row-level isolation, usage metering, audit logs, live multi-service deployment.
9. **Biggest risk?** Trust — mitigated by citations, refusal contract, compliance veto.
10. **What would you build next?** Real-time filing webhooks, Stripe billing, portfolio-level risk alerting.

---

## 18. The Distilled Master Prompt (paste this into Claude Code)

> Paste the block below into Claude Code in your empty `FinCopilot-` folder. It builds phase-by-phase, commits/pushes to your GitHub repo after each phase, and ends with a live deployment.

```
You are helping me build "FinCopilot", a multi-agent, agentic-RAG financial research
copilot with a premium UI, deployed live, built entirely on free-tier infrastructure.
Work phase-by-phase; do NOT dump the whole codebase at once. After each phase, stop,
summarize what you built, tell me what to test, commit the changes, and push to GitHub.

GITHUB
This repo already exists and is empty: https://github.com/krish2105/FinCopilot-
At the start: git init (if needed), git remote add origin
https://github.com/krish2105/FinCopilot-.git, git branch -M main.
After every phase: commit with a clear message (e.g. "feat: ingestion pipeline
(Phase 1)") and push to main.

GOAL
A user asks a plain-English finance question in a premium web dashboard and a team of
agents returns a FULLY CITED answer with charts — or replies "insufficient evidence"
instead of guessing. The whole thing is deployed and reachable via a live URL.

ARCHITECTURE
- Orchestrator (LangGraph state machine) classifies each query and routes it via an
  ADAPTIVE RAG ROUTER:
    * simple factual  -> hybrid search (dense + BM25) + local cross-encoder reranker
    * multi-hop       -> agentic ReAct retrieval loop, capped at 3 iterations, logged
    * relationship    -> GraphRAG over an in-process NetworkX entity graph
      (company/subsidiary/risk/executive)
- Specialist agents: Researcher (retrieve+rank evidence with source metadata),
  Analyst (compute ratios/trends from RETRIEVED figures only, cite each input),
  Compliance (flag risk language, validate claims, can veto to refusal),
  Visualization (charts/tables from validated figures only).
- Self-RAG faithfulness gate checks every claim is supported by cited context before
  returning; unsupported answers become "insufficient evidence" + what's missing.
- Log every query, route, sources, LLM provider used, and verdict (audit trail).

LLM / EMBEDDINGS (free, multi-provider fallback — build a provider router)
1st: Google Gemini 2.5 Flash-Lite (gemini-2.5-flash-lite)
2nd: Google Gemini 2.5 Flash
3rd fallback: Groq llama-3.3-70b-versatile
4th fallback: Groq openai/gpt-oss-120b
On rate-limit/error, retry with backoff then fall through the chain; log which
provider answered. Embeddings: gemini-embedding-001 primary, local
sentence-transformers (BAAI/bge-small-en-v1.5) as an offline/rate-limit fallback.
Reranker: local cross-encoder/ms-marco-MiniLM-L-6-v2 (no API needed).

BACKEND STACK
LangGraph, FastAPI, Pydantic, Supabase Postgres + pgvector (vector store), rank_bm25
(lexical), NetworkX (graph, MVP) -> Neo4j AuraDB Free (stretch), RAGAS (evaluation),
Docker.

FRONTEND STACK (premium UI — this matters, do not default to Streamlit)
Next.js 14 (App Router) + TypeScript, Tailwind CSS, shadcn/ui components, Recharts
for visualizations, Vercel AI SDK for streaming chat. Dark-mode finance-dashboard
aesthetic: near-black background, one confident accent color, Inter for UI text,
a monospace font for numbers/tickers/citations. Build these screens: landing page,
Supabase Auth login, a chat/research workspace with inline citation chips and a
source-excerpt side panel and a small badge showing which RAG route answered, a
ticker dashboard with auto-generated ratio/trend charts, an audit-log table view,
and an evaluation dashboard rendering the RAGAS scores as cards. Design the
"insufficient evidence" state as an intentional, calm UI state, not an error.

AUTH
Supabase Auth (email + Google OAuth), row-level security so each workspace only sees
its own uploaded documents.

DATA — REAL ONLY, NO SYNTHETIC DATA ANYWHERE
Ingestion: SEC EDGAR (real filings, free, no key) for 8-10 real tickers (mix of major
US tickers + 1-2 UAE/GCC names with public disclosures); yfinance or Financial
Modeling Prep free tier for market data/fundamentals; GDELT or a free news API for
headlines. Preserve page-level source metadata for citations.
Evaluation: sample real questions from FinQA, TAT-QA, and FinanceBench (real,
human-curated public financial-QA benchmarks) instead of self-generated questions.
Document every source and license in DATA_SOURCES.md and explicitly confirm no
synthetic data was used.

DEPLOYMENT (free tier, all connected via GitHub auto-deploy)
Frontend -> Vercel (connect repo, root = frontend/). Backend -> Render free Web
Service (connect repo, root = backend/, Docker). Database -> Supabase free project
with pgvector enabled. Add both live URLs to the top of README.md once deployed.
Add GitHub Actions: ci.yml (lint + test backend and frontend on every push) and
docker-build.yml (verify the backend image builds on every push to main).

COST GOVERNANCE
Implement response caching (hash normalized query+ticker), idempotent ingestion
(never re-embed existing chunks), and a request queue respecting each provider's
RPM so concurrent demo traffic degrades gracefully instead of throwing errors.

BUILD ORDER (one phase per response; commit + push after each)
0. Repo scaffold (full tree from the plan), .env.example, docker-compose skeleton,
   connect to GitHub remote, first commit + push, README stub, finalize ticker list.
1. Ingestion: fetch real filings/data -> parse (keep page numbers) -> structure-aware
   chunk -> embed -> store in Supabase pgvector + BM25 index, with source metadata.
2. Advanced RAG: hybrid search + local reranker + citation formatting.
3. Agents: LangGraph orchestrator + Researcher + Analyst + Compliance, Pydantic
   outputs, LLM provider fallback router.
4. Adaptive routing + GraphRAG: complexity classifier + NetworkX entity graph +
   relationship route.
5. Self-RAG gate + "insufficient evidence" refusal + structured audit log.
6. Premium frontend: Next.js + Tailwind + shadcn/ui, all screens listed above,
   Supabase Auth.
7. RAGAS evaluation harness on the real FinQA/TAT-QA/FinanceBench subset; write
   scores to eval/results/ and surface them in the eval dashboard.
8. Deploy: connect Vercel + Render + Supabase to the GitHub repo, verify the live
   URLs work end-to-end, add GitHub Actions CI, update README with live links and
   real eval numbers.

RULES
- Never fabricate numbers; every numeric claim must cite a source line.
- No synthetic data anywhere — ingestion and evaluation both use real, public data.
- Prefer the cheapest RAG route that can answer; reserve agentic/graph for hard
  queries.
- Typed structured outputs (Pydantic), no fragile regex parsing.
- Standing disclaimer: informational, not investment advice.
- Keep all secrets in .env (gitignored); never hardcode keys; never commit .env.
- After each phase: summarize what was built, what to test, commit, and push.

Start with Phase 0.
```

---

### Final note
This version is designed to end with **two live URLs, a GitHub commit history that tells the build story, real evaluation numbers on a peer-reviewed benchmark, and a premium dashboard UI** — the combination that separates a "finished tutorial" repo from a "this person already does the job" repo. Total build time is roughly the same 8–9 weeks as v1; the difference is entirely in what's actually shippable at the end.

# FinCopilot — 2026 Brainstorm, Gap Analysis & Implementation Plan

_Last updated: 2026-07-13. Constraints this plan is built around: **full arc (portfolio → launch → monetize)**, **$0 budget (free tiers only)**, **retail investors as the first user**, **full-time sprint**._

---

## 1. Executive read — where you actually stand

FinCopilot is **not a prototype**. It's ~6,800 LOC of backend across 20+ modules, ~1,500 lines of tests, 12 frontend routes, a real agentic RAG stack (LangGraph, adaptive routing, GraphRAG, Self-RAG faithfulness gate), multi-tenancy + RLS groundwork, guarded billing/ops/security. That is more than most funded seed-stage demos have.

**Your two genuine strengths map exactly onto 2026 differentiators:**
1. **Faithfulness engineering** — Self-RAG gate, numeric guardrail ("uncited numbers blocked"), honest "insufficient evidence" refusals, audit trail. This is precisely the wedge Brightwave/Finster market on. Most tools only *cite*; you *verify and refuse*.
2. **Agentic, adaptive routing** — cheap fast-path vs. multi-hop decomposition vs. GraphRAG. This is the "agentic depth" the market now rewards.

**The uncomfortable truth:** none of that matters until the thing is **actually live, seeded, and answering with a real LLM.** Right now the deployed site can't reach the backend, the corpus is empty, and answers run on the offline stub. So Phase 0 below is not optional.

---

## 2. What the 2026 market says (grounded in research)

**Table stakes — everyone has these now:** RAG over SEC filings + earnings + market data; inline citations; conversational Q&A over docs; earnings/filing summarization; multi-format ingestion (PDF/Excel/Word); a security baseline story.

**Differentiators — what leaders have:** true agentic multi-step workflows that produce *finished deliverables* in the user's own tools; faithfulness *beyond* citations (reasoning traces, validation layers, cross-doc inconsistency flagging); finance-native models; proprietary data moats; single-tenant deployments.

**Your flank:** **Perplexity Finance owns low-cost retail** — free tier + $20/mo Pro, live quotes, interactive charts, direct SEC filings, an Earnings Hub with live transcript metric extraction. That is the bar for a *retail-first* product, and it's the most useful competitor to benchmark against (not Bloomberg/Hebbia, who sell $18K–$30K/seat to institutions).

**Retail-first implication:** you don't need SOC 2, SSO, or data residency to launch to retail. You need **live prices, charts, earnings summaries, a fast/clean consumer UX, and rock-solid "not investment advice" framing.** Save the enterprise machinery for the upmarket phase.

---

## 3. Honest scorecard

| Dimension | Retail MVP | Full SaaS / Enterprise | Notes |
|---|---|---|---|
| Core agentic RAG | 9/10 | 8/10 | Genuine strength; ahead of most |
| Faithfulness / trust | 9/10 | 8/10 | Your headline differentiator |
| **Actually working live** | **2/10** | **2/10** | Deploy broken, corpus empty, stub LLM |
| Real-time market data / charts | 3/10 | 3/10 | Retail table-stakes; largely missing |
| Earnings-call data | 2/10 | 2/10 | Not ingested yet |
| Consumer UX / onboarding / mobile | 6/10 | 6/10 | Good desktop; needs retail polish |
| Auth (real, not demo) | 5/10 | 4/10 | Supabase Auth wired, demo fallback |
| Billing (live) | 4/10 | 3/10 | Guarded Stripe, not activated |
| Eval as CI gate | 5/10 | 5/10 | Harness exists; not blocking PRs |
| Security posture | 6/10 | 4/10 | Good code; no SOC2/SSO/pentest |
| Legal / trust pack | 4/10 | 3/10 | /trust page exists; no ToS/DPA/Privacy |
| **Overall** | **~68/100** | **~52/100** | Strong bones, unshipped |

---

## 4. Gap analysis — what's missing

**Blocking "it works" (days):**
- Frontend→backend wiring on Vercel (`NEXT_PUBLIC_API_URL` + redeploy) — in progress
- Corpus seeded into Supabase pgvector (seed from laptop; Render free tier has no shell)
- Valid `GEMINI_API_KEY` so answers are real, not stub refusals
- Embedding-dimension consistency between seed + query (both must use Gemini 768-d)

**Retail product depth:**
- Live price quotes + interactive price charts (yfinance is free — fits $0)
- Earnings-call transcripts + AI summaries (free sources: company IR pages, some via yfinance/news)
- Broader well-known ticker universe + a proper watchlist UI (backend alerts exist)
- "Compare two stocks" and "explain this metric" guided flows
- Consumer onboarding, shareable/permalinkable answers, mobile-responsive pass
- Latency masking (Render free cold start ~50s → needs a warm-ping + skeleton UX story)

**RAG quality (high-leverage, $0-friendly):**
- **Contextual Retrieval** (Anthropic technique): prepend an LLM-generated context blurb to each chunk before embedding. −35% to −67% retrieval-failure reductions; ~one-time cost, runs on Gemini free tier. **Biggest single quality win available to you.**
- **Calculator/tool use** for exact arithmetic (don't let the LLM do math) + structured-output extraction for financial figures
- **Eval as a PR-blocking gate** + a 200–500 query regression set on any corpus change
- Defer: ColPali/visual table retrieval (needs GPU — not $0-viable yet)

**SaaS foundations (for monetize track):**
- Activate Stripe billing + surface usage metering to the user
- Legal pack: ToS, Privacy Policy, DPA, public subprocessor list
- "Your data is not used to train models" explicit statement
- EU AI Act Article 50 transparency labels (AI disclosure) — **deadline 2 Aug 2026**
- Status page + trust center polish

**Enterprise / upmarket (deferred — needs time and usually money):**
- SOC 2 Type II (start gap assessment early; 9–15 months to report)
- SSO (SAML/OIDC) + SCIM provisioning; org-level MFA
- Data residency, per-tenant keys/BYOK, SIEM streaming
- 99.95%+ SLA, multi-region DR, pen-testing cadence
- ISO 27001 (if selling internationally / GCC / EU)

---

## 5. The plan — phase by phase

> Numbering continues your existing Phase 0–23 history. Each phase lists **Goal · Deliverables · Acceptance · Effort · $-fit.** Full-time sprint pacing.

### Phase 24 — Make it actually work (LIVE) · 1–2 days · $0
**Goal:** the deployed site answers a real question end-to-end.
- Fix Vercel `NEXT_PUBLIC_API_URL` → Render URL + **redeploy**; set `FRONTEND_ORIGIN` (done in blueprint).
- Add valid `GEMINI_API_KEY` locally + on Render.
- Seed corpus from laptop into Supabase (Gemini 768-d embeddings) for ~15–20 well-known tickers.
- **Acceptance:** `fin-copilot-six.vercel.app/workspace` returns a cited answer to "What risk factors does Apple disclose?" with a route badge and sources.

### Phase 25 — Retail data layer · ✅ DONE (2026-07-13) · $0
**Goal:** the numbers a retail user expects.
- ✅ Live quotes + price history + earnings service (`backend/src/market/quotes.py`), **FMP-primary (cloud-reliable, free tier) with yfinance fallback**, in-process TTL cache, graceful degradation, **DB-independent**.
- ✅ API: `GET /market/quote/{t}`, `/market/history/{t}?range=1M|3M|6M|1Y|5Y`, `/market/earnings/{t}` (`backend/src/api/market_routes.py`).
- ✅ Retail dashboard rewrite: quote header (price, change, mkt cap, P/E, ranges), interactive price chart with range toggle (`PriceViz`, green/red), earnings table (EPS beats/misses + next report date). Market loads **independently of the corpus** so it renders even while the DB is down.
- ✅ 8 new backend tests (152 total green); frontend tsc + vitest green.
- **Requires for live data:** a free `FMP_API_KEY` on the backend (yfinance 429s from datacenter IPs). Sign up free at financialmodelingprep.com.
- _Deferred to a follow-up:_ full earnings-call **transcript** ingestion + LLM summary (needs a transcript source); watchlist UI wiring.

### Phase 26 — RAG quality leap · ✅ DONE (2026-07-13) · $0
**Goal:** measurably better retrieval + exact math.
- ✅ **Contextual Retrieval** (`backend/src/ingestion/contextualize.py`): a situating blurb (ticker/doc-type/section/date) is prepended to every chunk before **embedding and BM25 indexing** — the citation excerpt stays the original text. Deterministic/keyless template path runs offline+CI; an `llm_context()` helper is ready to wire when a key is set. Anthropic's technique, adapted to $0.
- ✅ **Calculator + arithmetic guardrail** (`backend/src/agents/calculator.py`): safe AST evaluator (no `eval`), finance helpers (`percent_change`, `cagr`, `ratio`), and `verify_arithmetic()` wired into the **faithfulness gate** — any explicit `A op B = C` in an answer that doesn't compute now fails the grounding check (a novel trust guardrail beyond citations).
- ✅ 11 new backend tests (163 total green).
- _Upgrade path:_ set an API key → enable `llm_context` for LLM-written context + let the live LLM show arithmetic (auto-verified).

### Phase 27 — Consumer UX + launch polish · ✅ DONE (2026-07-13) · $0
**Goal:** looks and feels like a product a stranger would use.
- ✅ **Shareable answer permalinks**: every answer has a Share button that copies `/workspace?q=…`; a visitor opening that link auto-runs the question (Suspense-wrapped `useSearchParams`).
- ✅ **Cold-start masking**: app-shell fires a keep-warm `/health` ping on mount; the workspace shows an honest "waking the free backend (~50s)" note after 8s instead of a scary error.
- ✅ Mobile: confirmed responsive shell (drawer nav, hamburger), onboarding, suggestion grid, responsive dashboard/charts. Friendlier error copy.
- **Acceptance:** first-time user can ask → share on mobile; shared links re-run the question. ✓

### Phase 28 — Eval as a gate + reliability · ✅ DONE (2026-07-13) · $0
**Goal:** quality can't silently regress.
- ✅ **PR-blocking eval gate** (`backend/tests/test_eval_gate.py`): runs the full agent pipeline over a real FinanceBench sample offline and fails the build if context-hit / citation-coverage / faithfulness drop below committed baselines or refusal-rate spikes. Runs in CI (pytest) → can't merge a regression.
- ✅ **Public status page** (`frontend/app/status/page.tsx`): live checks of API (`/health`), Database (`/ready`), and Market data, with an all-systems banner + refresh; linked in the marketing nav.
- **Acceptance:** a PR that drops faithfulness/context-hit below baseline fails CI. ✓
- _Key-gated (do later):_ Langfuse tracing + Sentry (already guarded; flip on with keys).

### Phase 29 — Monetization foundations · ✅ DONE (keyless parts, 2026-07-13) · $0
**Goal:** the SaaS skeleton that lets you charge later.
- ✅ **Legal pack** (`frontend/app/legal/*`): Terms, Privacy Policy, DPA (GDPR Art. 28), and a live Subprocessors table — shared `LegalShell`, cross-linked, linked from /trust.
- ✅ **"Your data is not used to train models"** stated explicitly in Privacy + DPA.
- ✅ **EU AI Act Art. 50 transparency**: an "AI-generated" chip on every answer + disclosure in Terms.
- ⏸️ **Stripe checkout** — deferred (needs `STRIPE_*` keys; billing code already guarded/wired). Do tomorrow: add keys → test-mode checkout lights up.
- **Acceptance (revised):** legal + transparency shipped; billing activates on key drop.

### Phase 30 — Growth loop · ongoing · $0
**Goal:** something that compounds.
- Public shareable answer pages (SEO), "answer of the day," PostHog funnels (already wired).
- A weekly "earnings recap" email for watchlisted tickers (reuses alert backend).
- **Acceptance:** shared answer pages are crawlable and drive return visits.

### Phase 31+ — Upmarket / enterprise (DEFERRED — needs $ + time)
Start only if you decide to sell to firms: SOC 2 gap assessment, SSO/SCIM, data residency, BYOK, 99.95% SLA + DR, pen-testing, ISO 27001. **Do not build these now** — they add zero value to a retail launch and burn your sprint.

---

## 6. What to skip / defer (and why)
- **ColPali / visual table retrieval** — best-in-class for 10-K tables but GPU-bound; not $0-viable. Revisit if you get paid infra.
- **Finance-native / fine-tuned models** — huge cost, marginal at your scale. General Gemini/Groq is right.
- **Enterprise security machinery (SOC2/SSO/SCIM/DR)** — irrelevant to retail; defer to Phase 31.
- **Proprietary data moats / expert-network automation** — not accessible on $0.
- **Deliverable-into-Excel/PPT generation** — great for the institutional battleground, overkill for retail v1.

---

## 7. Immediate next 3 actions
1. **Finish Phase 24 wiring:** on Vercel, confirm `NEXT_PUBLIC_API_URL = https://fincopilot-api-qypb.onrender.com` (Production) → **Redeploy** → hard-refresh. This alone kills "Backend unreachable."
2. **Get a valid `AIza…` Gemini key** into local `.env` and Render env.
3. **Seed from your laptop:** `cd backend && source .venv/bin/activate && python -m src.ingestion.run --tickers AAPL MSFT AMZN TSLA JPM NVDA META GOOGL --sources edgar market news`

Everything after that is product depth. The bones are strong — the job now is to **ship, seed, and make it feel like Perplexity Finance for the trust-obsessed.**

# FinCopilot v2 — Financial-Depth Roadmap

> Turns FinCopilot from a working MVP into a credible, CFO-grade analysis platform —
> built entirely on **free tiers ($0)**, serving **retail investors first with professional
> depth underneath**, covering **any US-listed ticker on demand**.
>
> This is the *financial-analysis depth* track. The infrastructure / B2B-SaaS track lives
> in [`ROADMAP.md`](./ROADMAP.md); the two are complementary.

**Status:** Plan approved 2026-07-15. Implementation not yet started.
**Sequencing:** Phase 1 → Phase 2 first (data core, then valuation), then Phases 3–7.

---

## Guiding decisions (baked into every phase)

| Decision | Choice |
|---|---|
| **Positioning** | Retail-first UX with a "pro depth" layer underneath (progressive disclosure). |
| **Budget** | Strictly **$0** — free data sources and free hosting only. |
| **Universe** | **Any US filer, on demand** (type a ticker → ingest live). |
| **First priority** | The **Valuation suite** (after the data foundation). |
| **Forward-looking data** | Management **guidance from 8-K earnings releases** + our own model forecast + reverse-DCF implied growth (no paid analyst consensus). |
| **Storage** | Tiered: XBRL **facts always stored** · RAG text chunks **LRU-cached** per recently-viewed ticker · **soft cap** on total companies with an evict-prompt + background reaper. |
| **Auditability** | Every number carries an **as-of date + filing accession** (data lineage) from day one. |

### The insight that makes "$0 + any ticker" feasible
SEC's **`companyfacts` XBRL API** (free, keyless, uncapped) returns **every historical
financial line item for any US filer in a single call** — 10+ years of income statement,
balance sheet, and cash flow. Valuation and ratio analysis therefore work for **any ticker
on demand** with negligible storage (facts are tiny). Only the RAG **text chunks** are
storage-heavy, so those become a lazy, evictable cache.

### Free data source map (everything at $0)

| Need | Free source |
|---|---|
| Multi-year financials (any ticker) | SEC `companyfacts` XBRL API |
| Filing text (10-K / 10-Q / 8-K) | SEC EDGAR (on-demand, keyless) |
| Prices, history, β, market cap | Yahoo v8 chart endpoint |
| Risk-free rate / macro | US Treasury + FRED (free key) |
| Insider / institutional ownership | SEC Form 4 / 13F |
| Debt, covenants, segments | 10-K/Q XBRL + notes |
| "Earnings call" content | 8-K exhibit 99.1 earnings releases (free transcript proxy) |
| Comparable-company multiples | computed from peers' own XBRL + market cap |

### Honest constraints at $0 (with free workarounds)
- **No analyst consensus feed** → anchor forward views on management guidance (8-Ks) + our model.
- **Quotes are EOD/delayed** (no real-time); cold starts remain, mitigated by the keep-warm cron.
- **No full transcripts** → use 8-K earnings releases (results + guidance, no live Q&A).

---

## Flaws this roadmap fixes (finance-professional lens)

**Data foundation**
1. Single filing per company → `risk-diff` can't run; no multi-year trends.
2. No 10-Q / TTM; no full 3-statement structure; no segment or geographic breakdowns.
3. No non-GAAP reconciliation; only 10 mega-caps.

**Valuation**
4. WACC is a hand-set slider (no CAPM); terminal value dominates EV.
5. No reverse DCF, no trading comps, no scenario/Monte Carlo, no ROIC-vs-WACC framing.

**Analysis engine**
6. No ratio suite / DuPont; no Altman Z / Piotroski F / Beneish M; no earnings-quality/accruals.

**Risk & disclosure**
7. Red flags are keyword hits, not materiality assessments; no transcript/tone analysis.

**Capital-markets context**
8. No estimates, ownership (Form 4/13F), debt profile, or capital-allocation view; quotes delayed.

**Portfolio & trust**
9. Portfolio overlap shallow (no factor/concentration/correlation); no as-of lineage; no report export.

---

## Phase 1 — On-demand data core *(foundation; unblocks everything)*

**Goal:** any US ticker becomes fully analyzable in seconds, within free storage limits.

- **Data:** SEC `companyfacts` (all historical XBRL) + EDGAR filing fetch.
- **Backend:**
  - `ingest_on_demand(ticker)` → pull facts, build a structured **3-statement model** (Income Statement / Balance Sheet / Cash Flow).
  - **TTM engine** (trailing-twelve-months from 10-Qs).
  - **Segment & geographic** breakdowns.
  - RAG text chunks fetched **lazily**; **LRU eviction reaper** + **storage-cap guard**.
- **Frontend:** "Add a ticker" flow with ingest progress; works for any filer.
- **Definition of done:** type any ticker → full multi-year financials in <30s; the dead
  `risk-diff` feature runs (2+ years now exist); storage stays under the free cap.

## Phase 2 — Valuation suite *(first priority)*

**Goal:** a real valuation workbench, not a single-slider DCF.

- **Computed WACC (CAPM):** β from price history, risk-free from US Treasury, documented ERP.
- **Reverse DCF:** the growth the market is implying at today's price ("is that realistic?").
- **Trading comps:** auto-selected peers (SIC / entity graph); EV/EBITDA · EV/Sales · P/E · PEG with percentile ranks.
- **Scenario + Monte Carlo** on key drivers; **football-field** valuation chart.
- **ROIC vs WACC** value-creation view; FCFF/FCFE clarity; net-debt bridge.
- **DoD:** Valuation tab shows DCF + reverse-DCF + comps + scenarios, all cited to filed inputs.

## Phase 3 — Analysis engine

- Ratio suite — liquidity, leverage, profitability, efficiency — plus **DuPont** decomposition.
- Credit / quality scores: **Altman Z**, **Piotroski F**, **Beneish M** (earnings manipulation).
- **Earnings quality** — accruals ratio, cash-flow-vs-net-income divergence.
- Common-size statements + CAGR trends.
- New **Financials** and **Health** tabs with retail "what this means" tooltips.

## Phase 4 — Capital-markets layer

- **Ownership:** insider transactions (Form 4) + institutional holders (13F).
- **Debt profile:** maturity wall, coverage, covenants, refinancing risk.
- **Capital allocation:** dividends, buybacks, capex intensity, ROIC vs cost of capital.
- **Guidance extraction** from 8-K earnings releases.

## Phase 5 — Intelligence & alerts

- 8-K earnings-release analysis (results + guidance).
- Management-tone trend across MD&A over time.
- **Materiality-weighted** red flags (not keyword hits).
- New-filing / earnings / threshold alerts (built on the existing cron infra).

## Phase 6 — Portfolio & retail UX

- Portfolio analytics: factor exposure, sector concentration, correlation, VaR-lite.
- "Explain like a retail investor" translation layer.
- **One-click equity-research report export** (PDF / Excel model).

## Phase 7 — Trust & hardening

- Full **data lineage + confidence** surfaced on every extracted number.
- **Screener backtest**.
- Evaluation expansion (FinanceBench + custom valuation checks).

---

## Delivery principles
- Each phase ships independently and is demoable on its own.
- CI stays green; every step is committed and pushed.
- Retail simple-view always present; pro depth behind an "Advanced" disclosure.
- Runs on the existing live **$0 stack**: Supabase → Render → Vercel.

# FinCopilot v2 — UAE Financial-Depth Roadmap

> Turns FinCopilot from a working US-market MVP into a credible, CFO-grade analysis
> platform for the **UAE market** — built entirely on **free tiers ($0)**, serving
> **retail investors first with professional depth underneath**, covering **every
> company listed on the Dubai Financial Market (DFM) and Abu Dhabi Securities
> Exchange (ADX)**.
>
> This is the *financial-analysis depth* track. The infrastructure / B2B-SaaS track
> lives in [`ROADMAP.md`](./ROADMAP.md); the two are complementary.

**Status:** Recalibrated for UAE 2026-07-16 (superseding the 2026-07-15 US-market
version below). Implementation not yet started.
**Sequencing:** Phase 1 → Phase 2 first (data core, then valuation), then Phases 3–7.

> **Region pivot.** The original version of this roadmap assumed the US data
> landscape (SEC EDGAR + free bulk XBRL for any filer). The UAE has no equivalent —
> there is no free, keyless, "any company" financial-facts API. The addressable
> free/public universe is bounded to **exchange-listed companies**, which changes
> the shape of Phase 1 (a full backfill instead of on-demand-only ingestion, no
> eviction cache needed) and Phase 2 (IFRS line items, AED/peg economics, bank- and
> real-estate-heavy sector mix). Everything below is rebuilt around that reality,
> not a find-and-replace of "SEC" with a UAE agency name.

---

## Guiding decisions (baked into every phase)

| Decision | Choice |
|---|---|
| **Positioning** | Retail-first UX with a "pro depth" layer underneath (progressive disclosure). |
| **Budget** | Strictly **$0** — free data sources and free hosting only. |
| **Universe** | Every company listed on **DFM or ADX** (~150–190 tickers combined; exact count to confirm at implementation time). *Not* "any UAE company" — DIFC/ADGM free-zone and private-company financials aren't publicly published, so they're out of scope for on-demand ingestion. |
| **First priority** | The **Valuation suite** (after the data foundation) — but sector-routed, since banks and real-estate names dominate both exchanges and don't value like industrials. |
| **Forward-looking data** | Management guidance from **CMA-mandated company disclosures / board-of-directors reports** via the DFM & ADX newsrooms + our own model forecast + reverse-DCF implied growth (no paid analyst consensus). |
| **Storage** | **Full backfill, not a cache.** The whole listed universe (~150–190 companies × ~10 years of IFRS facts + disclosure text) fits comfortably in Supabase's free tier — no LRU eviction, no soft cap, no reaper needed. This is simpler than the US design, not harder. |
| **Accounting standard** | **IFRS** (as issued by the IASB), not US GAAP — one global taxonomy instead of thousands of company-specific US-GAAP extensions, which should make XBRL parsing *more* consistent, not less. |
| **Currency** | **AED**, hard-pegged to USD at 3.6725 since 1997 — no FX-risk modeling needed, unlike a typical emerging-market pivot. |
| **Sector routing** | Banks/insurers get a **P/B + ROE / excess-return** model; real estate gets **NAV/RNAV + DCF**; everyone else gets standard DCF. Decided now, in Phase 1/2, because it determines the schema Phase 3's ratio/credit-score work has to key off. |
| **Auditability** | Every number carries an **as-of date + DFM/ADX disclosure reference number** (the UAE has no SEC-style "accession number," so the exchange announcement/document ID is the lineage key). |

### Why the universe is bounded, and why that's fine
The US version leaned on SEC's `companyfacts` API to make "any ticker, on demand"
free. The UAE has no such API: the only free, structured, public financial dataset
is the **~150–190 companies listed on DFM and ADX**, filed via the jointly-operated
**XBRL-UAE** e-filing platform (IFRS taxonomy, mandatory for listed issuers) and
backed by each exchange's public disclosure archive (audited annual financials
required within 90 days of fiscal year-end). DIFC companies (DFSA) and ADGM
companies (FSRA) must also file audited IFRS financials, but those go to the
registrar, not a public archive — so they're not usable for a $0, no-key ingestion
pipeline. **Retail investors mostly care about listed shares anyway**, so scoping
to the exchange-listed universe isn't a compromise on the product's audience — and
because that universe is small, we can store *everything*, all the time, instead of
building on-demand ingestion + eviction. That removes a whole layer of complexity
the US roadmap needed.

### Free data source map (everything at $0)

| Need | Free source |
|---|---|
| Multi-year IFRS financials (listed companies) | **XBRL-UAE** e-filing platform (joint ADX + DFM) — access mechanics (bulk/API vs. per-filing) to be validated as the first Phase 1 spike |
| Filing text / material disclosures | ADX **Listed Companies Disclosures** + DFM **Investor Relations** newsroom (PDF announcements, board-of-directors reports) |
| Prices, history, β, market cap | Yahoo Finance `.AE` tickers (DFM coverage confirmed, e.g. `DFM.AE`; ADX ticker-suffix coverage to validate) |
| Risk-free rate | **CBUAE** EIBOR + UAE Federal / T-Sukuk yields (Central Bank open data) |
| Equity risk premium | No local publisher — use **Damodaran's country risk premium** table (UAE row), the standard free industry source, documented as such |
| Bank-specific disclosure | **CBUAE Rulebook** Pillar 3 + individual bank websites (audited financials within 4 months of FYE, IFRS + CBUAE instructions) |
| Corporate tax context (effective-rate input, not a data feed) | Ministry of Finance **Corporate Tax Law** (Federal Decree-Law 47/2022) + FTA administration — 9% above AED 375,000, 0% qualifying free-zone income, 15% top-up for in-scope MNEs |
| Ownership signals | CMA substantial-shareholding disclosures (≥5% stakes) via DFM/ADX announcements — no Form-4/13F-level granularity exists |
| Macro / open data | **Bayanat.ae** (Ministry of Finance open-data portal; has a dataset API) |

### Honest constraints at $0 (with free workarounds)
- **No "any company" bulk API** → universe is capped at DFM + ADX listed companies; free-zone/private companies are out of scope until a paid registry is budgeted.
- **XBRL-UAE bulk/public access is unconfirmed** — the platform is real and mandatory for issuers, but a direct fetch during this research returned a 403; Phase 1's first task is to determine whether it exposes free public/bulk access or whether we fall back to parsing the PDF disclosure archives on ADX/DFM.
- **No analyst consensus feed** → anchor forward views on CMA-mandated disclosures + board reports + our own model, same as the US plan.
- **No earnings-call transcripts** → UAE has no 8-K analogue; use press releases / board-of-directors reports published through the exchange newsrooms.
- **Quotes are EOD/delayed** via Yahoo; the existing cold-start keep-warm mitigation still applies.
- **No FinanceBench-equivalent eval corpus for UAE** — nothing to fix in Phase 1, but its citation/lineage fields must be clean enough that a custom eval set can be hand-built later (Phase 7).

---

## Flaws this roadmap fixes (finance-professional lens, UAE-adjusted)

**Data foundation**
1. Single filing per company → `risk-diff` can't run; no multi-year trends.
2. No quarterly/TTM view; no full 3-statement structure under IFRS; no segment or geographic breakdowns.
3. Only a handful of tickers, all US, all non-financial — no bank/real-estate valuation logic exists at all.

**Valuation**
4. WACC is a hand-set slider (no CAPM); terminal value dominates EV; no sector routing (a DCF run on a bank produces nonsense).
5. No reverse DCF, no trading comps, no scenario/Monte Carlo, no ROIC-vs-WACC framing — and no entity-specific effective-tax-rate handling (mainland vs. free-zone-qualifying vs. MNE top-up).

**Analysis engine**
6. No ratio suite / DuPont; no credit/quality scoring calibrated to IFRS or to bank/real-estate balance sheets; no earnings-quality/accruals view.

**Risk & disclosure**
7. Red flags are keyword hits, not materiality assessments; no tone analysis of board reports.

**Capital-markets context**
8. No estimates, ownership (substantial-shareholding disclosures), debt profile, or capital-allocation view; quotes delayed.

**Portfolio & trust**
9. Portfolio overlap shallow (no factor/concentration/correlation); no as-of lineage; no report export.

---

## Phase 1 — UAE listed-universe data core *(foundation; unblocks everything)*

**Goal:** every DFM- and ADX-listed company fully analyzable, IFRS-based, in a
single free, fully-backfilled, auditable store.

- **Data:** XBRL-UAE e-filing platform (primary) + ADX/DFM public disclosure
  archives (PDF fallback/cross-check for audited annual & interim financials).
- **Backend:**
  - **Spike first:** confirm whether XBRL-UAE exposes free public/bulk access, or
    whether ingestion must parse the ADX/DFM disclosure-PDF archives instead. This
    determines the rest of Phase 1's implementation shape.
  - `ingest_listed_company(ticker, exchange)` → pull IFRS facts → build a
    structured **3-statement model** (Income Statement / Balance Sheet / Cash Flow)
    using IFRS line items (e.g. "Revenue" not "Net Sales"; IFRS lease/impairment
    treatment; Islamic-finance line items — Murabaha, Ijarah, Takaful — for banks
    and insurers).
  - **Full-universe backfill job** (~150–190 companies) rather than on-demand-only
    ingestion — the whole exchange fits the free storage tier, so there's no reason
    to gate it behind a user typing a ticker.
  - **Sector classification** captured at ingestion time (Bank/Insurance · Real
    Estate · Energy · Telecom · everything else) — this routes valuation logic in
    Phase 2 and credit/quality scoring in Phase 3.
  - **Effective-tax-rate field** per entity (9% mainland, 0% qualifying free-zone
    income, 15% top-up where in-scope) captured for FCFF calculations in Phase 2.
  - RAG text from disclosure PDFs (board reports, material announcements) —
    ingested fully per company, no eviction reaper needed given the bounded universe.
- **Frontend:** "Browse UAE-listed companies" search/dropdown over the bounded
  universe, replacing the US MVP's free-text "any ticker" ingest flow — there's no
  free data path for tickers outside DFM/ADX, so the UI shouldn't imply there is.
- **Definition of done:** all DFM + ADX listed companies ingested with multi-year
  IFRS financials; every number traces to a disclosure reference number + as-of
  date; `risk-diff` runs (2+ years of filings now exist per company); storage sits
  comfortably inside the free tier with headroom, no eviction logic required.

## Phase 2 — Valuation suite, sector-routed *(first priority)*

**Goal:** a real valuation workbench tuned to a bank/real-estate/energy-heavy,
IFRS-reporting, currency-pegged market — not a DCF slider that breaks on half the exchange.

- **Computed WACC (CAPM):** β from Yahoo `.AE` price history; risk-free rate from
  CBUAE EIBOR / UAE Federal & T-Sukuk yields; ERP from Damodaran's UAE country risk
  premium table (documented as the source); cost of debt from disclosed interest
  expense/debt under IFRS.
- **Entity-specific effective tax rate** in FCFF — mainland 9%, qualifying
  free-zone income 0%, 15% top-up for in-scope MNEs — instead of a flat US rate.
- **Sector-routed valuation model**, decided at the data layer in Phase 1:
  - **Banks/insurers** → P/B + ROE / excess-return + NII-driven model (a standard
    DCF materially misprices these).
  - **Real estate/construction** → NAV/RNAV-style valuation + DCF.
  - **Everyone else** → standard two-stage DCF, as in the US version.
- **Reverse DCF:** same methodology, AED-denominated — the peg removes the
  FX-risk scenario a typical EM valuation would need.
- **Trading comps:** auto-selected peers from ADX/DFM sector classification —
  viable and meaningful precisely *because* the universe is small (~150–190
  companies), unlike sampling peers out of thousands of US filers.
- **Scenario + Monte Carlo:** include oil-price sensitivity as a standard driver
  given the market's energy exposure; no FX scenario needed (peg); football-field
  valuation chart per sector template.
- **ROIC vs WACC** value-creation view for non-financials; ROE vs cost-of-equity
  for banks; FCFF/FCFE clarity; net-debt bridge.
- **DoD:** Valuation tab shows the sector-appropriate model (bank P/B+ROE, real
  estate NAV+DCF, or standard DCF) + reverse-DCF + comps + scenarios, all cited to
  UAE disclosure references, for every company in the bounded universe.

## Phase 3 — Analysis engine

- Ratio suite — liquidity, leverage, profitability, efficiency — under IFRS line
  items, plus **DuPont** decomposition (ROE variant for banks).
- Credit / quality scores: **Altman Z / Piotroski F / Beneish M** were calibrated
  on US industrials and don't transfer cleanly to UAE banks or real-estate
  developers — this phase needs its own sector-appropriate scoring, to be scoped
  in detail when we get here, using the sector flag Phase 1 already captures.
- **Earnings quality** — accruals ratio, cash-flow-vs-net-income divergence.
- Common-size statements + CAGR trends.
- New **Financials** and **Health** tabs with retail "what this means" tooltips.

## Phase 4 — Capital-markets layer

- **Ownership:** CMA substantial-shareholding disclosures (≥5% stakes) — coarser
  than SEC Form 4/13F, so this phase's ambitions need to match what's actually
  disclosed.
- **Debt profile:** maturity wall, coverage, covenants, refinancing risk (IFRS
  disclosure notes).
- **Capital allocation:** dividends, buybacks, capex intensity, ROIC/ROE vs cost of capital.
- **Guidance extraction** from board-of-directors reports and material disclosures
  (the UAE substitute for 8-K earnings releases).

## Phase 5 — Intelligence & alerts

- Material-disclosure analysis (results + guidance) from the DFM/ADX newsrooms.
- Management-tone trend across board reports over time.
- **Materiality-weighted** red flags (not keyword hits).
- New-filing / earnings / threshold alerts (built on the existing cron infra).

## Phase 6 — Portfolio & retail UX

- Portfolio analytics: factor exposure, sector concentration (meaningful here
  given how bank/real-estate/energy-heavy the exchanges are), correlation, VaR-lite.
- "Explain like a retail investor" translation layer.
- **One-click equity-research report export** (PDF / Excel model).

## Phase 7 — Trust & hardening

- Full **data lineage + confidence** surfaced on every extracted number (DFM/ADX
  disclosure reference + as-of date).
- **Screener backtest**.
- Evaluation expansion — since no UAE FinanceBench exists, this is where a
  custom eval set gets hand-built from the clean citations Phase 1 captured.

---

## Delivery principles
- Each phase ships independently and is demoable on its own.
- CI stays green; every step is committed and pushed.
- Retail simple-view always present; pro depth behind an "Advanced" disclosure.
- Runs on the existing live **$0 stack**: Supabase → Render → Vercel — only the
  data-sourcing and valuation-logic layers change for the UAE pivot.

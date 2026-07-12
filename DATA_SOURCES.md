# DATA_SOURCES.md

**Zero synthetic data.** Every document ingested and every evaluation question used in
FinCopilot comes from a real, public, human-curated source. Nothing is LLM-generated.

## Ingestion corpus (real, public, free)

| Source | What | Access / license | Key required |
| --- | --- | --- | --- |
| **SEC EDGAR** (full-text search + submissions API) | Real 10-K / 10-Q / 8-K filings | Public domain (U.S. government); [fair-access policy](https://www.sec.gov/os/webmaster-faq#developers) — send a descriptive `User-Agent`, ≤10 req/s | No |
| **yfinance** | Prices, fundamentals, statements | Yahoo Finance public data; respect ToS, non-commercial demo use | No |
| **Financial Modeling Prep** (free tier) | Prices, ratios, statements | Free tier: 250 req/day; [terms](https://site.financialmodelingprep.com/terms-of-service) | Optional |
| **GDELT** | News headlines / events | Open data | No |
| **NewsAPI** (dev tier) | Recent headlines | Free dev tier, public articles only; respect ToS | Optional |
| **DFM / ADX public disclosures** | UAE/GCC filings (regional angle) | Public issuer disclosures; note free-access limits | No |

### Ticker set (real companies)

Default corpus (see `FINCOPILOT_TICKERS` in `.env.example`):
`AAPL, MSFT, AMZN, TSLA, JPM, NVDA, META, GOOGL` (US, EDGAR-rich) +
`EMAAR.AE, IHC.AE` (UAE-listed, public disclosures — regional relevance).

## Evaluation corpus (real, peer-reviewed benchmarks — not self-generated)

We evaluate on established public financial-QA benchmarks built from real filings, so
RAGAS numbers are grounded in genuine question sets rather than questions we authored:

| Benchmark | What | Reference |
| --- | --- | --- |
| **FinQA** | Numerical-reasoning Q&A over real earnings reports | Chen et al., 2021 (EMNLP) |
| **TAT-QA** | Hybrid tabular + textual financial QA | Zhu et al., 2021 (ACL) |
| **FinanceBench** | Open-book QA over real public filings, purpose-built for RAG eval | Islam et al., 2023 |

We sample a subset (~50–100 questions) relevant to our ingested tickers. Where a
benchmark's questions don't overlap our default tickers, we additionally ingest that
benchmark's own source filings so the eval is answerable from our corpus. Each
benchmark is used under its published license/terms for research/evaluation.

## Compliance note

No synthetic, scraped-proprietary, or paywalled data is used anywhere in ingestion or
evaluation. All sources above are public and free-tier. This choice is deliberate: a
finance product's evaluation must not be circular (grading itself with its own
generated questions).

# FinCopilot — Forward Roadmap

Current score: **~79/100** (commercial B2B SaaS) · **~92/100** (portfolio). Phases 0–14
shipped (see README build status). This roadmap takes it to a launch-ready,
compliant, multi-tenant product. Four milestones → ten phases.

Legend: ★ critical path · 🔑 needs API keys · 🏗 needs hosting/accounts · ⏳ mostly process.

## M1 — Production-Live

- **Phase 9 — Live LLM + streaming** ★🔑 — real Gemini/Groq answers; SSE `/ask/stream`
  with agent-step events + token streaming; real token counts into metering.
- **Phase 15 — Go live** ★🏗 — deploy Vercel + Render + Supabase; enable pgvector;
  `AUTH_REQUIRED=true`; seed corpus; live URLs + Loom; staging + preview deploys.
- **Phase 16 — Auth, RLS & isolation** ★ — enforce Supabase login; **Postgres
  Row-Level Security** keyed off a per-request org GUC; connection pooling; API-key
  expiry/rotation; cross-tenant pen-test.

## M2 — Scale & Reliability

- **Phase 17 — Async ingestion & scale** — background job queue for uploads
  (`processing→ready`); incremental/Postgres lexical search; pgvector index tuning;
  Redis response/embedding cache; large-PDF handling.
- **Phase 18 — Observability & FinOps** — OpenTelemetry spans per retrieve/rerank/
  generate/judge → Langfuse; per-request cost dashboard; Sentry releases; alerting;
  per-org budget guardrails.
- **Phase 19 — Test & release engineering** — Playwright e2e; Vitest components;
  integration tests (testcontainers pgvector); RAGAS regression in CI (real
  embeddings, threshold-gated); k6 load test; API contract tests.

## M3 — Enterprise & Compliance

- **Phase 20 — Teams, RBAC & SSO** — org invites + seats; RBAC on every route;
  SAML/OIDC SSO; MFA; per-workspace sharing; SIEM audit export; admin console.
- **Phase 21 — Compliance (SOC 2 + EU AI Act)** ⏳ — compliance platform; encryption
  + access reviews + DR/backups; retention/deletion; EU AI Act transparency +
  oversight docs; DPA + subprocessors; SOC 2 Type II window; `/trust` page.

## M4 — Product Depth & GTM

- **Phase 22 — Retrieval & analyst depth** — re-retrieval-on-failure loop; Neo4j
  GraphRAG + Exhibit 21 subsidiaries; cross-company comparison + time series;
  table-aware extraction; real-time corpus refresh; feedback→eval flywheel.
- **Phase 23 — GTM** — hybrid per-seat + usage pricing; public /pricing + self-serve
  trial; onboarding; docs site + API reference + SDK; PostHog analytics; SEO/blog.

## Critical path

```
9 → 15 → 16 ┬→ 17 → 18 → 22
            ├→ 19
            └→ 20 → 21 → 23
```

Quick wins first: keys+smoke-test live · deploy · drop vestigial JSONL audit · real
token counts · theme-flicker fix · conversation-history sidebar.

KPIs: faithfulness, context-hit, answer-match (live), P50/P95 + TTFT, $/query,
activation, trial→paid, seat expansion, churn.

Projected score: M1 → ~84 · M2 → ~88 · M3 → ~93 · M4 → ~96.

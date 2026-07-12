# Security Policy

## Reporting a vulnerability

Please report security issues privately via a GitHub **Security Advisory**
(Security → Advisories → Report a vulnerability) rather than a public issue.
We aim to acknowledge within 72 hours.

## What we do

- **Tenant isolation** — every vector chunk carries a `workspace_id`; retrieval is
  filtered so a tenant can only ever read the shared public corpus plus its own
  data rooms. The unauthenticated `/retrieve` endpoint is scoped to public only.
  In production on Postgres, this is enforced a second time by **Row-Level
  Security** (`backend/src/db/rls.sql`): each request sets `app.current_org` via a
  connection pool, and RLS policies make cross-tenant reads impossible even if
  application code has a bug.
- **Auth** — Supabase JWTs are verified with `SUPABASE_JWT_SECRET`; API keys are
  stored hashed. Set `AUTH_REQUIRED=true` in production to reject anonymous calls.
- **Prompt-injection defenses** — uploaded documents are untrusted; evidence is
  wrapped in an explicit untrusted-content delimiter for the LLM, injection
  patterns are flagged on upload, and the Self-RAG gate blocks ungrounded output.
- **Rate limiting** per principal; **CORS** locked to `FRONTEND_ORIGIN`; security
  response headers on every response.
- **Data rights** — `GET /account/export` and `DELETE /account` (GDPR-style export
  and permanent deletion, including vector purge).
- **Supply chain** — CodeQL scanning (Python + TS) and Dependabot updates.
- **Secrets** — never committed; provided via environment only.

## Not yet in scope (roadmap)

SOC 2 certification, SSO/SAML, field-level encryption, and a formal pen-test.

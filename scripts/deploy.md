# Deployment runbook (free tier, end-to-end)

Two live URLs at the end: a **Vercel** frontend and a **Render** backend, backed by a
**Supabase** Postgres/pgvector project, all auto-deploying from this GitHub repo.

> These steps require **your** accounts (logging in, accepting terms, entering your
> own secret keys). The repo already contains everything needed — `render.yaml`,
> `frontend/vercel.json`, a lean prod Dockerfile, `/health`, and CORS locked to
> `FRONTEND_ORIGIN`. Follow the sequence below.

| Component | Host | Root | Free-tier note |
| --- | --- | --- | --- |
| Frontend (Next.js) | Vercel (Hobby) | `frontend/` | Auto-deploy on push; preview per PR |
| Backend (FastAPI/Docker) | Render (free Web Service) | `backend/` | 512MB RAM; sleeps after 15 min idle → 30–60s cold start (expected) |
| Database (Postgres + pgvector + Auth) | Supabase (free) | — | Enable the `vector` extension |
| Demo mirror (optional) | Hugging Face Docker Space | repo | Single-container "click and it works" link |

---

## 0. Prerequisites (free keys)

- **Google AI Studio** → `GEMINI_API_KEY` — https://aistudio.google.com/app/apikey
- **Groq Cloud** → `GROQ_API_KEY` — https://console.groq.com/keys
- Accounts on **Supabase**, **Render**, **Vercel** (sign in with GitHub).

## 1. Supabase (database + auth)

1. Create a new project (free). Pick a region and a strong DB password.
2. SQL Editor → run:
   ```sql
   create extension if not exists vector;
   ```
   (Or paste `backend/src/retrieval/schema.sql`; `PgVectorStore` also creates the
   table at runtime.)
3. Copy from **Project Settings → API**: `Project URL` (→ `SUPABASE_URL` /
   `NEXT_PUBLIC_SUPABASE_URL`), `anon` key (→ `NEXT_PUBLIC_SUPABASE_ANON_KEY`),
   `service_role` key (→ `SUPABASE_SERVICE_ROLE_KEY`).
4. From **Project Settings → Database → Connection string (URI)**: → `DATABASE_URL`.
5. (Optional Google login) **Authentication → Providers → Google** → enable and add
   your OAuth client; add the Vercel URL to **URL Configuration → Redirect URLs**.

## 2. Render (backend API)

1. **New + → Blueprint** → connect this GitHub repo. Render reads `render.yaml` and
   creates the `fincopilot-api` Docker web service (root `backend/`, health check
   `/health`, auto-deploy on push).
2. In the service's **Environment**, set the secret vars (marked `sync: false`):
   `GEMINI_API_KEY`, `GROQ_API_KEY`, `DATABASE_URL`, `SUPABASE_URL`,
   `SUPABASE_SERVICE_ROLE_KEY`, and `FRONTEND_ORIGIN` (set after step 3, e.g.
   `https://fincopilot.vercel.app`).
3. Deploy. When live, note the URL, e.g. `https://fincopilot-api.onrender.com`.
   Verify: `curl https://fincopilot-api.onrender.com/health` → `{"status":"ok"}`.
4. **Seed the corpus** (Render's disk is ephemeral; the local vector store resets on
   redeploy — set `DATABASE_URL` so vectors persist in Supabase pgvector). From the
   Render **Shell** (or locally against the same `DATABASE_URL`):
   ```bash
   python -m src.ingestion.run --tickers AAPL MSFT --sources edgar market news
   ```

## 3. Vercel (frontend)

1. **Add New → Project** → import this repo → set **Root Directory** to `frontend/`.
   Framework preset **Next.js** is auto-detected.
2. **Environment Variables**:
   - `NEXT_PUBLIC_API_URL` = the Render URL from step 2.3
   - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (optional — without
     them the app runs in demo mode)
3. Deploy → note the URL, e.g. `https://fincopilot.vercel.app`.
4. Go back to Render and set `FRONTEND_ORIGIN` to this Vercel URL (locks CORS), then
   redeploy the backend.

## 4. Wire it up & verify

1. Open the Vercel URL → **Workspace** → ask "What risk factors does Apple disclose?"
   → confirm a cited answer with a route badge (allow ~30–60s on the first request
   while Render cold-starts).
2. Check `/dashboard`, `/audit`, `/evaluation` load live data from the API.
3. Add both live URLs to the top of `README.md`.

## 5. (Optional) Hugging Face Space mirror

Create a **Docker Space**, point it at this repo's `backend/`, set the same env
vars — a single-container link with no cold-start caveat to explain.

---

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR: backend `ruff` + `pytest` (fully
offline — no keys), frontend `lint` + `tsc` + `build`. `docker-build.yml` verifies
the backend image builds on push to `main`. Render and Vercel handle the actual
deploys via their own GitHub integrations (no secrets in Actions required).

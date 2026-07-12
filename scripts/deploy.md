# Deployment (free tier, all connected via GitHub auto-deploy)

Detailed steps are executed in **Phase 8**. Summary of the target topology:

| Component | Host | Root | Notes |
| --- | --- | --- | --- |
| Frontend (Next.js) | **Vercel** (Hobby) | `frontend/` | Auto-deploy on push to `main`; preview URL per PR |
| Backend API (FastAPI/Docker) | **Render** (free Web Service) | `backend/` | 512MB RAM; spins down after 15 min idle → 30–60s cold start (expected, documented) |
| Database (Postgres + pgvector + Auth) | **Supabase** (free project) | — | Enable the `vector` extension |
| Graph DB (Phase 9 only) | **Neo4j AuraDB Free** | — | MVP uses in-process NetworkX |
| Demo mirror (optional) | **Hugging Face Docker Space** | repo | Single-container "click and it works" link |

## Steps

1. **Supabase** — create a free project → SQL editor: `create extension if not exists
   vector;` → copy the connection string + anon/service keys into host env vars.
2. **Render** — new Web Service → connect the GitHub repo → root `backend/` → Docker →
   set env vars (`GEMINI_API_KEY`, `GROQ_API_KEY`, `DATABASE_URL`, `SUPABASE_*`) →
   health check path `/health` → auto-deploy on push to `main`.
3. **Vercel** — import the GitHub repo → root `frontend/` → set `NEXT_PUBLIC_API_URL`
   to the Render URL and the `NEXT_PUBLIC_SUPABASE_*` vars → auto-deploy on push.
4. **(Optional)** mirror to a Hugging Face Docker Space for a no-cold-start demo link.
5. Add both live URLs to the top of `README.md`.

## Environment variables per host

See `.env.example` for the full list. Never commit real values.

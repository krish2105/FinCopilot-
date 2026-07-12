# FinCopilot frontend

Premium dark-mode-first research dashboard — Next.js 14 (App Router) · TypeScript ·
Tailwind · Recharts · framer-motion · Supabase Auth. Talks to the FastAPI backend.

## Run

```bash
npm install
cp ../.env.example .env.local   # set NEXT_PUBLIC_API_URL (+ optional Supabase keys)
npm run dev                     # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` to the backend origin (default `http://localhost:8000`).
Supabase keys are optional — without them the app runs in **demo mode** (no login
gate), which is ideal for the portfolio demo.

## Screens

- `/` — landing (hero, sample cited answer, how-it-works, features)
- `/login` — Supabase Auth (email + Google) with demo-mode fallback
- `/workspace` — chat research: citation chips, source panel, RAG route badge,
  findings, compliance flags, charts, faithfulness bar, the calm
  "insufficient evidence" state, and a live provider trace
- `/dashboard` — corpus + entity-graph analytics and per-ticker key figures
- `/audit` — the structured audit trail
- `/evaluation` — RAGAS metric gauges (numbers land in Phase 7)

## Theme

Semantic CSS-variable tokens power a light/dark toggle with a smooth cross-fade and
AA-contrast in both themes. Emerald = verified/cited, amber = insufficient evidence,
red = compliance danger; each RAG route has its own hue.

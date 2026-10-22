# Vercel demo deployment

A **showcase only** — not the product backend. It exists so stakeholders can
open a real URL and see the foundation's status plus an interactive simulation
of the conversation-control rules. Chatwoot, PostgreSQL, workers, and any live
messaging do **not** run on Vercel (they need a persistent host — see roadmap).

## What's deployed
- `public/` — static page (project status + in-browser simulation of
  `domain/conversation.py` rules; clearly labelled as a demo).
- `api/health.py` — stdlib-only Python serverless function returning honest
  status JSON (`demo: true`, `live_messaging: false`, core version when the
  package is importable).
- `vercel.json` — no framework/build step; serves `public/`, basic security headers.

## Deploy (account owner, ~2 minutes)
1. vercel.com → sign in with GitHub → **Add New → Project** → import
   `iciiex/comu-center`.
2. Keep defaults (the repo's `vercel.json` configures everything) → **Deploy**.
3. Production deploys track `main`; every PR gets a Preview URL automatically
   (once the Vercel GitHub app is installed on the repo).

Do not add production secrets to the Vercel project for this demo — it needs
none. Never share Vercel tokens in chat/issues.

## Local preview
```bash
python3 -m http.server 3000 --directory public --bind 0.0.0.0
# open http://localhost:3000  (the /api/health badge will report "unavailable"
# locally unless you run `vercel dev`, which serves both static + functions)
```

## Honesty rules for this page
The demo must never imply a live Instagram/AI connection. When real components
land (persistence, Chatwoot live spike), update the status cards in
`public/index.html` in the same PR as the feature.

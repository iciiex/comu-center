# Local development

Prerequisites: Python 3.11+, `make`. Docker is optional (database skeleton).

```bash
make setup     # .venv + `pip install -e ".[dev]"`
make check     # ruff + mypy + pytest + config-check  (must be green before PRs)
make test      # pytest only
cp .env.example .env    # safe defaults: AI send OFF, Meta live OFF, product=damiish
.venv/bin/python -m invar_comms health
.venv/bin/python -m invar_comms config-check
.venv/bin/python -m invar_comms db-init     # create the local SQLite store
```

Run the HTTP intake + worker locally (no live messaging; unconfigured webhook
routes correctly return 503 until their secrets/mappings are set):

```bash
INVAR_CHATWOOT_WEBHOOK_SECRET=dev-only INVAR_CHATWOOT_INBOX_MAP=7=damiish:instagram:ig-acct-1 \
  .venv/bin/python -m invar_comms serve     # http://127.0.0.1:8000/health
.venv/bin/python -m invar_comms worker      # drain queued webhook jobs once
```

Notes:
- The core has **no runtime dependencies** — tests exercise real contracts with
  fakes (`adapters/fakes.py`), so no network, DB, Meta app, or AI key is needed.
- Docker: `docker compose config` validates; `docker compose up db` starts
  PostgreSQL 16 (volume `invar_pgdata`, healthcheck `pg_isready`). The DB port
  is **not** published by default — uncomment the localhost-only mapping in
  `compose.yaml` for debugging. The `core` service is a CLI skeleton (no HTTP
  server yet), so nothing is reachable from a browser yet.
- Verified on 2026-10-22 in the foundation sandbox: pytest 29 passed, ruff and
  mypy clean, pip-audit clean (after upgrading the venv's setuptools — the
  Makefile/CI do this). Docker itself was **not** available in that sandbox, so
  compose startup is *unverified* until run on a Docker host.

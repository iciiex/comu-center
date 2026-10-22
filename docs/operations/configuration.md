# Configuration reference

All settings come from environment variables (`.env` locally; the hosting
platform later). Loaded & validated by `invar_comms.config.load_settings`;
inspect safely with `python -m invar_comms config-check` (secrets redacted).

| Variable | Default | Notes |
|---|---|---|
| `INVAR_ENV` | `local` | `local` \| `test` \| `production` (production = stricter validation) |
| `INVAR_ENABLED_PRODUCTS` | `damiish` | Comma-separated product scope for this deployment |
| `INVAR_AI_SEND_ENABLED` | `false` | Global AI-send kill-switch. Off = suggestions/escalation only |
| `INVAR_META_LIVE_SEND_ENABLED` | `false` | Second, separate switch; requires AI-send on + all Meta secrets, else startup error |
| `INVAR_DATABASE_URL` | *(unset)* | Required in production before AI sending (audit persistence) |
| `INVAR_SQLITE_PATH` | `data/invar_comms.sqlite3` | Local dev/test store only (ADR-0008); create with `python -m invar_comms db-init` |
| `INVAR_META_APP_SECRET` | *(unset)* | Webhook signature verification |
| `INVAR_META_WEBHOOK_VERIFY_TOKEN` | *(unset)* | Webhook subscription handshake |
| `INVAR_META_ACCESS_TOKEN` | *(unset)* | Send API (future adapter) |
| `INVAR_CHATWOOT_BASE_URL` | *(unset)* | Chatwoot deployment URL (ADR-0007; empty until live spike) |
| `INVAR_CHATWOOT_BOT_TOKEN` | *(unset)* | Agent Bot access token (least-privilege; secret) |
| `INVAR_CHATWOOT_WEBHOOK_SECRET` | *(unset)* | Verifies signed Chatwoot webhooks (secret); webhook route returns 503 while unset |
| `INVAR_CHATWOOT_INBOX_MAP` | *(unset)* | `7=damiish:instagram:ig-acct-1,...` — inbox→product binding, validated at startup |
| `INVAR_HTTP_HOST` / `INVAR_HTTP_PORT` | `127.0.0.1` / `8000` | Bind for `python -m invar_comms serve`; use `0.0.0.0` only behind TLS/proxy |
| `INVAR_AI_PROVIDER_NAME` | `fake` | `fake` until a provider is selected via ADR |
| `INVAR_AI_PROVIDER_API_KEY` | *(unset)* | Never required by the domain core |

Validation failures exit non-zero with a message naming the rule — fix the
environment, never weaken validation to get a green start.

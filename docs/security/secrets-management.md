# Secrets management

## Rules
1. Secrets live in the environment / a secrets manager — **never in git**,
   issues, chat, screenshots, or logs. `.env.example` contains placeholders only;
   `.gitignore` blocks `.env*` (except the example) and key files.
2. One secret per purpose, per environment (local/test/production are distinct).
3. Least privilege: Meta tokens scoped to the DAMIISH pilot app/account only;
   DB user without superuser; AI-provider keys with spend caps where offered.
4. Config output is redacted by design (`Settings.redacted_summary`,
   `repr=False` on secret fields) — keep it that way in new code.

## Lifecycle
- **Create**: generate in the provider console (Meta/AI/hosting), store
  immediately in the manager; the person creating it records *where* it lives
  (not its value) in the team's password manager.
- **Rotate**: Meta app secret & access tokens on staff changes and at least
  quarterly once live; DB/passwords with platform tooling. Webhook verify
  token rotation = update Meta app + env together during a quiet window.
- **Revoke**: any suspected exposure → revoke/rotate *first*, then investigate
  (git history is forever — rewriting it is not a remediation).
- **Decommission**: removing a channel/product revokes its tokens the same day.

## Tooling path
Local: `.env` file (uncommitted). First hosted environment: the platform's
secret store (e.g. host env vars / SOPS / cloud secret manager — choose with
the hosting decision, record an ADR). CI uses GitHub Actions secrets/OIDC;
the foundation CI needs no secrets at all.

# Deployment Architecture

- Status: **PROTOTYPE ONLY** — local/dev process; production topology `OPEN`.
- Mode: P

## Today
- `uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000`
- SQLite file `var/kiloos.db`; evidence under `var/evidence/` (both gitignored).
- Config via environment: `KILOOS_ENV`, `KILOOS_DB`, `KILOOS_EVIDENCE_DIR`, `KILOOS_SECRET` and the
  limits listed in `docs/operations/runbook.md`. The app does not load a `.env` file.
- Already in place for the demo: CSRF field on every form, rate limit on demo login (in memory, per
  process), security headers.
- CI: lint + tests + app boot check (`.github/workflows/ci.yml`). Its secret-scan step cannot fail
  (backlog A10); `make doctor` is the working secret check.

## Before any real user
- PostgreSQL + managed backups + tested restore.
- Object storage (S3-compatible) with signed URLs for evidence.
- HTTPS termination, `Secure` session cookie, removal of the `?s=` session transport (D-002), a rate
  limiter that works across processes.
- Container image and pinned dependencies (backlog A7, D1).
- Staging environment close to production; rollback procedure.
- RPO/RTO and retention: `OPEN` (OD-12 / doc 11).

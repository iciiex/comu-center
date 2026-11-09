# Deployment Architecture

- Status: **PROTOTYPE ONLY** — local/dev process; production topology `OPEN`.
- Mode: P

## Today
- `uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000`
- SQLite file `var/kiloos.db`; evidence under `var/evidence/` (both gitignored).
- Config via environment: `KILOOS_ENV`, `KILOOS_DB`, `KILOOS_EVIDENCE_DIR`, `KILOOS_SECRET`.
- CI: lint + tests (`.github/workflows/ci.yml`).

## Before any real user
- PostgreSQL + managed backups + tested restore.
- Object storage (S3-compatible) with signed URLs for evidence.
- HTTPS termination, secure cookies, CSRF, rate limiting.
- Staging environment close to production; rollback procedure.
- RPO/RTO and retention: `OPEN` (OD-12 / doc 11).

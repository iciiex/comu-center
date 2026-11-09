# Runbook (prototype)

## Start / stop
```bash
make run     # uvicorn on 0.0.0.0:8000
# stop: Ctrl+C or kill the uvicorn process
```

## Health
```bash
curl -s localhost:8000/health
```
Expect `{"status":"ok","mode":"P",...}`.

## Reset demo data
```bash
make seed    # deletes var/kiloos.db, reseeds on next start
```
This is destructive and only for dev/demo. Never run against real data.

## Configuration (environment)
| Variable | Default | Meaning |
|---|---|---|
| `KILOOS_ENV` | `dev` | `dev`/`test` allow the fallback secret; anything else requires `KILOOS_SECRET` |
| `KILOOS_SECRET` | dev fallback | HMAC key for session + CSRF tokens (must be stable, ≥32 chars) |
| `KILOOS_DB` | `var/kiloos.db` | SQLite file |
| `KILOOS_EVIDENCE_DIR` | `var/evidence` | private evidence storage |
| `KILOOS_SESSION_TTL` | `43200` (12h) | session/token lifetime in seconds |
| `KILOOS_LOGIN_RATE_LIMIT` / `KILOOS_LOGIN_RATE_WINDOW` | `10` / `60` | demo-login attempts per IP per window |
| `KILOOS_EVIDENCE_RETENTION_DAYS` | `90` (SAMPLE, D-003) | purging window for evidence |
| `KILOOS_QUEUE_PAGE_SIZE` | `20` | review queue page size |
| `KILOOS_SALES_MAX_BYTES` / `KILOOS_SALES_MAX_ROWS` | `5242880` / `5000` | sales XLSX upload limits |

Changing `KILOOS_SECRET` invalidates every session (including `?s=` links already open).

## Evidence retention (manual, D-003)
```bash
.venv/bin/python -m app.maintenance purge-evidence --dry-run   # report only
.venv/bin/python -m app.maintenance purge-evidence             # delete older than the policy
.venv/bin/python -m app.maintenance purge-evidence --days 30   # override the window
```
Deletes the file and the `submission_evidences` row, and writes an `audit_logs` row
(`action='evidence.purged'`) with `submission_id`, `sha256`, `storage_path`. There is **no scheduler**;
the 90-day default is a sample value until the employer approves a policy.

## Sales import (admin)
```bash
python -m app.sample_sales        # var/sales-sample.xlsx (SAMPLE: 4 valid, 1 duplicate, 1 unmapped)
```
Upload at `/admin/sales/new`, check the row report, then press «پردازش».

| Symptom | Cause | Action |
|---|---|---|
| «این فایل قبلاً آپلود شده است» (409) | same bytes already imported (`file_sha256`) | open the existing import; no need to re-upload |
| all rows `E_USER_MAPPING` | `sales_user_map` has no entry for that org | add the mapping (explicit) before processing |
| `?processed=0` | nothing valid left (already scored or no valid rows) | expected on re-run; check the row report |
| red reconciliation banner | counts or points disagree | do not trust the import; inspect `sales_records` before using the points |

## Backup (prototype)
```bash
cp var/kiloos.db "var/backup-$(date +%F).db"
tar czf "var/evidence-$(date +%F).tgz" var/evidence
```
A backup is not considered valid until a restore has been tested.

## Restore (prototype)
Stop the app, copy the backup over `var/kiloos.db`, restore evidence, start, verify `/health`,
one mission, and one score record.

## Common issues
| Symptom | Cause | Action |
|---|---|---|
| `401`/redirect loop | cookie secret changed | re-login; keep `KILOOS_SECRET` stable |
| login lands back on `/login` in an embedded preview | third-party cookie blocked | expected: the `?s=` fallback handles it (D-002); check the URL carries `?s=` |
| `403` «اعتبار فرم منقضی شده» | CSRF token missing/stale (form from an old tab or another session) | reload the page and resubmit |
| `429` on login | rate limit hit | wait one window (`KILOOS_LOGIN_RATE_WINDOW`) or raise the limit in dev |
| `no such table` | DB path points to a new file | restart (init creates schema + seed) |
| `database is locked` | concurrent writers on SQLite | prototype limitation; serialize or move to PostgreSQL |
| evidence 404 | file removed from `var/evidence` | restore from backup; audit the deletion |

## Escalation
Prototype has no on-call. Record incidents in `docs/handoffs/current-state.md`; production
incident process is `OPEN` (doc 11).

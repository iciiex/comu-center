# Runbook (prototype)

## Start / stop
```bash
make run     # uvicorn on 0.0.0.0:8000
# stop: Ctrl+C or kill the uvicorn process
```

`make run` reads the process environment, not a `.env` file by itself. Demo access is **off by default**.
For a local Play rehearsal, set the following in the shell or use your environment/secret manager:

```bash
export KILOOS_ENV=dev KILOOS_DEMO_MODE=play
export KILOOS_DB="$(mktemp -d)/isolated-legacy.sqlite3"
# Enter a separate random 32+ character credential saved securely by the demo operator.
read -rs KILOOS_DEMO_OPERATOR_KEY; export KILOOS_DEMO_OPERATOR_KEY
make run
```

Open `http://localhost:8000/play/admin/login` for direct local rehearsal. Use HTTPS for other
hosts, with a trusted proxy passing the original Host and scheme. Do not log credentials or
share the operator key with participants. Use the admin’s demo account chooser to issue a one-use
code per participant, and open each account in a separate browser profile. A room link does not
sign anyone in. Rotate the operator key and restart to invalidate demo sessions/codes as needed.

For **legacy Club** rehearsal instead, use a separate process/host and synthetic database/evidence
paths, set `KILOOS_DEMO_MODE=legacy`, and use a different operator key. `/login` in this mode shows
only the seed set; staff need the key. Play and the old login are never enabled on the same process.

## Health
```bash
curl -s localhost:8000/health
```
Expect `{"status":"ok","mode":"P",...}`.

## Reset demo data
```bash
make seed    # deletes var/kiloos.db, reseeds on next start
```
This is destructive and only for the legacy dev/demo. Never run against existing customer data. Play reset uses the authenticated control center/confirmation and only its marked Play store; do not use `make seed` for Play.

## Configuration (environment)
| Variable | Default | Meaning |
|---|---|---|
| `KILOOS_ENV` | `dev` | `dev`/`test` allow the fallback secret; anything else requires `KILOOS_SECRET` |
| `KILOOS_SECRET` | dev fallback | Stable signing/CSRF configuration; use ≥32 random characters |
| `KILOOS_DEMO_MODE` | `off` | `play` or `legacy` enables one isolated demo in dev/test only |
| `KILOOS_DEMO_OPERATOR_KEY` | unset | Demo operator access/control; separate random 32+ chars required when a demo is enabled |
| `KILOOS_DB` | `var/kiloos.db` | SQLite file |
| `KILOOS_EVIDENCE_DIR` | `var/evidence` | private evidence storage |
| `KILOOS_SESSION_TTL` | `43200` (12h) | session/token lifetime in seconds |
| `KILOOS_LOGIN_RATE_LIMIT` / `KILOOS_LOGIN_RATE_WINDOW` | `10` / `60` | demo-login attempts per IP per window |
| `KILOOS_EVIDENCE_RETENTION_DAYS` | `90` (SAMPLE, D-003) | purging window for evidence |
| `KILOOS_QUEUE_PAGE_SIZE` | `20` | review queue page size |
| `KILOOS_SALES_MAX_BYTES` / `KILOOS_SALES_MAX_ROWS` | `5242880` / `5000` | sales XLSX upload limits |

Changing `KILOOS_DEMO_OPERATOR_KEY` invalidates demo cookies and unused Play entry codes. Changing `KILOOS_SECRET` invalidates legacy sessions and previously rendered Play CSRF forms.

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
Or use the admin-only download link on `/admin/sales/new` (`GET /admin/sales/sample`).
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
| `401` at `/login` | no mode or active authenticated session | enable only the required isolated demo for rehearsal; do not enable either mode on a live non-demo host |
| Login `403` on alternate hostname | credential transport/origin mismatch | use HTTPS, preserve the public Host and scheme in the trusted proxy, or open direct loopback locally |
| login lands back on `/login` in an embedded preview | third-party cookie blocked | in the isolated `legacy` demo only, check `?s=` (D-002); for Play use the partitioned HTTPS cookie or open the host top-level |
| `403` «اعتبار فرم منقضی شده» | CSRF token missing/stale (form from an old tab or another session) | reload the page and resubmit |
| `429` on login | rate limit hit | wait one window (`KILOOS_LOGIN_RATE_WINDOW`) or raise the limit in dev |
| `no such table` | DB path points to a new file | restart (init creates schema + seed) |
| `database is locked` | concurrent writers on SQLite | prototype limitation; serialize or move to PostgreSQL |
| evidence 404 | file removed from `var/evidence` | restore from backup; audit the deletion |

## Repository health and generated documents
```bash
make doctor      # structure, current-state freshness, decision statuses, secret patterns
make docs        # regenerate docs/agent-guide/code-map.md and traceability.md
make docs-check  # fail if they are stale
make graph       # rebuild graphify-out/ when sources changed (first run installs graphify from PyPI)
```
Developer problems (setup, failing checks, test helpers): `docs/agent-guide/troubleshooting.md`.
Demo day procedure: `docs/delivery/demo-script.md`.

## Escalation
Prototype has no on-call. Record incidents in `docs/handoffs/current-state.md`; production
incident process is `OPEN` (doc 11).

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
| `no such table` | DB path points to a new file | restart (init creates schema + seed) |
| `database is locked` | concurrent writers on SQLite | prototype limitation; serialize or move to PostgreSQL |
| evidence 404 | file removed from `var/evidence` | restore from backup; audit the deletion |

## Escalation
Prototype has no on-call. Record incidents in `docs/handoffs/current-state.md`; production
incident process is `OPEN` (doc 11).

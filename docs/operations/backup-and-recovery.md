# Backup & recovery

Applies once PostgreSQL holds real data (PoC task 2 onward). Written now so
the first deployment inherits the habit, not the incident.

## What to back up
- PostgreSQL (messages, conversations, knowledge, audit) — `pg_dump` custom
  format, nightly, encrypted, off-host copy. Keep 14 daily + 4 weekly to start;
  retention of *customer content* must also satisfy the privacy/retention
  policy (legal decision pending — backups older than the retention limit must
  be deleted too).
- Configuration *names* + secrets live in the secrets manager (its own backup);
  never dump secrets into the DB backup job.
- Chatwoot (if adopted): its Postgres/Redis/attachments per upstream guidance.

## Local example (Docker dev)
```bash
docker compose exec db pg_dump -U invar -d invar_comms -Fc > backups/invar-$(date +%F).dump
docker compose exec -T db pg_restore -U invar -d invar_comms --clean < backups/invar-YYYY-MM-DD.dump
```

## Recovery discipline
1. A backup is unproven until restored: quarterly restore drill into a scratch
   instance + row-count/`config-check` sanity; record date & result here.
2. Restore order: DB → app config/secrets → webhook re-subscription check →
   kill-switches stay **off** until a human verifies state, then enable.
3. RPO/RTO targets are set at production-readiness review (roadmap Phase 2);
   the pilot target is "no silent loss of audit events" ahead of speed.

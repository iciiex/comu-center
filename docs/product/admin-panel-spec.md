# Admin Panel Specification (prototype)

- Status: **PARTIAL** — implemented scope below; full spec is doc 09.
- Mode: P

## Implemented
- Review queue by status with evidence count; review screen with private evidence, approve/reject.
- Mission list with status; create draft; edit; publish; archive.
- Changing points publishes a new rule version (old version retired).
- Every admin action writes to `audit_logs`.

## Not implemented
- Users/roles management, organization tree, scoring-rule editor (only via mission points),
  sales imports, competitions, reports, settings, exports.

## Access model
`permission × organization scope`, enforced server-side. Operator: queue only. Admin: missions.

## Open
Which roles exist in MVP (OD-10) and the final permission matrix.

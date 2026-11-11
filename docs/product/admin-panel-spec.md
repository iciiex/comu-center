# Admin Panel Specification (prototype)

- Status: **PARTIAL** — implemented scope below; full spec is doc 09.
- Mode: P

## Implemented
- Review queue by status with evidence count; review screen with private evidence, approve/reject.
- Mission list with status; create draft; edit; publish; archive.
- Changing points publishes a new rule version (old version retired).
- Sales import (admin): XLSX upload, row report, explicit processing, reconciliation
  (`docs/engineering/sales-import.md`).
- Score correction (admin): the form is on the submission page `/submissions/{id}` only; no
  admin screen links to it yet, and it fails for sales events (backlog A2).
- Every admin action writes to `audit_logs`.

## Not implemented
- Users/roles management, organization tree, scoring-rule editor (only via mission points),
  sales visitor-mapping management, competitions, reports, settings, exports.

## Access model
`permission × organization scope`, enforced server-side.

| Role | Review queue | Missions | Sales import | Score correction |
|---|---|---|---|---|
| Operator | review, approve, reject | read-only list | no (403) | no (403) |
| Admin | review, approve, reject | create, edit, publish, archive | yes | yes |

Exact guard of every route: `docs/agent-guide/code-map.md` §2.

## Open
Which roles exist in MVP (OD-10) and the final permission matrix.

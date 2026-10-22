# Contributing

## Workflow

1. Branch from `main` (`feature/...`, `fix/...`, `docs/...`). Never commit
   directly to `main`.
2. Small, meaningful commits with imperative messages
   (`feat:`, `fix:`, `docs:`, `chore:`, `test:`).
3. Run `make check` before opening a PR. CI must be green; a skipped or
   weakened check is a review blocker, not a detail.
4. PRs describe: problem, change, tests run, risks, and any docs/ADR updates.
5. Material architecture decisions get an ADR in `docs/architecture/decisions/`.

## Engineering rules (non-negotiable)

- Domain core (`invar_comms/domain`) stays free of I/O, frameworks, and
  provider SDKs. Dependencies point inward: adapters → ports → domain.
- No secrets in git, ever. Config via environment; `.env.example` holds only
  placeholders. See `docs/security/secrets-management.md`.
- Fail closed: authorization, eligibility, and webhook verification deny on
  doubt. New external input is untrusted input.
- Anything that can send to a customer needs: an authorization check, the
  conversation-control guard, an audit event, and a test proving the blocked
  path as well as the happy path.
- Product data stays product-scoped. No cross-product queries without an ADR.
- Prefer mature open source over rebuilding commodity features — but evaluate
  licenses first and record findings in `docs/open-source-evaluation.md`.
- No third-party code is copied into this repo without a license check.

## Tests

Write tests for behavior and invariants (especially safety guards), not for
coverage numbers. A guard without a "blocked" test is unfinished work.

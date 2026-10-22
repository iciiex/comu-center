# Security policy

## Reporting

Report suspected vulnerabilities privately to the Invar engineering owners
(channel to be confirmed by the owners — do not open a public issue for
anything exploitable). Include reproduction steps and impact; expect an
acknowledgement within two business days once the private channel exists.

## Scope notes

- This repository is a **foundation**: it processes no production customer data
  and has no live external integrations yet.
- Security requirements and the initial threat model live in `docs/security/`.
- Secrets handling: `docs/security/secrets-management.md`. Any credential found
  in git history must be treated as compromised: rotate first, investigate after.

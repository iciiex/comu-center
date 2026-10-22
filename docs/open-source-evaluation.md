# Open-source & third-party evaluation

Verified 2026-10-22 against vendor docs/license files (URLs below).
**Re-verify every license, edition split, and price at adoption time** — they
change. Nothing below is legal advice; material adoptions need owner/legal sign-off.
No third-party code is vendored in this repository.

## Summary

| Candidate | Verdict | License (verified) | Why |
|---|---|---|---|
| Chatwoot Community Edition | **Adopt as direction; spike first** (ADR-0002) | MIT Expat for community code; `enterprise/` directory is proprietary & paid [1] | Saves building a commodity inbox; self-hostable; exit = replace adapter |
| Dify | **Deferred** (ADR-0005) | Modified Apache-2.0: multi-tenant operation needs written authorization; frontend branding clause [2] | Conflicts with multi-product trajectory; not needed for PoC |
| n8n | **Deferred** (ADR-0005) | Sustainable Use License (fair-code, not OSI): internal use OK; hosting for customers restricted; EE code paid [3] | No workflow need yet; avoid entanglement |
| PostgreSQL 16 | **Adopt as direction** (ADR-0003) | PostgreSQL License (permissive) | Transactions, FTS, one backup story |
| Python 3.11 + stdlib | **Adopted** (ADR-0001) | PSF License | Core has zero runtime deps |
| Dev tooling (pytest/ruff/mypy/pip-audit) | Adopted (dev-only) | MIT / MIT / MIT / Apache-2.0 resp. | Not shipped in the runtime |

## Per-candidate notes

### Chatwoot CE — purpose, burden, boundary, exit
- Purpose: operator inbox (queues, assignment, channel plumbing, canned replies).
- Burden: self-hosted Rails + PostgreSQL + Redis + Sidekiq; vendor guidance is
  roughly 2 CPU / 4 GB RAM minimum; upgrades + backups are ours. CE excludes
  Captain AI, SSO/SAML, SLA policies, custom roles/permissions, audit logs
  (paid tiers) [1][4] — our core therefore enforces authorization/audit itself.
- Boundary: external system via API + webhooks only; no Invar logic inside it;
  use CE images (`-ce`) / community code paths only.
- Exit: switch inbox adapter; export conversations via API/DB.
- Open questions for the spike: CE webhook/API sufficiency for takeover
  semantics; Instagram channel behavior vs. our direct Meta adapter (pick one
  owner of the Meta connection — do not double-connect); current CE image
  version pinning & upgrade path.

### Dify — if revisited
Internal single-tenant experimentation appears permitted, but Invar's
multi-product/customer ambitions approach the multi-tenant clause [2].
Any future use: internal-only, behind `AIProvider` port, written license
confirmation for the exact deployment shape first.

### n8n — if revisited
Internal automations appear permitted under the SUL [3]; customer-facing
hosting/workflow-building is the restricted zone. Adopt only for a named
internal workflow, never as core architecture.

### AI providers — not yet selected
Selection criteria when the PoC needs one: data-processing terms (no training
on customer data; retention/deletion), regional processing, Persian-language
quality, cost per resolved conversation, and an easy exit via the
`AIProvider` port. **No provider is a dependency of the domain layer.**

## Sources
1. Chatwoot LICENSE (MIT Expat outside `enterprise/`): https://github.com/chatwoot/chatwoot/blob/develop/LICENSE · editions/pricing: https://www.chatwoot.com/pricing/self-hosted-plans
2. Dify LICENSE (modified Apache-2.0): https://github.com/langgenius/dify/blob/main/LICENSE
3. n8n Sustainable Use License FAQ: https://docs.n8n.io/privacy-and-security/sustainable-use-license · LICENSE.md: https://github.com/n8n-io/n8n/blob/master/LICENSE.md
4. Chatwoot developer FAQ (CE MIT, EE terms): https://developers.chatwoot.com/self-hosted/faq

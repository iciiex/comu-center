# ADR-0005: Defer Dify and n8n

Status: accepted (revisit only with a concrete, documented need).

**Context.** Both are popular, but neither is needed to prove the DAMIISH
Instagram FAQ + handover loop, and both carry license conditions that matter
for a multi-product commercial platform:

- **Dify** — modified Apache-2.0 ("Dify Open Source License"): operating a
  multi-tenant environment (one workspace = one tenant) needs written
  authorization/commercial license; frontend logo/copyright may not be removed.
  Invar's direction (multiple products/customers) sits exactly in that grey zone.
- **n8n** — Sustainable Use License (fair-code, not OSI open source): internal
  business use is allowed, but hosting for customers / letting external users
  build workflows needs a commercial agreement; `.ee.` code needs an
  Enterprise license.

**Decision.** Do not adopt now. The provider-independent core covers the PoC.
If experimentation speed (Dify) or a real integration workflow (n8n) later
justifies one, adopt it *behind* a port, internal-only, after a written
license review for the exact intended use, recorded in a new ADR.

**Consequences.** + No license entanglement in Invar's core IP; + one less
system to secure/upgrade during the pilot. − Less visual workflow tooling for
non-engineers early on (acceptable for a single FAQ pilot).

Sources: `docs/open-source-evaluation.md` (verified 2026-10-22; re-verify at
adoption time — licenses and pricing change).

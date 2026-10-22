# ADR-0002: Chatwoot Community Edition as the (external) operator inbox

Status: accepted as direction; desk spike done 2026-10-22
(`docs/spikes/0001-chatwoot-ce.md`), integration shape decided in **ADR-0007**;
**live deployment still pending** the spike's live-phase checklist.

**Context.** Operators need a real inbox (queues, assignment, history) for the
DAMIISH pilot. Building one is commodity work with high maintenance cost.

**Decision.** Evaluate/deploy Chatwoot Community Edition **as a separate
system** integrated via its APIs/webhooks. Invar's core remains the authority
for conversation control, authorization, knowledge, and audit. Use only the
MIT-licensed Community code/images; features under Chatwoot's `enterprise/`
directory (proprietary: e.g. Captain AI, SSO/SAML, SLA, audit logs) are out of
scope unless separately licensed. Spike first (roadmap task 1): verify CE
webhook/API fit for takeover/handover semantics, then confirm or revisit.

**Consequences.** + Weeks saved vs. custom inbox; + self-hostable, MIT core,
data stays on Invar infra. − Operating Rails+Postgres+Redis+Sidekiq (~4 GB RAM
class footprint) and tracking upstream upgrades/security; − fine-grained
roles/audit are enterprise features, so our core must enforce/record them.

**Exit strategy.** Core contracts are inbox-independent; replacing Chatwoot =
one new adapter + data export. No Invar business logic inside Chatwoot.

**Alternatives rejected (for now).** Custom inbox (only if the spike documents
a material CE limitation); commercial SaaS inboxes (cost/data-residency and
lock-in unassessed); Chatwoot Cloud (API/webhook availability varies by plan —
recheck at spike time). License sources: `docs/open-source-evaluation.md`.

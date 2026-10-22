# ADR-0010: Direct Meta integration for the single-account product mode

Status: accepted; implemented and tested (stub-level). Narrows ADR-0007 for
the owner's own-account use case; does not delete the Chatwoot path.

**Context.** The owner wants a ready, free-to-run product that reads their own
Instagram chats and answers with an AI API behind it. Running Chatwoot (ADR-0007)
remains the better *team inbox* at scale, but for a single professional
account it adds a Rails stack to operate before any value is proven. Meta's
Instagram API with Instagram Login is free, officially supports messaging on
graph.instagram.com, and does not require a Facebook Page.

**Decision.** Implement the direct route as a first-class path: Meta webhook
normalization (`entry[].messaging[]`), Graph send client
(`POST /{version}/{ig_id}/messages`, 1000-byte text limit), processing through
the unchanged domain send gate, a token-gated read-only inbox API over the
store, and an OpenAI-compatible AI provider adapter so free tiers (Gemini,
Groq, OpenRouter) or local Ollama plug in by config. **Exactly one owner per
IG account**: an account connected directly must not also be connected via
Chatwoot, or customers get duplicate replies. Chatwoot remains available as
the operator inbox when a team workflow justifies operating it.

**Consequences.** + Zero new runtime deps, runs on one small machine/process,
free at pilot scale; + the same domain invariants guard both routes.
− We now own Meta token lifecycle and webhook operations ourselves;
− the built-in inbox is read-only JSON (no assignment/team UX like Chatwoot);
− free AI tiers have quotas and weaker data terms — a paid or local provider
should be chosen deliberately before real customer volume.

**Alternatives rejected.** Unofficial scrapers/instagram-private-api style
clients (ban/ToS risk — ADR-0006 still binding); forcing Chatwoot for a solo
account (operational weight before proof); hard-coding one AI vendor.

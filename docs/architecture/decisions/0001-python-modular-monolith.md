# ADR-0001: Python modular monolith, zero-dependency domain core

Status: accepted (foundation). Date: 2026-10-22.

**Context.** Empty repository; first need is testable business contracts
(messages, handover, authorization, knowledge), not scale. AI ecosystem and
future hiring favor Python; the sandbox/CI provide Python 3.11.

**Decision.** One Python package (`invar_comms`) in a modular monolith:
`domain` (pure, stdlib only) ← `ports` ← `application` ← `adapters`.
Zero runtime dependencies for the core; frameworks (HTTP/ORM) enter later as
adapters only. Tooling: setuptools, pytest, ruff, mypy — all dev-only.

**Consequences.** + Contracts are unit-testable with no services running;
+ no supply-chain/runtime lock-in while the product is unproven; + low TCO.
− HTTP/persistence still to come (deliberate); − monolith discipline must be
enforced by review (see CONTRIBUTING).

**Alternatives rejected.** TypeScript/Node core (no advantage for AI-adjacent
domain logic, duplicates Chatwoot-adjacent JS without need); microservices /
Kubernetes (premature — mission explicitly excludes); starting inside Dify/n8n
as the core (see ADR-0005).

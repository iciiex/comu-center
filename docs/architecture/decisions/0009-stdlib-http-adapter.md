# ADR-0009: Stdlib HTTP adapter for the PoC (no web framework yet)

Status: accepted; implemented and tested.

**Context.** Task 3 needs exactly four routes (health, Chatwoot webhook, Meta
handshake + webhook). Handlers only verify signatures and enqueue outbox jobs;
all logic lives in the application layer. The core's zero-runtime-dependency
posture (ADR-0001) keeps supply-chain and upgrade cost near zero.

**Decision.** Implement the HTTP adapter on `http.server.ThreadingHTTPServer`
(stdlib) with explicit hardening: raw-body signature verification before
parsing, 1 MiB body cap, fail-closed 503 when secrets are unconfigured, 401 on
bad signatures, JSON-only errors, no request logging of bodies. Run it behind
a TLS-terminating reverse proxy in any hosted environment.

**Consequences.** + No new dependencies; the whole request path is unit-tested
against a real local server; deploys anywhere Python runs. − No OpenAPI,
routing niceties, or async I/O; ThreadingHTTPServer is adequate for pilot
webhook volume but is not a long-term API platform.

**Revisit trigger.** Adopt FastAPI (or similar) via a new ADR when we need
operator-facing APIs, authentication/session handling, request validation at
scale, or OpenAPI consumers — likely alongside the operator resume endpoint
(spike R6). The adapter boundary (`adapters/http_api.py`) keeps that swap
local: ports, processing, and tests above HTTP do not change.

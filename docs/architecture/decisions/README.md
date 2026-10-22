# Architecture Decision Records

| ADR | Decision |
|---|---|
| 0001 | Python modular monolith, zero-dependency domain core |
| 0002 | Chatwoot Community Edition as external operator inbox (spike first) |
| 0003 | PostgreSQL + full-text search; pgvector deferred |
| 0004 | Server-side conversation control with control_version guard |
| 0005 | Defer Dify and n8n (licensing + no demonstrated need) |
| 0006 | Official Meta APIs only; prepare, don't fake |
| 0007 | Chatwoot owns the Instagram connection; core integrates as Agent Bot |
| 0008 | SQLite adapter now (contract proof), PostgreSQL stays the target |
| 0009 | Stdlib HTTP adapter for the PoC (no web framework yet) |
| 0010 | Direct Meta integration for the single-account product mode |

Format: Context · Decision · Consequences · Alternatives rejected.
Supersede, don't rewrite: a changed decision gets a new ADR.

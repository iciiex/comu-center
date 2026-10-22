# Internal message contract (schema v1)

Implemented in `src/invar_comms/domain/messages.py`; tested in
`tests/test_messages.py` and `tests/test_conversation_service.py`.

## Fields

| Field | Meaning |
|---|---|
| `schema_version` | Contract version (`1`). Unsupported versions are rejected. |
| `product_id` | Product scope, e.g. `damiish`. Slug-validated. |
| `channel` | `instagram`, `website_chat`, `whatsapp`, `telegram`, `email`, `fake` (tests). |
| `channel_account_id` | The connected account on that channel (e.g. one IG professional account). |
| `external_contact_id` | Platform contact id — **unique only within (product, channel, account)**. Never join across platforms on this alone. |
| `conversation_id` | Invar conversation identifier. |
| `external_event_id` | Platform event/webhook id (dedupe source). |
| `external_message_id` | Platform message id, when distinct from the event id. |
| `direction`, `content_type` | `inbound/outbound`; `text/comment/reaction/system`. |
| `text` | Untrusted content. Required non-empty for text/comment. |
| `occurred_at` | Timezone-aware event time (normalized to UTC). Naive timestamps rejected. |
| `processing_status`, `delivery_status` | Lifecycle enums; inbound delivery is always `not_applicable`. |
| `correlation_id`, `metadata` | Tracing + minimal string metadata (no secrets). |

## Idempotency & deduplication

`idempotency_key = sha256(product|channel|account|external_event_id)`.
Webhook redelivery and bounded retries must present the same key; the
application layer ignores duplicates and audits them (`duplicate_ignored`).
In persistence this is a UNIQUE column (see `db/migrations/0001_initial.sql`).

## Retry & error expectations (for future adapters)

- Acknowledge webhooks fast (HTTP 200 after signature verification + durable
  enqueue); process asynchronously. *Planned with the HTTP adapter.*
- Retries use bounded exponential backoff; permanent validation failures are
  not retried; every failed send lands in `delivery_status=failed` + audit.
- Unknown/extra platform fields are ignored by adapters, never trusted as
  instructions, and never echoed to customers without the send gate.

## Evolution

Additive changes within v1 (new optional metadata). Any breaking change bumps
`schema_version`, requires an ADR + migration, and dual-read during rollout.

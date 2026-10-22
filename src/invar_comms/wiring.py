"""Composition root: assemble the application from settings.

This is the ONLY module that knows about all adapters at once. It keeps the
domain/application layers dependency-free and makes the current reality
explicit: AI provider is the deterministic fake until one is selected by ADR;
sending goes through Chatwoot REST and refuses to run unconfigured.
"""

from __future__ import annotations

from dataclasses import dataclass

from .adapters.chatwoot import InboxMapping
from .adapters.chatwoot_rest import ChatwootRestChannel
from .adapters.fakes import FakeAIProvider
from .adapters.sqlite_store import (
    SqliteAuditLog,
    SqliteConversationRepository,
    SqliteDeduplicator,
    SqliteKnowledgeStore,
    SqliteMessageRepository,
    SqliteOutbox,
    SqliteStore,
)
from .application.chatwoot_processing import ChatwootEventProcessor
from .application.conversation_service import ConversationService
from .application.worker import JobHandler, OutboxWorker
from .config import Settings
from .domain.authorization import Actor, Role
from .domain.errors import ValidationError
from .domain.messages import Channel


def parse_inbox_map(raw: str, *, enabled_products: frozenset[str]) -> dict[int, InboxMapping]:
    """Parse '7=damiish:instagram:ig-acct-1,...' — fail fast on any ambiguity."""
    result: dict[int, InboxMapping] = {}
    for entry in (part.strip() for part in raw.split(",") if part.strip()):
        inbox_part, sep, mapping_part = entry.partition("=")
        fields = mapping_part.split(":")
        if sep != "=" or len(fields) != 3 or not inbox_part.strip().isdigit():
            raise ValidationError(
                f"invalid INVAR_CHATWOOT_INBOX_MAP entry {entry!r}; "
                "expected '<inbox_id>=<product>:<channel>:<account_id>'"
            )
        product_id, channel_raw, account_id = (f.strip() for f in fields)
        if product_id not in enabled_products:
            raise ValidationError(
                f"inbox map product {product_id!r} not in INVAR_ENABLED_PRODUCTS")
        try:
            channel = Channel(channel_raw)
        except ValueError as exc:
            raise ValidationError(f"unknown channel {channel_raw!r} in inbox map") from exc
        inbox_id = int(inbox_part.strip())
        if inbox_id in result:
            raise ValidationError(f"duplicate Chatwoot inbox id {inbox_id} in map")
        result[inbox_id] = InboxMapping(product_id, channel, account_id)
    return result


@dataclass
class ApplicationStack:
    store: SqliteStore
    outbox: SqliteOutbox
    processor: ChatwootEventProcessor
    worker: OutboxWorker


def build_stack(settings: Settings) -> ApplicationStack:
    store = SqliteStore(settings.sqlite_path)
    conversations = SqliteConversationRepository(store)
    messages = SqliteMessageRepository(store)
    audit = SqliteAuditLog(store)
    knowledge = SqliteKnowledgeStore(store)
    outbox = SqliteOutbox(store)

    if settings.ai_provider_name != "fake":
        store.close()
        raise ValidationError(
            f"AI provider {settings.ai_provider_name!r} is not implemented yet; "
            "only the deterministic 'fake' provider exists (selection needs an ADR)"
        )
    channel = ChatwootRestChannel(
        base_url=settings.chatwoot_base_url, bot_token=settings.chatwoot_bot_token
    )
    inboxes = parse_inbox_map(
        settings.chatwoot_inbox_map, enabled_products=settings.enabled_products)

    # One AI system actor per enabled product scope (suggest/send/request
    # handover only — it can never accept, resume or approve; see ADR-0004).
    ai_actor = Actor("ai-system", Role.AI_SYSTEM, settings.enabled_products)
    service = ConversationService(
        ai=FakeAIProvider(), channel=channel, knowledge=knowledge, audit=audit,
        ai_actor=ai_actor, ai_send_enabled=settings.ai_send_enabled,
        dedupe=SqliteDeduplicator(messages),
    )
    processor = ChatwootEventProcessor(
        service=service, conversations=conversations, audit=audit,
        ai_actor=ai_actor, inboxes=inboxes,
        status_sync=(
            (lambda key, status: channel.toggle_status(
                conversation_id=key, status=status))
            if channel.configured else None
        ),
    )

    def handle_chatwoot_event(payload: dict[str, object]) -> None:
        processor.process(payload)  # type: ignore[arg-type]

    def handle_meta_event(_payload: dict[str, object]) -> None:
        raise ValidationError(
            "Meta event normalization is not implemented (exit path only — "
            "Chatwoot owns Instagram in the PoC, ADR-0007)"
        )

    handlers: dict[str, JobHandler] = {
        "chatwoot_event": handle_chatwoot_event,  # type: ignore[dict-item]
        "meta_event": handle_meta_event,  # type: ignore[dict-item]
    }
    return ApplicationStack(
        store=store, outbox=outbox, processor=processor,
        worker=OutboxWorker(outbox, handlers),
    )

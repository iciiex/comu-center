"""Composition root: assemble the application from settings.

This is the ONLY module that knows about all adapters at once. It keeps the
domain/application layers dependency-free and makes the current reality
explicit: the AI provider is the deterministic fake unless an
OpenAI-compatible endpoint is configured; every outbound channel refuses to
run unconfigured, and all live switches default to off.
"""

from __future__ import annotations

from dataclasses import dataclass

from .adapters.chatwoot import InboxMapping
from .adapters.chatwoot_rest import ChatwootRestChannel
from .adapters.fakes import FakeAIProvider
from .adapters.meta_instagram import MetaInstagramAdapter
from .adapters.openai_compat import OpenAICompatibleProvider
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
from .application.meta_processing import MetaEventProcessor
from .application.worker import JobHandler, OutboxWorker
from .config import Settings
from .domain.authorization import Actor, Role
from .domain.errors import ValidationError
from .domain.messages import Channel
from .ports.ai_provider import AIProvider


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


def parse_meta_account_map(
    raw: str, *, enabled_products: frozenset[str]
) -> dict[str, str]:
    """Parse '17841400008460056=damiish,...' — fail fast on any ambiguity."""
    result: dict[str, str] = {}
    for entry in (part.strip() for part in raw.split(",") if part.strip()):
        account_part, sep, product_part = entry.partition("=")
        account_id, product_id = account_part.strip(), product_part.strip()
        if sep != "=" or not account_id or not product_id:
            raise ValidationError(
                f"invalid INVAR_META_ACCOUNT_MAP entry {entry!r}; "
                "expected '<ig_account_id>=<product>'")
        if product_id not in enabled_products:
            raise ValidationError(
                f"meta account map product {product_id!r} not enabled")
        if account_id in result:
            raise ValidationError(f"duplicate Meta account id {account_id} in map")
        result[account_id] = product_id
    return result


def build_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider_name == "fake":
        return FakeAIProvider()
    if settings.ai_provider_name == "openai_compat":
        return OpenAICompatibleProvider(
            base_url=settings.ai_api_base_url,
            model=settings.ai_model,
            api_key=settings.ai_provider_api_key,
        )
    raise ValidationError(
        f"unknown AI provider {settings.ai_provider_name!r}; "
        "expected 'fake' or 'openai_compat'")


@dataclass
class ApplicationStack:
    store: SqliteStore
    outbox: SqliteOutbox
    processor: ChatwootEventProcessor
    meta_processor: MetaEventProcessor
    worker: OutboxWorker


def build_stack(settings: Settings) -> ApplicationStack:
    store = SqliteStore(settings.sqlite_path)
    conversations = SqliteConversationRepository(store)
    messages = SqliteMessageRepository(store)
    audit = SqliteAuditLog(store)
    knowledge = SqliteKnowledgeStore(store)
    outbox = SqliteOutbox(store)

    try:
        ai_provider = build_ai_provider(settings)
        inboxes = parse_inbox_map(
            settings.chatwoot_inbox_map, enabled_products=settings.enabled_products)
        meta_accounts = parse_meta_account_map(
            settings.meta_account_map, enabled_products=settings.enabled_products)
    except ValidationError:
        store.close()
        raise
    channel = ChatwootRestChannel(
        base_url=settings.chatwoot_base_url, bot_token=settings.chatwoot_bot_token
    )
    meta_channel = MetaInstagramAdapter(
        access_token=settings.meta_access_token,
        ig_account_id=settings.meta_ig_account_id,
        graph_base_url=settings.meta_graph_base_url,
        api_version=settings.meta_api_version,
        live_send_enabled=settings.meta_live_send_enabled,
        account_products=meta_accounts,
    )

    # One AI system actor per enabled product scope (suggest/send/request
    # handover only — it can never accept, resume or approve; see ADR-0004).
    ai_actor = Actor("ai-system", Role.AI_SYSTEM, settings.enabled_products)
    service = ConversationService(
        ai=ai_provider, channel=channel, knowledge=knowledge, audit=audit,
        ai_actor=ai_actor, ai_send_enabled=settings.ai_send_enabled,
        dedupe=SqliteDeduplicator(messages),
    )
    meta_service = ConversationService(
        ai=ai_provider, channel=meta_channel, knowledge=knowledge, audit=audit,
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

    meta_processor = MetaEventProcessor(
        service=meta_service, conversations=conversations, audit=audit,
        ai_actor=ai_actor, account_products=meta_accounts,
    )

    def handle_chatwoot_event(payload: dict[str, object]) -> None:
        processor.process(payload)  # type: ignore[arg-type]

    def handle_meta_event(payload: dict[str, object]) -> None:
        meta_processor.process(payload)  # type: ignore[arg-type]

    handlers: dict[str, JobHandler] = {
        "chatwoot_event": handle_chatwoot_event,  # type: ignore[dict-item]
        "meta_event": handle_meta_event,  # type: ignore[dict-item]
    }
    return ApplicationStack(
        store=store, outbox=outbox, processor=processor,
        meta_processor=meta_processor,
        worker=OutboxWorker(outbox, handlers),
    )

import hashlib
import hmac

import pytest

from invar_comms.adapters.chatwoot import (
    ChatwootSignalKind,
    InboxMapping,
    build_create_message_payload,
    build_toggle_status_payload,
    normalize_event,
    verify_chatwoot_signature,
)
from invar_comms.domain.errors import ValidationError
from invar_comms.domain.messages import Channel

INBOXES = {7: InboxMapping("damiish", Channel.INSTAGRAM, "ig-acct-1")}


def customer_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "event": "message_created",
        "id": 101,
        "content": "How do I register a new animal?",
        "created_at": 1792312800,
        "message_type": "incoming",
        "private": False,
        "source_id": "ig-msg-55",
        "sender": {"id": 42, "type": "contact", "name": "Customer"},
        "conversation": {
            "id": 900,
            "inbox_id": 7,
            "status": "pending",
            "contact_inbox": {"source_id": "ig-user-42"},
        },
        "account": {"id": 3, "name": "DAMIISH"},
    }
    base.update(overrides)
    return base


def signature_for(body: bytes, ts: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), f"{ts}.".encode() + body,
                      hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_signature_verification_and_replay_window() -> None:
    body, secret, ts = b'{"event":"message_created"}', "bot-secret-test-only", "1792312800"
    sig = signature_for(body, ts, secret)  # noqa: S106 test fixture secret
    verify_chatwoot_signature(raw_body=body, signature_header=sig,
                              timestamp_header=ts, secret=secret,
                              now_epoch=1792312800)
    with pytest.raises(ValidationError):  # tampered body
        verify_chatwoot_signature(raw_body=b"tampered", signature_header=sig,
                                  timestamp_header=ts, secret=secret,
                                  now_epoch=1792312800)
    with pytest.raises(ValidationError):  # stale -> replay rejected
        verify_chatwoot_signature(raw_body=body, signature_header=sig,
                                  timestamp_header=ts, secret=secret,
                                  now_epoch=1792312800 + 3600)
    with pytest.raises(ValidationError):  # no secret configured -> fail closed
        verify_chatwoot_signature(raw_body=body, signature_header=sig,
                                  timestamp_header=ts, secret="",
                                  now_epoch=1792312800)


def test_customer_message_normalizes_to_internal_contract() -> None:
    signal = normalize_event(customer_payload(), inboxes=INBOXES)  # type: ignore[arg-type]
    assert signal.kind is ChatwootSignalKind.CUSTOMER_MESSAGE
    assert signal.conversation_key == "cw-3-900"
    assert signal.message is not None
    msg = signal.message
    assert (msg.product_id, msg.channel) == ("damiish", Channel.INSTAGRAM)
    assert msg.external_contact_id == "ig-user-42"  # contact_inbox source_id wins
    assert msg.external_event_id == "chatwoot-msg-101"


def test_bot_echo_and_private_notes_never_become_customer_messages() -> None:
    echo = customer_payload(sender={"id": 1, "type": "agent_bot"})
    assert normalize_event(echo, inboxes=INBOXES).kind is ChatwootSignalKind.BOT_ECHO  # type: ignore[arg-type]
    note = customer_payload(private=True)
    assert normalize_event(note, inboxes=INBOXES).kind is ChatwootSignalKind.PRIVATE_NOTE  # type: ignore[arg-type]


def test_operator_reply_is_a_takeover_signal_not_a_message() -> None:
    payload = customer_payload(message_type="outgoing",
                               sender={"id": 9, "type": "user"})
    signal = normalize_event(payload, inboxes=INBOXES)  # type: ignore[arg-type]
    assert signal.kind is ChatwootSignalKind.OPERATOR_REPLIED
    assert signal.message is None


def test_status_changes_map_to_control_signals() -> None:
    opened = {"event": "conversation_status_changed", "id": 900, "status": "open",
              "account": {"id": 3}}
    assert normalize_event(opened, inboxes=INBOXES).kind is ChatwootSignalKind.STATUS_OPEN
    pending = {**opened, "status": "pending"}
    assert normalize_event(pending, inboxes=INBOXES).kind is (  # type: ignore[arg-type]
        ChatwootSignalKind.STATUS_PENDING)


def test_unknown_inbox_fails_closed() -> None:
    with pytest.raises(ValidationError):
        normalize_event(customer_payload(), inboxes={})  # type: ignore[arg-type]


def test_outbound_payload_builders_enforce_limits() -> None:
    assert build_create_message_payload(" hello ") == {
        "content": "hello", "message_type": "outgoing", "private": False}
    with pytest.raises(ValidationError):
        build_create_message_payload("x" * 1001)  # Instagram channel limit
    assert build_toggle_status_payload("open") == {"status": "open"}
    with pytest.raises(ValidationError):
        build_toggle_status_payload("banana")

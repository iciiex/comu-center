"""Direct Meta path: normalization, Graph send (stub server), processing."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from helpers import AI, make_doc

from invar_comms.adapters.fakes import FakeAIProvider, FakeChannelAdapter
from invar_comms.adapters.meta_instagram import (
    MetaApiError,
    MetaInstagramAdapter,
    MetaSignalKind,
    normalize_meta_event,
)
from invar_comms.adapters.sqlite_store import (
    SqliteAuditLog,
    SqliteConversationRepository,
    SqliteDeduplicator,
    SqliteKnowledgeStore,
    SqliteMessageRepository,
    SqliteStore,
)
from invar_comms.application.conversation_service import ConversationService
from invar_comms.application.meta_processing import MetaEventProcessor
from invar_comms.domain.conversation import ControlState
from invar_comms.domain.errors import LiveSendDisabled, ValidationError
from invar_comms.wiring import parse_meta_account_map

ACCOUNTS = {"17841400008460056": "damiish"}


def meta_payload(text: str = "How do I register a new animal?",
                 mid: str = "mid-1", **msg_overrides: object) -> dict[str, object]:
    message: dict[str, object] = {"mid": mid, "text": text}
    message.update(msg_overrides)
    return {
        "object": "instagram",
        "entry": [{
            "id": "17841400008460056", "time": 1792312800000,
            "messaging": [{
                "sender": {"id": "99887766"},
                "recipient": {"id": "17841400008460056"},
                "timestamp": 1792312800000,
                "message": message,
            }],
        }],
    }


def test_normalize_customer_message() -> None:
    signals = normalize_meta_event(meta_payload(), account_products=ACCOUNTS)  # type: ignore[arg-type]
    assert len(signals) == 1
    signal = signals[0]
    assert signal.kind is MetaSignalKind.CUSTOMER_MESSAGE
    assert signal.conversation_key == "ig-17841400008460056-99887766"
    assert signal.message is not None
    assert signal.message.product_id == "damiish"
    assert signal.message.external_message_id == "mid-1"


def test_echo_unmapped_and_non_text_are_ignored_not_guessed() -> None:
    echo = normalize_meta_event(meta_payload(is_echo=True), account_products=ACCOUNTS)  # type: ignore[arg-type]
    assert echo[0].kind is MetaSignalKind.ECHO
    unmapped = normalize_meta_event(meta_payload(), account_products={})  # type: ignore[arg-type]
    assert unmapped[0].kind is MetaSignalKind.IGNORED
    assert "unmapped" in unmapped[0].detail
    no_text = meta_payload()
    no_text["entry"][0]["messaging"][0]["message"] = {"mid": "m2", "attachments": []}  # type: ignore[index]
    assert normalize_meta_event(no_text, account_products=ACCOUNTS)[0].kind is (  # type: ignore[arg-type]
        MetaSignalKind.IGNORED)
    with pytest.raises(ValidationError):
        normalize_meta_event({"object": "whatsapp"}, account_products=ACCOUNTS)  # type: ignore[arg-type]


CAPTURED: list[dict[str, object]] = []


class GraphStub(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        CAPTURED.append({"path": self.path,
                         "auth": self.headers.get("Authorization"),
                         "body": json.loads(body.decode()) if body else {}})
        payload = json.dumps({"recipient_id": "99887766",
                              "message_id": "m_abc"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture()
def graph_url():  # type: ignore[no-untyped-def]
    CAPTURED.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), GraphStub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_graph_send_uses_official_shape(graph_url: str) -> None:
    adapter = MetaInstagramAdapter(
        access_token="tok", ig_account_id="17841400008460056",
        graph_base_url=graph_url, api_version="v25.0", live_send_enabled=True)
    sent = adapter.send_text(conversation_id="ig-17841400008460056-99887766",
                             external_contact_id="99887766", text="سلام")
    assert sent == "m_abc"
    assert CAPTURED[0]["path"] == "/v25.0/17841400008460056/messages"
    assert CAPTURED[0]["auth"] == "Bearer tok"
    assert CAPTURED[0]["body"] == {
        "recipient": {"id": "99887766"}, "messaging_type": "RESPONSE",
        "message": {"text": "سلام"}}


def test_graph_send_gates_and_byte_limit(graph_url: str) -> None:
    off = MetaInstagramAdapter(access_token="tok", ig_account_id="178",
                               graph_base_url=graph_url, live_send_enabled=False)
    with pytest.raises(LiveSendDisabled):
        off.send_text(conversation_id="c", external_contact_id="u", text="hi")
    on = MetaInstagramAdapter(access_token="tok", ig_account_id="178",
                              graph_base_url=graph_url, live_send_enabled=True)
    with pytest.raises(ValidationError):  # Persian char = 2 bytes; 501 chars > 1000 bytes
        on.send_text(conversation_id="c", external_contact_id="u", text="س" * 501)


def test_graph_unreachable_is_api_error() -> None:
    adapter = MetaInstagramAdapter(
        access_token="tok", ig_account_id="178",
        graph_base_url="http://127.0.0.1:1", live_send_enabled=True,
        timeout_seconds=1.0)
    with pytest.raises(MetaApiError):
        adapter.send_text(conversation_id="c", external_contact_id="u", text="hi")


def build_processor(tmp_path, *, with_knowledge: bool = True):  # type: ignore[no-untyped-def]
    store = SqliteStore(tmp_path / "t.sqlite3")
    knowledge = SqliteKnowledgeStore(store)
    if with_knowledge:
        knowledge.add(make_doc())
    channel = FakeChannelAdapter()
    service = ConversationService(
        ai=FakeAIProvider(), channel=channel, knowledge=knowledge,
        audit=SqliteAuditLog(store), ai_actor=AI, ai_send_enabled=True,
        dedupe=SqliteDeduplicator(SqliteMessageRepository(store)))
    processor = MetaEventProcessor(
        service=service, conversations=SqliteConversationRepository(store),
        audit=SqliteAuditLog(store), ai_actor=AI, account_products=ACCOUNTS)
    return store, channel, processor


def test_meta_processing_replies_once_and_dedupes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store, channel, processor = build_processor(tmp_path)
    first = processor.process(meta_payload())  # type: ignore[arg-type]
    second = processor.process(meta_payload())  # redelivery
    assert first[0].outcome == "replied"
    assert second[0].duplicate is True
    assert len(channel.sent) == 1
    stored = store.messages_list("ig-17841400008460056-99887766")
    assert [m.text for m in stored] == ["How do I register a new animal?"]
    listed = store.conversations_list()
    assert [c.conversation_id for c in listed] == ["ig-17841400008460056-99887766"]
    store.close()


def test_meta_processing_escalates_without_knowledge(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store, channel, processor = build_processor(tmp_path, with_knowledge=False)
    result = processor.process(meta_payload("قیمت چنده؟", mid="mid-9"))  # type: ignore[arg-type]
    assert result[0].escalated is True
    assert channel.sent == []
    conv = SqliteConversationRepository(store).load("ig-17841400008460056-99887766")
    assert conv is not None and conv.state is ControlState.HANDOVER_REQUESTED
    store.close()


def test_parse_meta_account_map_strictness() -> None:
    parsed = parse_meta_account_map("178=damiish", enabled_products=frozenset({"damiish"}))
    assert parsed == {"178": "damiish"}
    for bad in ["178", "178=other", "=damiish", "178=damiish,178=damiish"]:
        with pytest.raises(ValidationError):
            parse_meta_account_map(bad, enabled_products=frozenset({"damiish"}))

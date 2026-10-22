"""Chatwoot REST client tests against a local stub server (no live Chatwoot)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from invar_comms.adapters.chatwoot_rest import (
    ChatwootApiError,
    ChatwootRestChannel,
    parse_conversation_key,
)
from invar_comms.domain.errors import LiveSendDisabled, ValidationError

CAPTURED: list[dict[str, object]] = []
FAIL_MODE = {"on": False}


class StubHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        CAPTURED.append({
            "path": self.path,
            "token": self.headers.get("api_access_token"),
            "body": json.loads(body.decode()) if body else {},
        })
        if FAIL_MODE["on"]:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"{}")
            return
        payload = json.dumps({"id": 555}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture()
def stub_url():  # type: ignore[no-untyped-def]
    CAPTURED.clear()
    FAIL_MODE["on"] = False
    server = ThreadingHTTPServer(("127.0.0.1", 0), StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_send_text_posts_to_correct_conversation(stub_url: str) -> None:
    channel = ChatwootRestChannel(base_url=stub_url, bot_token="bot-tok")
    sent_id = channel.send_text(conversation_id="cw-3-900",
                                external_contact_id="ig-user-42", text=" سلام ")
    assert sent_id == "chatwoot-msg-555"
    assert CAPTURED == [{
        "path": "/api/v1/accounts/3/conversations/900/messages",
        "token": "bot-tok",
        "body": {"content": "سلام", "message_type": "outgoing", "private": False},
    }]


def test_toggle_status_payload(stub_url: str) -> None:
    channel = ChatwootRestChannel(base_url=stub_url, bot_token="bot-tok")
    channel.toggle_status(conversation_id="cw-3-900", status="open")
    assert CAPTURED[0]["path"] == "/api/v1/accounts/3/conversations/900/toggle_status"
    assert CAPTURED[0]["body"] == {"status": "open"}


def test_unconfigured_client_refuses_to_send() -> None:
    channel = ChatwootRestChannel(base_url="", bot_token="")
    with pytest.raises(LiveSendDisabled):
        channel.send_text(conversation_id="cw-3-900",
                          external_contact_id="x", text="hi")


def test_api_error_is_surfaced(stub_url: str) -> None:
    FAIL_MODE["on"] = True
    channel = ChatwootRestChannel(base_url=stub_url, bot_token="bot-tok")
    with pytest.raises(ChatwootApiError):
        channel.send_text(conversation_id="cw-3-900",
                          external_contact_id="x", text="hi")


def test_conversation_key_parsing_is_strict() -> None:
    assert parse_conversation_key("cw-12-34") == ("12", "34")
    for bad in ["cw-12", "xx-1-2", "cw--2", "cw-1-2-3"]:
        with pytest.raises(ValidationError):
            parse_conversation_key(bad)

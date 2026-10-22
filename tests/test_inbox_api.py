"""Operator inbox API: token-gated conversation/message listing."""

from __future__ import annotations

import json

from helpers import make_conversation, make_message
from test_http_api import Server

from invar_comms.adapters.sqlite_store import (
    SqliteConversationRepository,
    SqliteMessageRepository,
    SqliteOutbox,
    SqliteStore,
)
from invar_comms.config import Settings

TOKEN = "op-token-test-only"  # noqa: S105 test fixture


def test_inbox_requires_operator_token(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SqliteStore(tmp_path / "t.sqlite3")
    SqliteConversationRepository(store).add(make_conversation())
    SqliteMessageRepository(store).try_insert(make_message())
    settings = Settings(http_host="127.0.0.1", http_port=0, operator_token=TOKEN)
    with Server(settings, SqliteOutbox(store)) as server:
        # Server helper builds without store, so the API must fail closed 503.
        assert server.request("GET", "/api/conversations")[0] == 503
    store.close()


def test_inbox_lists_with_token(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from invar_comms.adapters.http_api import build_server

    store = SqliteStore(tmp_path / "t.sqlite3")
    SqliteConversationRepository(store).add(make_conversation())
    SqliteMessageRepository(store).try_insert(make_message())
    settings = Settings(http_host="127.0.0.1", http_port=0, operator_token=TOKEN)

    class WithStore(Server):
        def __init__(self) -> None:  # noqa: D107
            self._server = build_server(settings, SqliteOutbox(store), store)
            self.port = int(self._server.server_address[1])
            import threading

            self._thread = threading.Thread(
                target=self._server.serve_forever, daemon=True)

    with WithStore() as server:
        assert server.request("GET", "/api/conversations")[0] == 401
        assert server.request(
            "GET", "/api/conversations",
            headers={"X-Operator-Token": "wrong"})[0] == 401
        code, body = server.request(
            "GET", "/api/conversations",
            headers={"X-Operator-Token": TOKEN})
        assert code == 200
        conversations = json.loads(body)["conversations"]
        assert conversations[0]["conversation_id"] == "conv-1"
        assert conversations[0]["control_state"] == "ai_active"
        code, body = server.request(
            "GET", "/api/conversations/conv-1",
            headers={"X-Operator-Token": TOKEN})
        assert code == 200
        detail = json.loads(body)
        assert detail["messages"][0]["text"] == "How do I register a new animal?"
        assert server.request(
            "GET", "/api/conversations/missing",
            headers={"X-Operator-Token": TOKEN})[0] == 404
    store.close()

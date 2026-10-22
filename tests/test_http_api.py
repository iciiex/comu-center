"""HTTP adapter tests against a real local server (ephemeral port)."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import urllib.error
import urllib.request

import pytest

from invar_comms.adapters.http_api import build_server
from invar_comms.adapters.sqlite_store import SqliteOutbox, SqliteStore
from invar_comms.config import Settings

SECRET = "cw-secret-test-only"  # noqa: S105 test fixture


def sign(body: bytes, ts: str, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(
        secret.encode(), f"{ts}.".encode() + body, hashlib.sha256
    ).hexdigest()


class Server:
    def __init__(self, settings: Settings, outbox: SqliteOutbox) -> None:
        self._server = build_server(settings, outbox)
        self.port = int(self._server.server_address[1])
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> Server:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._server.shutdown()
        self._server.server_close()

    def request(self, method: str, path: str, body: bytes | None = None,
                headers: dict[str, str] | None = None) -> tuple[int, bytes]:
        req = urllib.request.Request(  # noqa: S310 localhost test server
            f"http://127.0.0.1:{self.port}{path}", data=body, method=method,
            headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
                return int(resp.status), resp.read()
        except urllib.error.HTTPError as exc:
            return int(exc.code), exc.read()


@pytest.fixture()
def stack(tmp_path):  # type: ignore[no-untyped-def]
    store = SqliteStore(tmp_path / "t.sqlite3")
    outbox = SqliteOutbox(store)
    settings = Settings(http_host="127.0.0.1", http_port=0,
                        chatwoot_webhook_secret=SECRET,
                        meta_app_secret="meta-secret-test-only",
                        meta_webhook_verify_token="verify-tok")
    yield settings, outbox
    store.close()


def test_health_and_unknown_route(stack) -> None:  # type: ignore[no-untyped-def]
    with Server(*stack) as server:
        code, body = server.request("GET", "/health")
        assert code == 200
        assert json.loads(body)["live_messaging"] is False
        assert server.request("GET", "/nope")[0] == 404


def test_chatwoot_webhook_signature_flow(stack) -> None:  # type: ignore[no-untyped-def]
    settings, outbox = stack
    body = json.dumps({"event": "message_created", "id": 1}).encode()
    ts = "1792312800"
    with Server(settings, outbox) as server:
        import time

        fresh_ts = str(int(time.time()))
        code, resp = server.request("POST", "/webhooks/chatwoot", body, {
            "X-Chatwoot-Signature": sign(body, fresh_ts),
            "X-Chatwoot-Timestamp": fresh_ts,
        })
        assert code == 202
        assert json.loads(resp)["accepted"] is True
        # tampered body + missing signature are rejected, nothing enqueued
        code, _ = server.request("POST", "/webhooks/chatwoot", b"tampered", {
            "X-Chatwoot-Signature": sign(body, fresh_ts),
            "X-Chatwoot-Timestamp": fresh_ts,
        })
        assert code == 401
        assert server.request("POST", "/webhooks/chatwoot", body)[0] == 401
        code, _ = server.request("POST", "/webhooks/chatwoot", b"x" * 1_100_000, {
            "X-Chatwoot-Signature": "sha256=whatever",
            "X-Chatwoot-Timestamp": ts,
        })
        assert code == 413
    jobs = outbox.fetch_pending(limit=10)
    assert len(jobs) == 1
    assert jobs[0].job_type == "chatwoot_event"


def test_unconfigured_webhook_fails_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SqliteStore(tmp_path / "t.sqlite3")
    settings = Settings(http_host="127.0.0.1", http_port=0)  # no secrets at all
    with Server(settings, SqliteOutbox(store)) as server:
        assert server.request("POST", "/webhooks/chatwoot", b"{}")[0] == 503
        assert server.request("POST", "/webhooks/meta", b"{}")[0] == 503
        assert server.request(
            "GET", "/webhooks/meta?hub.mode=subscribe&hub.verify_token=x"
                   "&hub.challenge=1")[0] == 503
    store.close()


def test_meta_handshake_and_signed_post(stack) -> None:  # type: ignore[no-untyped-def]
    settings, outbox = stack
    with Server(settings, outbox) as server:
        code, body = server.request(
            "GET", "/webhooks/meta?hub.mode=subscribe"
                   "&hub.verify_token=verify-tok&hub.challenge=abc123")
        assert (code, body) == (200, b"abc123")
        assert server.request(
            "GET", "/webhooks/meta?hub.mode=subscribe"
                   "&hub.verify_token=wrong&hub.challenge=abc123")[0] == 403

        raw = json.dumps({"object": "instagram", "entry": []}).encode()
        sig = "sha256=" + hmac.new(b"meta-secret-test-only", raw,
                                   hashlib.sha256).hexdigest()
        code, _ = server.request("POST", "/webhooks/meta", raw,
                                 {"X-Hub-Signature-256": sig})
        assert code == 202
        assert server.request("POST", "/webhooks/meta", b"tampered",
                              {"X-Hub-Signature-256": sig})[0] == 401
    assert [j.job_type for j in outbox.fetch_pending(limit=10)] == ["meta_event"]

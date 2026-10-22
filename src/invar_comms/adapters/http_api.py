"""HTTP adapter (stdlib `http.server`, ADR-0009).

Routes:
- GET  /health             liveness, no secrets
- POST /webhooks/chatwoot  signed Chatwoot Agent Bot events -> outbox (202)
- GET  /webhooks/meta      Meta subscription handshake (exit-path prep)
- POST /webhooks/meta      signed Meta events -> outbox (202)
- GET  /api/conversations  operator inbox API (requires X-Operator-Token)
- GET  /api/conversations/{id}  messages + audit for one conversation

Security posture: signatures are verified on the RAW body before any parsing;
missing configuration fails closed (503), bad signatures 401, oversized
bodies 413, malformed JSON 400. Webhook handlers only *enqueue* — processing
happens in the outbox worker so we can ACK fast, per platform expectations.
Nothing here sends messages.
"""

from __future__ import annotations

import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, unquote, urlparse

from .. import __version__
from ..config import Settings
from ..domain.errors import ValidationError
from ..ports.repositories import Outbox
from .chatwoot import verify_chatwoot_signature
from .meta_instagram import verify_payload_signature, verify_webhook_subscription

if TYPE_CHECKING:
    from .sqlite_store import SqliteStore

MAX_BODY_BYTES = 1_048_576  # 1 MiB


def make_handler(
    settings: Settings, outbox: Outbox, store: SqliteStore | None = None
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "InvarComms/0.1"

        # -- plumbing ------------------------------------------------------
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

        def _send(self, code: int, body: bytes,
                  content_type: str = "application/json; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, payload: dict[str, Any]) -> None:
            self._send(code, json.dumps(payload).encode("utf-8"))

        def _read_body(self) -> bytes | None:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                self._json(411, {"error": "content-length required"})
                return None
            try:
                length = int(raw_length)
            except ValueError:
                self._json(400, {"error": "invalid content-length"})
                return None
            if length < 0:
                self._json(400, {"error": "invalid content-length"})
                return None
            if length > MAX_BODY_BYTES:
                # Discard the oversized body in bounded chunks before replying,
                # so well-behaved clients get a clean 413 instead of a broken
                # pipe. Absurd declarations just get their connection closed.
                if length <= 16 * MAX_BODY_BYTES:
                    remaining = length
                    while remaining > 0:
                        chunk = self.rfile.read(min(remaining, 65_536))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                else:
                    self.close_connection = True
                self._json(413, {"error": "body too large"})
                return None
            return self.rfile.read(length)

        def _enqueue_json(self, job_type: str, raw: bytes) -> None:
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._json(400, {"error": "invalid JSON body"})
                return
            if not isinstance(payload, dict):
                self._json(400, {"error": "JSON body must be an object"})
                return
            job_id = outbox.enqueue(job_type, payload)
            self._json(202, {"accepted": True, "job_id": job_id})

        def _operator_authorized(self) -> bool:
            if not settings.operator_token or store is None:
                return False
            provided = self.headers.get("X-Operator-Token") or ""
            return hmac.compare_digest(provided, settings.operator_token)

        # -- routes ---------------------------------------------------------
        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/conversations" or path.startswith("/api/conversations/"):
                if not settings.operator_token or store is None:
                    self._json(503, {"error": "operator API not configured"})
                    return
                if not self._operator_authorized():
                    self._json(401, {"error": "unauthorized"})
                    return
                if path == "/api/conversations":
                    self._json(200, {"conversations": [
                        {
                            "conversation_id": c.conversation_id,
                            "product_id": c.product_id,
                            "channel": str(c.contact.channel),
                            "external_contact_id": c.contact.external_contact_id,
                            "control_state": str(c.state),
                            "control_version": c.control_version,
                            "human_owner_id": c.human_owner_id,
                        } for c in store.conversations_list()
                    ]})
                    return
                conversation_id = unquote(path.removeprefix("/api/conversations/"))
                conversation = store.conversation_load(conversation_id)
                if conversation is None:
                    self._json(404, {"error": "conversation not found"})
                    return
                self._json(200, {
                    "conversation_id": conversation_id,
                    "control_state": str(conversation.state),
                    "messages": [
                        {
                            "external_message_id": m.external_message_id,
                            "direction": str(m.direction),
                            "text": m.text,
                            "occurred_at": m.occurred_at.isoformat(),
                        } for m in store.messages_list(conversation_id)
                    ],
                    "audit": [
                        {
                            "event_type": str(e.event_type),
                            "actor_id": e.actor_id,
                            "detail": e.detail,
                            "occurred_at": e.occurred_at.isoformat(),
                        } for e in store.audit_list(conversation_id)
                    ],
                })
                return
            if path == "/health":
                self._json(200, {
                    "status": "ok", "service": "invar-comms",
                    "version": __version__, "live_messaging": False,
                })
                return
            if path == "/webhooks/meta":
                if not settings.meta_webhook_verify_token:
                    self._json(503, {"error": "Meta webhook not configured"})
                    return
                query = parse_qs(urlparse(self.path).query)

                def first(name: str) -> str | None:
                    values = query.get(name)
                    return values[0] if values else None

                try:
                    challenge = verify_webhook_subscription(
                        mode=first("hub.mode"),
                        verify_token=first("hub.verify_token"),
                        challenge=first("hub.challenge"),
                        expected_token=settings.meta_webhook_verify_token,
                    )
                except ValidationError:
                    self._json(403, {"error": "verification failed"})
                    return
                self._send(200, challenge.encode("utf-8"),
                           "text/plain; charset=utf-8")
                return
            self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/webhooks/chatwoot":
                if not settings.chatwoot_webhook_secret:
                    self._json(503, {"error": "Chatwoot webhook not configured"})
                    return
                raw = self._read_body()
                if raw is None:
                    return
                try:
                    verify_chatwoot_signature(
                        raw_body=raw,
                        signature_header=self.headers.get("X-Chatwoot-Signature"),
                        timestamp_header=self.headers.get("X-Chatwoot-Timestamp"),
                        secret=settings.chatwoot_webhook_secret,
                    )
                except ValidationError:
                    self._json(401, {"error": "signature verification failed"})
                    return
                self._enqueue_json("chatwoot_event", raw)
                return
            if path == "/webhooks/meta":
                if not settings.meta_app_secret:
                    self._json(503, {"error": "Meta webhook not configured"})
                    return
                raw = self._read_body()
                if raw is None:
                    return
                try:
                    verify_payload_signature(
                        raw_body=raw,
                        signature_header=self.headers.get("X-Hub-Signature-256"),
                        app_secret=settings.meta_app_secret,
                    )
                except ValidationError:
                    self._json(401, {"error": "signature verification failed"})
                    return
                self._enqueue_json("meta_event", raw)
                return
            self._json(404, {"error": "not found"})

    return Handler


def build_server(
    settings: Settings, outbox: Outbox, store: SqliteStore | None = None
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(
        (settings.http_host, settings.http_port),
        make_handler(settings, outbox, store),
    )

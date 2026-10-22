"""HTTP adapter (stdlib `http.server`, ADR-0009).

Routes:
- GET  /health             liveness, no secrets
- POST /webhooks/chatwoot  signed Chatwoot Agent Bot events -> outbox (202)
- GET  /webhooks/meta      Meta subscription handshake (exit-path prep)
- POST /webhooks/meta      signed Meta events -> outbox (202)

Security posture: signatures are verified on the RAW body before any parsing;
missing configuration fails closed (503), bad signatures 401, oversized
bodies 413, malformed JSON 400. Webhook handlers only *enqueue* — processing
happens in the outbox worker so we can ACK fast, per platform expectations.
Nothing here sends messages.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .. import __version__
from ..config import Settings
from ..domain.errors import ValidationError
from ..ports.repositories import Outbox
from .chatwoot import verify_chatwoot_signature
from .meta_instagram import verify_payload_signature, verify_webhook_subscription

MAX_BODY_BYTES = 1_048_576  # 1 MiB


def make_handler(settings: Settings, outbox: Outbox) -> type[BaseHTTPRequestHandler]:
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
            if length < 0 or length > MAX_BODY_BYTES:
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

        # -- routes ---------------------------------------------------------
        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
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


def build_server(settings: Settings, outbox: Outbox) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(
        (settings.http_host, settings.http_port), make_handler(settings, outbox)
    )

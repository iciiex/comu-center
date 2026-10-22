"""Vercel Python serverless function: GET /api/health

Reports demo/core status as JSON. Stdlib-only so it runs on Vercel without a
build step. It tries to import the real core package from ``src/`` and reports
honestly if that is unavailable in the serverless environment.

This endpoint has no side effects and exposes no secrets or configuration.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler


def health_payload() -> dict[str, object]:
    core_version: str | None = None
    try:
        src = os.path.join(os.path.dirname(__file__), "..", "src")
        if os.path.isdir(src) and src not in sys.path:
            sys.path.insert(0, src)
        import invar_comms  # noqa: PLC0415

        core_version = str(invar_comms.__version__)
    except Exception:  # noqa: BLE001 - report honestly, never fake core health
        core_version = None
    return {
        "status": "ok",
        "service": "invar-comms",
        "demo": True,
        "core_version": core_version,
        "core_available": core_version is not None,
        "live_messaging": False,
        "note": "Foundation demo only — no customer channel is connected.",
    }


class handler(BaseHTTPRequestHandler):  # noqa: N801 - Vercel expects this name
    def do_GET(self) -> None:  # noqa: N802
        body = json.dumps(health_payload()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return  # keep function logs clean

"""Tests for the Vercel demo health function (api/health.py)."""

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load_health_module():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("vercel_health", ROOT / "api" / "health.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_health_payload_is_honest_demo_status() -> None:
    payload = _load_health_module().health_payload()
    assert payload["status"] == "ok"
    assert payload["demo"] is True
    assert payload["live_messaging"] is False
    # Locally the real core package must be importable from src/.
    assert payload["core_available"] is True
    assert payload["core_version"] == "0.1.0"

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import replace

from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import VISITOR, login


def _id() -> str:
    return str(uuid.uuid4())


def test_org_units_api_is_gated_when_feature_is_off(client: TestClient, settings) -> None:
    login(client, settings, VISITOR)
    response = client.get("/api/v1/tribal/org-units")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEATURE_DISABLED"


def test_org_units_api_is_tenant_scoped_and_paginated(settings) -> None:
    enabled_settings = replace(settings, tribal_gamification_enabled=True)
    app = create_app(enabled_settings)
    with TestClient(app) as client:
        login(client, enabled_settings, VISITOR)
        conn = sqlite3.connect(enabled_settings.db_path)
        try:
            org_id = conn.execute("SELECT organization_id FROM users LIMIT 1").fetchone()[0]
            now = "2026-11-12T12:00:00+00:00"
            type_id = _id()
            conn.execute(
                """INSERT INTO org_unit_types
                   (id, organization_id, code, label, created_at) VALUES (?, ?, ?, ?, ?)""",
                (type_id, org_id, "team", "Team", now),
            )
            for name in ("Alpha", "Beta", "Gamma"):
                conn.execute(
                    """INSERT INTO org_units
                       (id, organization_id, type_id, name, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (_id(), org_id, type_id, name, now, now),
                )
            conn.commit()
        finally:
            conn.close()

        first = client.get("/api/v1/tribal/org-units?limit=2")
        assert first.status_code == 200, first.text
        payload = first.json()
        assert [item["name"] for item in payload["items"]] == ["Alpha", "Beta"]
        assert payload["next_cursor"]
        second = client.get(
            "/api/v1/tribal/org-units?limit=2&cursor=" + payload["next_cursor"]
        )
        assert [item["name"] for item in second.json()["items"]] == ["Gamma"]
        outsider = client.get("/api/v1/tribal/org-units/not-a-unit")
        assert outsider.status_code == 404
        assert "Gamma" not in outsider.text

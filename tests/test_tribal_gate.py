from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import VISITOR, login


def test_tribal_bootstrap_is_feature_disabled_by_default(client: TestClient, settings) -> None:
    assert client.get("/api/v1/tribal/bootstrap").status_code == 401
    login(client, settings, VISITOR)
    response = client.get("/api/v1/tribal/bootstrap")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEATURE_DISABLED"


def test_tribal_bootstrap_does_not_expose_legacy_demo_data(settings) -> None:
    enabled_settings = replace(settings, tribal_gamification_enabled=True)
    app = create_app(enabled_settings)
    with TestClient(app) as client:
        login(client, enabled_settings, VISITOR)
        response = client.get("/api/v1/tribal/bootstrap")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODULE_NOT_CONFIGURED"
    assert "users" not in response.json()
    assert "organization" not in response.json()

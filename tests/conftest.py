from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.security import COOKIE_NAME, csrf_for

TEST_OPERATOR_KEY = "synthetic-fixture-authorized-operator-key-only"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        env="test",
        db_path=tmp_path / "kiloos.db",
        evidence_dir=tmp_path / "evidence",
        secret="test-secret-that-is-long-enough-1234567890",
        demo_mode="legacy",
        demo_operator_key=TEST_OPERATOR_KEY,
    )


@pytest.fixture
def play_settings(settings: Settings) -> Settings:
    return replace(settings, demo_mode="play")


@pytest.fixture
def play_client(play_settings):
    with TestClient(create_app(play_settings), base_url="https://play.test") as client:
        yield client


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app, base_url="https://legacy.test") as test_client:
        yield test_client


@pytest.fixture
def db(client: TestClient, settings: Settings) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def csrf(client: TestClient, settings: Settings) -> str:
    """CSRF value for the session currently held by the test client."""
    token = (client.cookies.get(COOKIE_NAME) or "").strip('"')
    assert token, "no session cookie; call login() first"
    return csrf_for(token, settings.legacy_session_secret)


def post(
    client: TestClient,
    settings: Settings,
    path: str,
    *,
    data: dict | None = None,
    files: dict | None = None,
    follow_redirects: bool = True,
):
    """POST a form with a valid CSRF token (unlike the real form, this is explicit)."""
    payload = dict(data or {})
    payload["csrf"] = csrf(client, settings)
    if files is not None:
        return client.post(path, data=payload, files=files, follow_redirects=follow_redirects)
    return client.post(path, data=payload, follow_redirects=follow_redirects)


def login(client: TestClient, settings: Settings, mobile: str) -> None:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT id FROM users WHERE mobile = ?", (mobile,)).fetchone()
        assert row is not None, f"seed user {mobile} missing"
        user_id = row["id"]
    finally:
        conn.close()
    response = client.post(
        "/demo-login", data={"user_id": user_id, "operator_key": settings.demo_operator_key}
    )
    assert response.status_code == 200


def row_id(settings: Settings, sql: str, params: tuple) -> str:
    conn = sqlite3.connect(settings.db_path)
    try:
        row = conn.execute(sql, params).fetchone()
        assert row is not None
        return str(row[0])
    finally:
        conn.close()


VISITOR = "09120000001"  # سارا محمدی
OTHER_VISITOR = "09120000002"  # امیر رضایی
OPERATOR = "09120000004"
ADMIN = "09120000005"

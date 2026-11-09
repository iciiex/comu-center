from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        env="test",
        db_path=tmp_path / "kiloos.db",
        evidence_dir=tmp_path / "evidence",
        secret="test-secret-that-is-long-enough-1234567890",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(client: TestClient, settings: Settings) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def login(client: TestClient, settings: Settings, mobile: str) -> None:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT id FROM users WHERE mobile = ?", (mobile,)).fetchone()
        assert row is not None, f"seed user {mobile} missing"
        user_id = row["id"]
    finally:
        conn.close()
    response = client.post("/demo-login", data={"user_id": user_id})
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

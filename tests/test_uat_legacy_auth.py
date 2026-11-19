"""UAT-01/05: verify browser auth and old direct URLs in each explicit mode."""

from contextlib import closing
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import create_app
from app.security import COOKIE_NAME, make_token
from tests.conftest import ADMIN, VISITOR, row_id

LEGACY_AUTH_PATHS = ("/demo-login", "/api/v1/game/demo-users", "/api/v1/game/demo-login")
MARKER_NAME = "حساب خارج از دموی آزمایشی"
MARKER_ID = "synthetic-marked-non-demo-account"
BASE = "https://isolated.test"


def add_non_demo_account(settings):
    with closing(db.connect(settings.db_path)) as conn, conn:
        conn.execute(
            """INSERT INTO users (id,organization_id,full_name,mobile,role,is_active,created_at)
               SELECT ?,organization_id,?,'09000009999','visitor',1,created_at
               FROM users WHERE mobile=?""",
            (MARKER_ID, MARKER_NAME, VISITOR),
        )


def test_uat05_play_never_dispatches_legacy_routes_or_reads_legacy_db(play_settings, monkeypatch):
    db.init_db(play_settings.db_path, play_settings.evidence_dir)
    add_non_demo_account(play_settings)
    legacy = replace(play_settings, demo_mode="legacy")
    uid = row_id(legacy, "SELECT id FROM users WHERE mobile=?", (ADMIN,))
    old_token = make_token(uid, legacy.legacy_session_secret)
    before = play_settings.db_path.read_bytes()
    connect = db.connect

    def protect(path):
        assert path != play_settings.db_path, "Play attempted to open the legacy database"
        return connect(path)

    monkeypatch.setattr(db, "connect", protect)
    with TestClient(create_app(play_settings), base_url=BASE) as play:
        play.cookies.set(COOKIE_NAME, old_token, domain="isolated.test", path="/")
        assert play.get("/").url.path == "/play/entrance"
        assert play.get("/login").url.path == "/play/entrance"
        login = play.get(f"/login?s={old_token}", follow_redirects=False)
        assert login.status_code == 303 and login.headers["location"] == "/play/entrance"
        assert login.headers["cache-control"] == "no-store"
        for path in (
            *LEGACY_AUTH_PATHS,
            "/logout",
            "/home",
            "/admin/sales",
            "/api/v1/game/bootstrap",
        ):
            # Direct URLs, also with a formerly valid token, never reach legacy handlers.
            assert play.get(path, follow_redirects=False).status_code == 404
            assert play.get(f"{path}?s={old_token}", follow_redirects=False).status_code == 404
        for path in LEGACY_AUTH_PATHS:
            resp = play.post(path, data={"user_id": MARKER_ID}, follow_redirects=False)
            assert resp.status_code == 404 and "set-cookie" not in resp.headers
        assert MARKER_NAME not in play.get("/login").text
        assert (
            play.get("/play/admin/export", headers={"Accept": "application/json"}).status_code
            == 401
        )
    assert play_settings.db_path.read_bytes() == before


def test_uat05_off_and_prod_have_no_demo_picker_or_url_auth(settings):
    db.init_db(settings.db_path, settings.evidence_dir)
    add_non_demo_account(settings)
    before = settings.db_path.read_bytes()
    for cfg in (replace(settings, demo_mode="off"), replace(settings, env="prod")):
        uid = row_id(cfg, "SELECT id FROM users WHERE mobile=?", (ADMIN,))
        token = make_token(uid, cfg.legacy_session_secret)
        with TestClient(create_app(cfg), base_url=BASE) as client:
            page = client.get("/login")
            assert (
                page.status_code == 401
                and MARKER_NAME not in page.text
                and MARKER_ID not in page.text
            )
            assert 'name="user_id"' not in page.text
            assert client.get("/play/").status_code == 404
            assert client.post("/demo-login", data={"user_id": uid}).status_code == 404
            assert client.get("/api/v1/game/demo-users").status_code == 404
            assert (
                client.post("/api/v1/game/demo-login", json={"user_id": MARKER_ID}).status_code
                == 404
            )
            protected = client.get(f"/admin/sales?s={token}", follow_redirects=False)
            assert protected.status_code == 303 and protected.headers["location"] == "/login"
            for old_secret in (cfg.secret, settings.legacy_session_secret):
                client.cookies.set(COOKIE_NAME, make_token(uid, old_secret))
                assert client.get("/admin/sales", follow_redirects=False).status_code == 303
            # A legitimate versioned session from a trusted issuer can still use legacy screens.
            client.cookies.set(COOKIE_NAME, token)
            assert client.get("/login").url.path == "/home"
            assert client.get("/admin/sales").status_code == 200
    assert settings.db_path.read_bytes() == before
    assert not settings.db_path.with_name(
        settings.db_path.name + ".kilos-play-demo.sqlite3"
    ).exists()


def test_uat05_explicit_legacy_demo_only_allows_seed_identities_and_staff_key(client, settings):
    add_non_demo_account(settings)
    assert client.get("/").url.path == "/login"
    picker = client.get("/login").text
    api = client.get("/api/v1/game/demo-users").text
    for contents in (picker, api):
        assert MARKER_NAME not in contents and MARKER_ID not in contents
    assert len(client.get("/api/v1/game/demo-users").json()["users"]) == 3
    assert client.post("/demo-login", data={"user_id": MARKER_ID}).status_code == 404
    assert client.post("/api/v1/game/demo-login", json={"user_id": MARKER_ID}).status_code == 404
    uid = row_id(settings, "SELECT id FROM users WHERE mobile=?", (ADMIN,))
    assert client.post("/api/v1/game/demo-login", json={"user_id": uid}).status_code == 404
    for operator_key in ("", "not-authorized"):
        response = client.post("/demo-login", data={"user_id": uid, "operator_key": operator_key})
        assert response.status_code == 401 and not client.cookies.get(COOKIE_NAME)
    form = {"user_id": uid, "operator_key": settings.demo_operator_key}
    assert (
        client.post(
            "/demo-login", data=form, headers={"Origin": "https://unrelated.test"}
        ).status_code
        == 403
    )
    response = client.post("/demo-login", data=form, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"].startswith(
        "/admin/submissions?s="
    )
    assert "Secure" in response.headers["set-cookie"]
    assert client.get("/admin/sales").status_code == 200


def test_uat01_demo_mode_fails_closed_without_an_independent_operator_key(play_settings):
    for mode in ("play", "legacy"):
        for key in ("", "short-key", play_settings.secret):
            with pytest.raises(RuntimeError, match="KILOOS_DEMO_OPERATOR_KEY"):
                create_app(replace(play_settings, demo_mode=mode, demo_operator_key=key))
    assert not list(play_settings.db_path.parent.iterdir())

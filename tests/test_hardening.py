"""Hardening behaviour: cookie-less sessions, CSRF, rate limit, paging, retention."""

from __future__ import annotations

import re
import sqlite3
import time
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.db import connect
from app.main import create_app
from app.maintenance import purge_evidence
from app.security import COOKIE_NAME, csrf_for, make_token
from app.seed import PNG_1PX
from tests.conftest import OPERATOR, VISITOR, login, post, row_id

MISSION_ONE = "ثبت تصویر یخچال فروشگاه"


def token_csrf(settings: Settings, token: str) -> str:
    return csrf_for(token, settings.secret)


def test_session_token_in_url_works_without_cookies(
    client: TestClient, settings: Settings
) -> None:
    """The shared preview iframe blocks cookies; the signed token is the fallback."""
    user_id = row_id(settings, "SELECT id FROM users WHERE mobile = ?", (VISITOR,))
    response = client.post(
        "/demo-login", data={"user_id": user_id}, follow_redirects=False
    )
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/home?s=")
    token = location.split("s=", 1)[1]

    client.cookies.clear()  # simulate a browser that rejected the cookie
    home = client.get(location)
    assert home.status_code == 200
    assert "امتیاز فعلی شما" in home.text
    assert f'name="csrf" value="{token_csrf(settings, token)}"' in home.text

    match = re.search(r'href="(/missions\?s=[^"]+)"', home.text)
    assert match is not None, "internal links must carry the fallback token"
    missions = client.get(match.group(1))
    assert missions.status_code == 200
    assert MISSION_ONE in missions.text


def test_token_only_session_can_post_forms(client: TestClient, settings: Settings) -> None:
    user_id = row_id(settings, "SELECT id FROM users WHERE mobile = ?", (VISITOR,))
    location = client.post(
        "/demo-login", data={"user_id": user_id}, follow_redirects=False
    ).headers["location"]
    token = location.split("s=", 1)[1]
    client.cookies.clear()

    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (MISSION_ONE,))
    response = client.post(
        f"/missions/{mission_id}/submissions?s={token}",
        data={
            "request_id": "token-post-1",
            "note": "ثبت بدون کوکی",
            "csrf": token_csrf(settings, token),
        },
        files={"evidence": ("evidence.png", PNG_1PX, "image/png")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/submissions/")
    assert "s=" in response.headers["location"]


def test_admin_queue_carries_token_between_pages(
    client: TestClient, settings: Settings
) -> None:
    operator_id = row_id(settings, "SELECT id FROM users WHERE mobile = ?", (OPERATOR,))
    location = client.post(
        "/demo-login", data={"user_id": operator_id}, follow_redirects=False
    ).headers["location"]
    assert location.startswith("/admin/submissions?s=")

    client.cookies.clear()
    queue = client.get(location)
    assert queue.status_code == 200
    assert "صف بررسی" in queue.text
    assert re.search(r"/admin/missions\?s=", queue.text) is not None


def test_post_without_csrf_is_rejected(client: TestClient, settings: Settings) -> None:
    login(client, settings, VISITOR)
    response = client.post("/logout", data={}, follow_redirects=False)
    assert response.status_code == 403
    assert "اعتبار فرم" in response.text


def test_post_with_forged_csrf_is_rejected(client: TestClient, settings: Settings) -> None:
    login(client, settings, VISITOR)
    response = client.post("/logout", data={"csrf": "forged"}, follow_redirects=False)
    assert response.status_code == 403


def test_forged_csrf_upload_creates_nothing(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, VISITOR)
    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (MISSION_ONE,))
    response = client.post(
        f"/missions/{mission_id}/submissions",
        data={"request_id": "forged-1", "csrf": "forged"},
    )
    assert response.status_code == 403
    created = db.execute(
        "SELECT COUNT(*) FROM submissions WHERE request_id = 'forged-1'"
    ).fetchone()[0]
    assert created == 0


def test_forms_render_a_csrf_field(client: TestClient, settings: Settings) -> None:
    login(client, settings, VISITOR)
    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (MISSION_ONE,))
    page = client.get(f"/missions/{mission_id}")
    match = re.search(r'name="csrf" value="([0-9a-f]{64})"', page.text)
    assert match is not None


def test_expired_token_is_rejected(client: TestClient, settings: Settings) -> None:
    user_id = row_id(settings, "SELECT id FROM users WHERE mobile = ?", (VISITOR,))
    stale = make_token(user_id, settings.secret, now=time.time() - 48 * 3600)
    response = client.get(f"/home?s={stale}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_is_rate_limited(client: TestClient, settings: Settings) -> None:
    user_id = row_id(settings, "SELECT id FROM users WHERE mobile = ?", (VISITOR,))
    for _ in range(settings.login_rate_limit):
        assert (
            client.post(
                "/demo-login", data={"user_id": user_id}, follow_redirects=False
            ).status_code
            == 303
        )
    blocked = client.post(
        "/demo-login", data={"user_id": user_id}, follow_redirects=False
    )
    assert blocked.status_code == 429
    assert "بیش از حد مجاز" in blocked.text


def test_security_headers_and_no_frame_denial(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "X-Frame-Options" not in response.headers  # preview embeds the app
    assert "frame-ancestors *" in response.headers["Content-Security-Policy"]


def test_unknown_route_renders_persian_404(client: TestClient) -> None:
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "یافت نشد" in response.text


def test_admin_queue_paginates(tmp_path: Path) -> None:
    settings = Settings(
        env="test",
        db_path=tmp_path / "paged.db",
        evidence_dir=tmp_path / "evidence",
        secret="test-secret-that-is-long-enough-1234567890",
        queue_page_size=1,
    )
    with TestClient(create_app(settings)) as client:
        mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (MISSION_ONE,))
        conn = connect(settings.db_path)
        try:
            users = [
                row["id"]
                for row in conn.execute(
                    "SELECT id FROM users WHERE mobile IN ('09120000001', '09120000003')"
                )
            ]
        finally:
            conn.close()
        assert len(users) == 2

        for index, visit in enumerate(users):
            client.post("/demo-login", data={"user_id": visit}, follow_redirects=False)
            response = post(
                client,
                settings,
                f"/missions/{mission_id}/submissions",
                data={"request_id": f"paged-{index}", "note": "page test"},
                files={"evidence": ("evidence.png", PNG_1PX, "image/png")},
                follow_redirects=False,
            )
            assert response.status_code == 303
            post(client, settings, "/logout", follow_redirects=False)

        login(client, settings, OPERATOR)
        first = client.get("/admin/submissions")
        assert first.status_code == 200
        assert "صفحه ۱ از ۲" in first.text
        assert first.text.count("btn--ghost btn--sm\" href=\"/admin/submissions/") == 1

        second = client.get("/admin/submissions?page=2")
        assert second.status_code == 200
        assert "صفحه ۲ از ۲" in second.text

        clamped = client.get("/admin/submissions?page=99")
        assert "صفحه ۲ از ۲" in clamped.text


def test_evidence_retention_purges_only_old_files(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    submission_id = db.execute("SELECT id FROM submissions LIMIT 1").fetchone()["id"]
    old_id, recent_id = str(uuid.uuid4()), str(uuid.uuid4())
    (settings.evidence_dir / "old.png").write_bytes(b"old")
    (settings.evidence_dir / "recent.png").write_bytes(b"recent")
    db.execute(
        """INSERT INTO submission_evidences
           (id, submission_id, file_name, content_type, storage_path, sha256, created_at)
           VALUES (?
           , ?, 'old.png', 'image/png', 'old.png', 'x', '2020-01-01T00:00:00+00:00')""",
        (old_id, submission_id),
    )
    db.execute(
        """INSERT INTO submission_evidences
           (id, submission_id, file_name, content_type, storage_path, sha256, created_at)
           VALUES (?, ?, 'recent.png', 'image/png', 'recent.png', 'y', ?)""",
        (recent_id, submission_id, db.execute("SELECT datetime('now') AS n").fetchone()["n"]),
    )
    db.commit()

    result = purge_evidence(settings, retention_days=90)
    assert result["candidates"] == 1
    assert result["deleted"] == 1
    assert not (settings.evidence_dir / "old.png").exists()
    assert (settings.evidence_dir / "recent.png").exists()
    assert db.execute(
        "SELECT COUNT(*) FROM submission_evidences WHERE id = ?", (old_id,)
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM submission_evidences WHERE id = ?", (recent_id,)
    ).fetchone()[0] == 1
    assert db.execute(
        "SELECT COUNT(*) FROM audit_logs WHERE action = 'evidence.purged'"
    ).fetchone()[0] == 1


def test_dry_run_deletes_nothing(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    submission_id = db.execute("SELECT id FROM submissions LIMIT 1").fetchone()["id"]
    (settings.evidence_dir / "dry.png").write_bytes(b"dry")
    db.execute(
        """INSERT INTO submission_evidences
           (id, submission_id, file_name, content_type, storage_path, sha256, created_at)
           VALUES (?, ?, 'dry.png', 'image/png', 'dry.png', 'z', '2020-01-01T00:00:00+00:00')""",
        (str(uuid.uuid4()), submission_id),
    )
    db.commit()
    result = purge_evidence(settings, retention_days=90, dry_run=True)
    assert result["candidates"] == 1
    assert (settings.evidence_dir / "dry.png").exists()


def test_cookie_session_still_works(client: TestClient, settings: Settings) -> None:
    login(client, settings, VISITOR)
    assert client.cookies.get(COOKIE_NAME)
    response = client.get("/home")
    assert response.status_code == 200
    assert "/missions?s=" not in response.text  # clean URLs when cookies work

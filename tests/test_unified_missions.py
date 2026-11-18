"""Unified missions (D-009 PROPOSED): admin mission -> game -> submission -> review -> rewards.

Organizational points live only in score_events; XP/coins only in game_reward_events.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app import game_rewards
from app.config import Settings
from app.seed import PNG_1PX
from tests.conftest import ADMIN, OPERATOR, VISITOR, login, post, row_id

V2 = {"X-Game-Api": "2"}
TITLE = "معرفی محصول جدید"


def _day(offset: int) -> str:
    return (datetime.now(tz=UTC) + timedelta(days=offset)).date().isoformat()


def _form(title: str = TITLE, **over) -> dict:
    data = {
        "title": title,
        "description": "معرفی محصول جدید به مشتریان فروشگاه.",
        "instructions": "۱. محصول را معرفی کنید. ۲. واکنش مشتری را بنویسید.",
        "category": "product_intro",
        "difficulty": "easy",
        "estimated_minutes": "10",
        "points": "20",
        "game_xp": "100",
        "game_coins": "20",
        "max_per_user": "1",
        "starts_on": _day(-1),
        "ends_on": _day(10),
        "requires_evidence": "0",
        "requires_review": "1",
    }
    data.update(over)
    return data


def _create(client: TestClient, settings: Settings, publish: bool = True, **over) -> str:
    login(client, settings, ADMIN)
    form = _form(**over)
    response = post(client, settings, "/admin/missions/new", data=form)
    assert response.status_code == 200, response.text
    mission_id = row_id(settings, "SELECT id FROM missions WHERE title = ?", (form["title"],))
    if publish:
        assert post(client, settings, f"/admin/missions/{mission_id}/publish").status_code == 200
    return mission_id


def _boot(client: TestClient) -> dict:
    response = client.get("/api/v1/game/bootstrap", headers=V2)
    assert response.status_code == 200, response.text
    return response.json()


def _mission(client: TestClient, mission_id: str) -> dict | None:
    return next((m for m in _boot(client)["missions"] if m["id"] == mission_id), None)


def _submit(client: TestClient, mission_id: str, key: str, answer: str = "پاسخ آزمایشی",
            image: bool = False, headers: dict | None = None):
    boot = _boot(client)
    sent = {**V2, "X-CSRF-Token": boot["csrf_token"], "Idempotency-Key": key}
    sent.update(headers or {})
    files = {"evidence": ("shot.png", PNG_1PX, "image/png")} if image else None
    return client.post(
        f"/api/v1/game/missions/{mission_id}/submissions",
        data={"answer": answer}, files=files, headers=sent,
    )


def _review(client, settings, submission_id: str, decision: str, reason: str = ""):
    login(client, settings, OPERATOR)
    data = {"decision": decision}
    if reason:
        data["reason"] = reason
    return post(client, settings, f"/admin/submissions/{submission_id}/review", data=data)


def _sub_id(settings: Settings, key: str) -> str:
    return row_id(settings, "SELECT id FROM submissions WHERE request_id = ?", (key,))


def _org_points(db: sqlite3.Connection, submission_id: str) -> float:
    row = db.execute(
        "SELECT COALESCE(SUM(points), 0) AS p FROM score_events WHERE source_id = ?",
        (submission_id,),
    ).fetchone()
    return float(row["p"])


def _game_events(db: sqlite3.Connection, submission_id: str) -> list[sqlite3.Row]:
    return db.execute(
        "SELECT * FROM game_reward_events WHERE source_id = ?", (submission_id,)
    ).fetchall()


def test_full_scenario_create_publish_submit_review_rewards_and_retries(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    mission_id = _create(client, settings)
    login(client, settings, VISITOR)
    before = _boot(client)
    view = _mission(client, mission_id)
    assert view is not None and view["title"] == TITLE
    assert (view["orgPoints"], view["xpReward"], view["coinReward"]) == (20, 100, 20)
    assert view["status"] == "available" and view["remaining"] == 1
    assert view["category"] == "product_intro" and view["estimatedMinutes"] == 10
    assert view["instructions"].startswith("۱.")
    assert before["progress"]["daily"] is None  # v2 exposes no daily challenge

    response = _submit(client, mission_id, "key-1", answer="معرفی انجام شد؛ مشتری استقبال کرد.")
    assert response.status_code == 201, response.text
    assert response.headers["Idempotent-Replay"] == "false"
    submission_id = _sub_id(settings, "key-1")

    # appears in the existing operator review queue
    login(client, settings, OPERATOR)
    queue = client.get("/admin/submissions?status=submitted")
    assert TITLE in queue.text

    # pending: no rewards anywhere
    login(client, settings, VISITOR)
    pending = _mission(client, mission_id)
    assert pending["status"] == "pending_review" and pending["canStart"] is False
    boot = _boot(client)
    assert (boot["progress"]["xp"], boot["progress"]["coins"]) == (0, 0)
    assert _org_points(db, submission_id) == 0 and not _game_events(db, submission_id)

    assert _review(client, settings, submission_id, "approve").status_code == 200

    login(client, settings, VISITOR)
    approved = _mission(client, mission_id)
    assert approved["status"] == "approved" and approved["completions"] == 1
    assert _org_points(db, submission_id) == 20
    events = _game_events(db, submission_id)
    assert len(events) == 1 and (events[0]["xp"], events[0]["coins"]) == (100, 20)
    boot = _boot(client)
    assert (boot["progress"]["xp"], boot["progress"]["coins"]) == (100, 20)
    # separate economies: the org wallet is not touched by XP/coins
    wallet = db.execute(
        "SELECT balance FROM point_wallets WHERE user_id = (SELECT user_id FROM submissions "
        "WHERE id = ?)",
        (submission_id,),
    ).fetchone()
    assert float(wallet["balance"]) == 20
    history = client.get("/api/v1/game/history", headers=V2).json()["items"]
    assert history and history[0]["rewards"]["xp"] == 100

    # repeated approval and request retries never pay twice
    assert _review(client, settings, submission_id, "approve").status_code == 409
    login(client, settings, VISITOR)
    replay = _submit(client, mission_id, "key-1", answer="معرفی انجام شد؛ مشتری استقبال کرد.")
    assert replay.status_code == 200 and replay.headers["Idempotent-Replay"] == "true"
    submission = db.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    assert game_rewards.grant_game_reward(db, submission) is False
    db.commit()
    assert _org_points(db, submission_id) == 20
    assert len(_game_events(db, submission_id)) == 1
    boot = _boot(client)
    assert (boot["progress"]["xp"], boot["progress"]["coins"]) == (100, 20)


def test_draft_and_unstarted_missions_are_hidden_and_not_submittable(
    client: TestClient, settings: Settings
) -> None:
    draft_id = _create(client, settings, publish=False, title="مأموریت پیش‌نویس")
    future_id = _create(client, settings, title="مأموریت آینده",
                        starts_on=_day(5), ends_on=_day(9))
    login(client, settings, VISITOR)
    ids = {m["id"] for m in _boot(client)["missions"]}
    assert draft_id not in ids and future_id not in ids
    assert client.get(f"/api/v1/game/missions/{draft_id}", headers=V2).status_code == 404
    assert _submit(client, draft_id, "k-draft").status_code == 404


def test_expired_mission_is_listed_as_expired_and_cannot_be_started(
    client: TestClient, settings: Settings
) -> None:
    mission_id = _create(client, settings, title="کمپین تمام‌شده", starts_on=_day(-20),
                         ends_on=_day(-2))
    login(client, settings, VISITOR)
    view = _mission(client, mission_id)
    assert view["status"] == "expired" and view["canStart"] is False
    response = _submit(client, mission_id, "k-exp")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "MISSION_EXPIRED"


def test_completion_limit_pending_block_and_rejection_gives_no_rewards(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    mission_id = _create(client, settings, max_per_user="2")
    login(client, settings, VISITOR)
    assert _submit(client, mission_id, "k1").status_code == 201
    blocked = _submit(client, mission_id, "k1-b")
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "SUBMISSION_PENDING"

    assert _review(client, settings, _sub_id(settings, "k1"), "reject").status_code == 409
    rejection = _review(client, settings, _sub_id(settings, "k1"), "reject", "ناخوانا")
    assert rejection.status_code == 200
    login(client, settings, VISITOR)
    rejected = _mission(client, mission_id)
    assert rejected["status"] == "rejected" and rejected["canStart"] is True
    assert rejected["latestSubmission"]["rejectionReason"] == "ناخوانا"
    assert _org_points(db, _sub_id(settings, "k1")) == 0
    assert not _game_events(db, _sub_id(settings, "k1"))
    assert _boot(client)["progress"]["xp"] == 0

    assert _submit(client, mission_id, "k2").status_code == 201
    _review(client, settings, _sub_id(settings, "k2"), "reject", "ناقص")
    login(client, settings, VISITOR)
    capped = _submit(client, mission_id, "k3")
    assert capped.status_code == 409
    assert capped.json()["error"]["code"] == "MAX_ATTEMPTS_REACHED"
    assert _mission(client, mission_id)["canStart"] is False


def test_game_reward_is_frozen_at_submission_time(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    mission_id = _create(client, settings)
    login(client, settings, VISITOR)
    assert _submit(client, mission_id, "snap").status_code == 201
    submission_id = _sub_id(settings, "snap")

    login(client, settings, ADMIN)
    edited = _form(game_xp="999", game_coins="99")
    assert post(client, settings, f"/admin/missions/{mission_id}", data=edited).status_code == 200

    assert _review(client, settings, submission_id, "approve").status_code == 200
    event = _game_events(db, submission_id)[0]
    assert (event["xp"], event["coins"]) == (100, 20)  # not 999/99


def test_auto_approved_mission_awards_both_economies_once(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    mission_id = _create(client, settings, title="مأموریت خودکار", requires_review="0")
    login(client, settings, VISITOR)
    assert _submit(client, mission_id, "auto").status_code == 201
    submission_id = _sub_id(settings, "auto")
    assert _org_points(db, submission_id) == 20
    assert len(_game_events(db, submission_id)) == 1
    assert _mission(client, mission_id)["status"] == "approved"
    assert _submit(client, mission_id, "auto").status_code == 200  # replay
    assert len(_game_events(db, submission_id)) == 1
    assert _boot(client)["progress"]["xp"] == 100


def test_validation_evidence_answer_and_idempotency_conflict(
    client: TestClient, settings: Settings
) -> None:
    needs_photo = _create(client, settings, title="نیازمند تصویر", requires_evidence="1")
    login(client, settings, VISITOR)
    missing = _submit(client, needs_photo, "e1", answer="")
    assert missing.status_code == 422 and missing.json()["error"]["code"] == "EVIDENCE_REQUIRED"
    assert _submit(client, needs_photo, "e2", answer="", image=True).status_code == 201

    text_only = _create(client, settings, title="فقط متن")
    login(client, settings, VISITOR)
    short = _submit(client, text_only, "t1", answer="ا")
    assert short.status_code == 422 and short.json()["error"]["code"] == "ANSWER_REQUIRED"
    assert _submit(client, text_only, "t2", answer="پاسخ درست").status_code == 201
    reused = _submit(client, text_only, "t2", answer="پاسخ دیگر")
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    bad_type = _boot(client)
    response = client.post(
        f"/api/v1/game/missions/{needs_photo}/submissions",
        data={"answer": ""},
        files={"evidence": ("x.gif", b"GIF89a", "image/gif")},
        headers={**V2, "X-CSRF-Token": bad_type["csrf_token"], "Idempotency-Key": "gif"},
    )
    assert response.status_code == 422


def test_game_api_permissions_csrf_and_org_scope(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    mission_id = _create(client, settings)
    anonymous = TestClient(client.app)
    assert anonymous.get("/api/v1/game/missions", headers=V2).status_code == 401

    login(client, settings, VISITOR)
    no_csrf = client.post(
        f"/api/v1/game/missions/{mission_id}/submissions",
        data={"answer": "پاسخ"}, headers={**V2, "Idempotency-Key": "nocsrf"},
    )
    assert no_csrf.status_code == 403
    no_key = client.post(
        f"/api/v1/game/missions/{mission_id}/submissions",
        data={"answer": "پاسخ"},
        headers={**V2, "X-CSRF-Token": _boot(client)["csrf_token"]},
    )
    assert no_key.status_code == 400

    login(client, settings, OPERATOR)
    assert client.get("/api/v1/game/missions", headers=V2).status_code == 403

    # a visitor of another organization cannot see or submit the mission
    org_id, user_id = str(uuid.uuid4()), str(uuid.uuid4())
    db.execute("INSERT INTO organizations (id, name, created_at) VALUES (?, 'سازمان دیگر', 'x')",
               (org_id,))
    db.execute(
        """INSERT INTO users (id, organization_id, full_name, mobile, role, is_active, created_at)
           VALUES (?, ?, 'بیگانه', '09129999999', 'visitor', 1, 'x')""",
        (user_id, org_id),
    )
    db.commit()
    login(client, settings, "09129999999")
    assert _mission(client, mission_id) is None
    assert _submit(client, mission_id, "foreign").status_code == 404


def test_v1_remains_default_and_v2_hides_unavailable_features(
    client: TestClient, settings: Settings
) -> None:
    _create(client, settings)
    login(client, settings, VISITOR)
    v1 = client.get("/api/v1/game/bootstrap").json()
    assert v1["api_version"] == "1" and len(v1["missions"]) == 6
    assert v1["progress"]["daily"] is not None

    v2 = _boot(client)
    assert v2["api_version"] == "2"
    assert not any(m["id"] == "customer-visit-challenge" for m in v2["missions"])
    flags = {a["id"]: a["available"] for a in v2["achievements_catalog"]}
    assert flags["trailblazer"] is False and flags["daily_hero"] is False
    assert flags["first_steps"] is True
    # catalog missions cannot be completed through the v2 contract
    response = client.post(
        "/api/v1/game/missions/customer-visit-challenge/completions",
        json={"answers": {}},
        headers={**V2, "X-CSRF-Token": v2["csrf_token"], "Idempotency-Key": "c1"},
    )
    assert response.status_code == 404


def test_v2_drafts_use_db_missions(client: TestClient, settings: Settings) -> None:
    mission_id = _create(client, settings)
    login(client, settings, VISITOR)
    token = _boot(client)["csrf_token"]
    headers = {**V2, "X-CSRF-Token": token}
    saved = client.put(
        f"/api/v1/game/missions/{mission_id}/draft",
        json={"step_index": 0, "answers": {"answer": "پیش‌نویس"}}, headers=headers,
    )
    assert saved.status_code == 200, saved.text
    assert next(m for m in saved.json()["missions"] if m["id"] == mission_id)["status"] == (
        "in_progress"
    )
    bad = client.put(
        f"/api/v1/game/missions/{mission_id}/draft",
        json={"step_index": 0, "answers": {"evidence": "x"}}, headers=headers,
    )
    assert bad.status_code == 422
    cleared = client.delete(f"/api/v1/game/missions/{mission_id}/draft", headers=headers)
    assert next(m for m in cleared.json()["missions"] if m["id"] == mission_id)["status"] == (
        "available"
    )


def test_admin_form_validation_and_edit_round_trip(
    client: TestClient, settings: Settings, db: sqlite3.Connection
) -> None:
    login(client, settings, ADMIN)
    for field, value in (("game_xp", "-5"), ("game_coins", "abc"), ("difficulty", "insane"),
                         ("category", "nope"), ("estimated_minutes", "0")):
        response = post(client, settings, "/admin/missions/new", data=_form(**{field: value}))
        assert response.status_code == 422, field
        assert "alert--error" in response.text
    mission_id = _create(client, settings)
    row = db.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
    assert (row["game_xp"], row["game_coins"], row["category"], row["requires_evidence"]) == (
        100, 20, "product_intro", 0)
    page = client.get(f"/admin/missions/{mission_id}")
    assert 'value="100"' in page.text and "پاداش‌ها" in page.text


def test_existing_web_flow_and_legacy_forms_still_work(
    client: TestClient, settings: Settings
) -> None:
    """A pre-0007 style admin form (no new fields) still creates a mission with safe defaults."""
    login(client, settings, ADMIN)
    legacy = {"title": "فرم قدیمی", "description": "توضیح کافی برای مأموریت.", "points": "7",
              "max_per_user": "1", "starts_on": _day(-1), "ends_on": _day(5)}
    assert post(client, settings, "/admin/missions/new", data=legacy).status_code == 200
    row = row_id(settings, "SELECT requires_review || game_xp FROM missions WHERE title = ?",
                 ("فرم قدیمی",))
    assert row == "10"

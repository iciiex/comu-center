from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from app import game_quests
from app.config import Settings
from tests.conftest import VISITOR, login

CUSTOMER_VISIT = {"customer_type": "new", "outcome": "order_received", "rating": 5}
PRODUCT_SPOTLIGHT = {"showcase": "new_product", "reaction": "loved_it", "rating": 4}
FOLLOW_UP = {"channel": "call", "result": "order", "rating": 4}
CLAIM = "/api/v1/game/quests/{quest_id}/claim"
ALL_QUESTS = {
    "weekly-momentum",
    "product-champion",
    "customer-coverage",
    "consistency-streak",
    "team-challenge",
}


def bootstrap(client: TestClient) -> dict:
    response = client.get("/api/v1/game/bootstrap")
    assert response.status_code == 200, response.text
    return response.json()


def csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": bootstrap(client)["csrf_token"]}


def complete(client: TestClient, headers: dict, mission_id: str, answers: dict, key: str) -> dict:
    response = client.post(
        f"/api/v1/game/missions/{mission_id}/completions",
        json={"answers": answers},
        headers={**headers, "Idempotency-Key": key},
    )
    assert response.status_code == 200, response.text
    return response.json()


def claim(client: TestClient, headers: dict, quest_id: str, key: str | None):
    extra = {"Idempotency-Key": key} if key is not None else {}
    return client.post(CLAIM.format(quest_id=quest_id), headers={**headers, **extra})


def quests_by_id(payload: dict) -> dict[str, dict]:
    return {quest["id"]: quest for quest in payload["quests"]["quests"]}


def test_week_key_and_bounds_follow_iso_weeks_in_utc() -> None:
    # 2026-11-18 is a Wednesday; its ISO week runs Monday 2026-11-16 to Sunday 2026-11-22.
    assert game_quests.week_key("2026-11-18") == "2026-W47"
    assert game_quests.week_bounds("2026-11-18") == ("2026-11-16", "2026-11-22")
    assert game_quests.week_bounds("2026-11-22") == ("2026-11-16", "2026-11-22")


def test_weekly_quests_are_demo_labelled_and_start_in_progress(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, VISITOR)
    payload = bootstrap(client)
    weekly = payload["quests"]
    assert weekly["label"] == "DEMO"
    assert weekly["weekKey"] == game_quests.week_key(payload["date_key"])
    quests = quests_by_id(payload)
    assert set(quests) == ALL_QUESTS
    assert all(q["status"] == "in_progress" and q["progress"] == 0 for q in quests.values())
    assert all(q["rewardXp"] > 0 for q in quests.values())


def test_weekly_quest_claims_are_server_checked_once_per_week_and_pay_game_xp_only(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, VISITOR)
    headers = csrf(client)

    missing_key = claim(client, headers, "weekly-momentum", None)
    assert missing_key.status_code == 400
    unknown = claim(client, headers, "not-a-quest", "q-unknown")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "QUEST_NOT_FOUND"
    no_csrf = client.post(
        CLAIM.format(quest_id="weekly-momentum"), headers={"Idempotency-Key": "q-x"}
    )
    assert no_csrf.status_code == 403

    early = claim(client, headers, "weekly-momentum", "q-early")
    assert early.status_code == 409
    assert early.json()["error"]["code"] == "QUEST_NOT_COMPLETE"

    # Five completions in three categories: customer visit x2, product intro x2 (unlocked by the
    # customer visit), follow-up x1. Repeats are allowed for base missions.
    complete(client, headers, "customer-visit-challenge", CUSTOMER_VISIT, "q-cv-1")
    complete(client, headers, "product-spotlight", PRODUCT_SPOTLIGHT, "q-ps-1")
    complete(client, headers, "product-spotlight", PRODUCT_SPOTLIGHT, "q-ps-2")
    complete(client, headers, "follow-up-sprint", FOLLOW_UP, "q-fu-1")
    last = complete(client, headers, "customer-visit-challenge", CUSTOMER_VISIT, "q-cv-2")

    quests = quests_by_id(last)
    assert quests["weekly-momentum"]["complete"] is True
    assert quests["weekly-momentum"]["status"] == "claimable"
    assert quests["product-champion"]["complete"] is True
    assert quests["customer-coverage"]["complete"] is True
    assert quests["consistency-streak"]["complete"] is False
    assert quests["consistency-streak"]["progress"] == 1

    xp_before = client.get("/api/v1/game/progress").json()["progress"]["xp"]
    with sqlite3.connect(settings.db_path) as conn:
        org_before = conn.execute("SELECT COUNT(*) FROM score_events").fetchone()[0]

    claimed = claim(client, headers, "weekly-momentum", "claim-momentum")
    assert claimed.status_code == 200, claimed.text
    assert claimed.headers["Idempotent-Replay"] == "false"
    body = claimed.json()
    assert body["claim"]["xp"] == 150
    assert body["claim"]["xp_after"] - body["claim"]["xp_before"] == 150
    assert quests_by_id(body)["weekly-momentum"]["status"] == "claimed"

    replay = claim(client, headers, "weekly-momentum", "claim-momentum")
    assert replay.status_code == 200
    assert replay.headers["Idempotent-Replay"] == "true"
    assert replay.json()["claim"] == body["claim"]

    reused_key = claim(client, headers, "product-champion", "claim-momentum")
    assert reused_key.status_code == 409
    assert reused_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"

    again = claim(client, headers, "weekly-momentum", "claim-momentum-2")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "QUEST_ALREADY_CLAIMED"

    not_done = claim(client, headers, "consistency-streak", "claim-streak-early")
    assert not_done.status_code == 409
    assert not_done.json()["error"]["code"] == "QUEST_NOT_COMPLETE"

    for quest_id, reward in (("product-champion", 100), ("customer-coverage", 120)):
        response = claim(client, headers, quest_id, f"claim-{quest_id}")
        assert response.status_code == 200, response.text
        assert response.json()["claim"]["xp"] == reward

    progress = client.get("/api/v1/game/progress").json()
    assert progress["progress"]["xp"] == xp_before + 150 + 100 + 120
    states = quests_by_id(progress)
    assert states["weekly-momentum"]["status"] == "claimed"
    assert states["product-champion"]["status"] == "claimed"
    assert states["customer-coverage"]["status"] == "claimed"
    assert states["consistency-streak"]["status"] == "in_progress"

    with sqlite3.connect(settings.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM game_quest_claims").fetchone()[0] == 3
        # Quest rewards are game XP only: no organizational points are written.
        assert conn.execute("SELECT COUNT(*) FROM score_events").fetchone()[0] == org_before

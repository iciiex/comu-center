from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import VISITOR
from tests.test_kiloos_demo import (
    ADMIN,
    AMIR,
    ELHAM,
    MANAGEMENT,
    SUPERVISOR_1,
    import_and_process,
    login,
    user_id,
)

CUSTOMER_VISIT = {"customer_type": "new", "outcome": "order_received", "rating": 5}
PRODUCT_SPOTLIGHT = {"showcase": "new_product", "reaction": "loved_it", "rating": 4}


@pytest.fixture
def demo_settings(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("KILOOS_DEMO_PROFILE", "kiloos")
    return settings


@pytest.fixture
def demo(demo_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(demo_settings)) as c:
        yield c


def csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.get("/api/v1/auth/me").json()["csrf_token"]}


def mission_ids(client: TestClient) -> dict[str, dict]:
    body = client.get("/api/v1/game/bootstrap").json()
    return {m["id"]: m for m in body["missions"]}


def complete(client: TestClient, mission_id: str, answers: dict, key: str):
    token = client.get("/api/v1/game/bootstrap").json()["csrf_token"]
    return client.post(
        f"/api/v1/game/missions/{mission_id}/completions",
        json={"answers": answers},
        headers={"X-CSRF-Token": token, "Idempotency-Key": key},
    )


NEW_MISSION = {
    "title": "چالش ویزیت صبحگاهی",
    "description": "پیش از ظهر پنج مشتری را ویزیت کنید.",
    "category": "customer_visit",
    "kind": "daily",
    "xp_reward": 80,
}


def test_admin_creates_assigns_and_deactivates_missions(
    demo: TestClient, demo_settings: Settings
) -> None:
    import_and_process(demo, demo_settings)
    headers = csrf(demo)
    listing = demo.get("/api/v1/mgmt/missions").json()
    assert any(m["id"] == "market-scout" for m in listing["missions"])
    assert len(listing["visitors"]) == 8 and len(listing["branches"]) == 2

    amir_id = user_id(demo_settings, AMIR)
    created = demo.post(
        "/api/v1/mgmt/missions",
        json={**NEW_MISSION, "scope": "user", "scope_value": amir_id},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    custom_id = created.json()["id"]

    # Assigned to one visitor only.
    login(demo, demo_settings, AMIR)
    assert mission_ids(demo)[custom_id]["xpReward"] == 80
    login(demo, demo_settings, ELHAM)
    assert custom_id not in mission_ids(demo)

    # The visitor completes it through the normal server-authoritative path.
    login(demo, demo_settings, AMIR)
    done = complete(demo, custom_id, {"result": "done"}, "custom-1")
    assert done.status_code == 200, done.text
    entry = done.json()["entry"]
    assert entry["rewards"]["xp"] == 80
    assert entry["xpAfter"] - entry["xpBefore"] == 80

    # Deactivating removes it; a direct completion attempt is refused by the server.
    login(demo, demo_settings, ADMIN)
    off = demo.patch(
        f"/api/v1/mgmt/missions/{custom_id}", json={"status": "inactive"}, headers=csrf(demo)
    )
    assert off.status_code == 200
    login(demo, demo_settings, AMIR)
    assert custom_id not in mission_ids(demo)
    assert complete(demo, custom_id, {"result": "done"}, "custom-2").status_code in (404, 409)

    # A catalog mission can be switched off too, and then cannot be completed.
    login(demo, demo_settings, ADMIN)
    demo.patch(
        "/api/v1/mgmt/missions/customer-visit-challenge",
        json={"status": "inactive"},
        headers=csrf(demo),
    )
    login(demo, demo_settings, AMIR)
    assert "customer-visit-challenge" not in mission_ids(demo)
    blocked = complete(demo, "customer-visit-challenge", CUSTOMER_VISIT, "catalog-off")
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "MISSION_LOCKED"


def test_mission_admin_is_administrator_only_and_validates_input(
    demo: TestClient, demo_settings: Settings
) -> None:
    import_and_process(demo, demo_settings)
    bad = demo.post(
        "/api/v1/mgmt/missions", json={**NEW_MISSION, "xp_reward": 9999}, headers=csrf(demo)
    )
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "INVALID_XP"
    missing = demo.post(
        "/api/v1/mgmt/missions",
        json={**NEW_MISSION, "scope": "user", "scope_value": "nobody"},
        headers=csrf(demo),
    )
    assert missing.status_code == 404

    headers = login(demo, demo_settings, SUPERVISOR_1)
    assert demo.get("/api/v1/mgmt/missions").status_code == 403
    assert demo.post("/api/v1/mgmt/missions", json=NEW_MISSION, headers=headers).status_code == 403
    assert demo.post("/api/v1/demo/reset", headers=headers).status_code == 403
    login(demo, demo_settings, AMIR)
    assert demo.get("/api/v1/mgmt/missions").status_code == 403


def test_activity_feed_is_scoped_to_the_viewers_hierarchy(
    demo: TestClient, demo_settings: Settings
) -> None:
    import_and_process(demo, demo_settings)
    login(demo, demo_settings, AMIR)  # VIS-002 belongs to SUP-01
    assert complete(demo, "customer-visit-challenge", CUSTOMER_VISIT, "act-1").status_code == 200
    amir_id = user_id(demo_settings, AMIR)

    login(demo, demo_settings, MANAGEMENT)
    items = demo.get("/api/v1/mgmt/activity").json()["items"]
    kinds = {item["kind"] for item in items if item["user_id"] == amir_id}
    assert {"mission", "achievement"} <= kinds

    login(demo, demo_settings, SUPERVISOR_1)
    assert any(i["user_id"] == amir_id for i in demo.get("/api/v1/mgmt/activity").json()["items"])

    conn = sqlite3.connect(demo_settings.db_path)
    other = conn.execute(
        """SELECT u.mobile FROM users u JOIN employee_positions p ON p.user_id = u.id
           WHERE p.employee_code = 'SUP-02'"""
    ).fetchone()[0]
    conn.close()
    login(demo, demo_settings, other)
    assert all(i["user_id"] != amir_id for i in demo.get("/api/v1/mgmt/activity").json()["items"])


def test_team_challenge_progress_is_shared_by_the_team(
    demo: TestClient, demo_settings: Settings
) -> None:
    import_and_process(demo, demo_settings)
    login(demo, demo_settings, AMIR)
    assert complete(demo, "customer-visit-challenge", CUSTOMER_VISIT, "team-1").status_code == 200
    assert complete(demo, "product-spotlight", PRODUCT_SPOTLIGHT, "team-2").status_code == 200

    login(demo, demo_settings, VISITOR)  # VIS-001 is in the same team as VIS-002
    quests = {q["id"]: q for q in demo.get("/api/v1/game/bootstrap").json()["quests"]["quests"]}
    assert quests["team-challenge"]["progress"] == 2
    assert quests["team-challenge"]["status"] == "in_progress"


def test_demo_reset_rebuilds_the_scripted_scenario(
    demo: TestClient, demo_settings: Settings
) -> None:
    login(demo, demo_settings, ADMIN)
    reset = demo.post("/api/v1/demo/reset", headers=csrf(demo))
    assert reset.status_code == 200, reset.text
    assert reset.json()["visitors"]["VIS-001"] > 0

    # The administrator session survives the reset and sees the loaded sample data.
    response = demo.get("/api/v1/mgmt/overview")
    assert response.status_code == 200, response.text
    overview = response.json()
    assert overview["empty"] is False
    assert overview["command_center"]["players"] >= 4

    # Different levels and mission states across visitors, all server-computed.
    login(demo, demo_settings, VISITOR)  # VIS-001
    sara = demo.get("/api/v1/game/bootstrap").json()
    assert sara["progress"]["xp"] >= 400
    assert mission_ids(demo)["target-sprint"]["status"] == "completed"
    login(demo, demo_settings, ELHAM)  # VIS-005: one mission, sales gate not met
    assert demo.get("/api/v1/game/bootstrap").json()["progress"]["xp"] >= 100

    # Running it again gives the same starting point (repeatable presentation).
    login(demo, demo_settings, ADMIN)
    again = demo.post("/api/v1/demo/reset", headers=csrf(demo))
    assert again.status_code == 200
    assert again.json()["visitors"] == reset.json()["visitors"]

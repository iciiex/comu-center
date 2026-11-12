from __future__ import annotations

import json
from dataclasses import replace

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import OPERATOR, OTHER_VISITOR, VISITOR, login


def game_bootstrap(client: TestClient) -> dict:
    response = client.get("/api/v1/game/bootstrap")
    assert response.status_code == 200, response.text
    return response.json()


def csrf_header(client: TestClient, settings: Settings) -> dict[str, str]:
    token = game_bootstrap(client)["csrf_token"]
    return {"X-CSRF-Token": token}


def completion_payload() -> dict:
    return {
        "answers": {
            "customer_type": "new",
            "outcome": "order_received",
            "rating": 5,
            "note": "Call Friday",
        }
    }


def test_api_demo_login_lists_visitors_sets_cookie_and_logout_clears_it(
    client: TestClient,
) -> None:
    users = client.get("/api/v1/game/demo-users")
    assert users.status_code == 200
    assert users.json()["users"]
    assert all("mobile" not in user for user in users.json()["users"])

    visitor_id = users.json()["users"][0]["id"]
    logged_in = client.post("/api/v1/game/demo-login", json={"user_id": visitor_id})
    assert logged_in.status_code == 200
    assert logged_in.headers["set-cookie"].lower().find("httponly") >= 0
    assert logged_in.headers["x-csrf-token"]
    assert client.get("/api/v1/game/bootstrap").status_code == 200

    logout = client.post(
        "/api/v1/game/logout",
        headers={"X-CSRF-Token": client.get("/api/v1/game/bootstrap").json()["csrf_token"]},
    )
    assert logout.status_code == 200
    assert logout.json() == {"logged_out": True}
    assert client.get("/api/v1/game/bootstrap").status_code == 401


def test_game_demo_login_is_disabled_outside_dev_and_test(settings: Settings) -> None:
    production_settings = replace(settings, env="production")
    with TestClient(create_app(production_settings)) as production_client:
        assert production_client.get("/api/v1/game/demo-users").status_code == 404
        assert (
            production_client.post(
                "/api/v1/game/demo-login", json={"user_id": "not-a-user"}
            ).status_code
            == 404
        )


def test_game_bootstrap_is_authenticated_json_and_serves_pinned_catalog(
    client: TestClient, settings: Settings
) -> None:
    anonymous = client.get("/api/v1/game/bootstrap")
    assert anonymous.status_code == 401
    assert anonymous.headers["content-type"].startswith("application/json")
    assert anonymous.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    login(client, settings, VISITOR)
    response = client.get("/api/v1/game/bootstrap")
    data = response.json()
    assert response.status_code == 200
    assert data["api_version"] == "1"
    assert data["content_version"].startswith("sales-quest-arena-")
    assert len(data["missions"]) == 6
    assert len(data["achievements_catalog"]) == 10
    assert data["progress"]["xp"] == 0
    assert data["csrf_token"]
    assert data["date_key"]


def test_game_completion_is_server_scored_idempotent_and_separate_from_org_points(
    client: TestClient, settings: Settings, db
) -> None:
    login(client, settings, VISITOR)
    before_score_events = db.execute("SELECT COUNT(*) FROM score_events").fetchone()[0]
    bootstrap = game_bootstrap(client)
    headers = {"X-CSRF-Token": bootstrap["csrf_token"], "Idempotency-Key": "run-001"}
    first = client.post(
        "/api/v1/game/missions/customer-visit-challenge/completions",
        json=completion_payload(),
        headers=headers,
    )
    assert first.status_code == 200, first.text
    assert first.headers["Idempotent-Replay"] == "false"
    result = first.json()
    expected_xp = 130 + (50 if bootstrap["missions"][0]["isDaily"] else 0)
    assert result["entry"]["rewards"]["xp"] == expected_xp
    assert result["entry"]["rewards"]["coins"] == 20
    assert "order_received" in result["entry"]["flags"]
    assert "first_steps" in result["entry"]["achievementsUnlocked"]
    assert result["progress"]["xp"] == expected_xp
    assert result["progress"]["coins"] == 20

    replay = client.post(
        "/api/v1/game/missions/customer-visit-challenge/completions",
        json=completion_payload(),
        headers=headers,
    )
    assert replay.status_code == 200
    assert replay.headers["Idempotent-Replay"] == "true"
    assert replay.json() == result
    assert db.execute("SELECT COUNT(*) FROM game_completions").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM score_events").fetchone()[0] == before_score_events
    persisted = json.loads(db.execute("SELECT state_json FROM game_progress").fetchone()[0])
    assert persisted["xp"] == expected_xp


def test_daily_bonus_is_not_awarded_again_on_a_new_idempotency_key(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, VISITOR)
    headers = csrf_header(client, settings)
    path = "/api/v1/game/missions/customer-visit-challenge/completions"
    first = client.post(
        path,
        json=completion_payload(),
        headers={**headers, "Idempotency-Key": "daily-first"},
    )
    second = client.post(
        path,
        json=completion_payload(),
        headers={**headers, "Idempotency-Key": "daily-second"},
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["entry"]["wasDaily"] is True
    assert first.json()["entry"]["rewards"]["xp"] == 180
    assert second.json()["entry"]["wasDaily"] is False
    assert second.json()["entry"]["rewards"]["xp"] == 130
    assert second.json()["progress"]["xp"] == 310


def test_game_api_rejects_client_rewards_bad_answers_locks_and_bad_csrf(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, VISITOR)
    csrf = csrf_header(client, settings)
    path = "/api/v1/game/missions/customer-visit-challenge/completions"

    no_csrf = client.post(path, json=completion_payload(), headers={"Idempotency-Key": "x1"})
    assert no_csrf.status_code == 403
    assert no_csrf.headers["content-type"].startswith("application/json")

    forged = client.post(
        path,
        json={**completion_payload(), "xp": 999999},
        headers={**csrf, "Idempotency-Key": "x2"},
    )
    assert forged.status_code == 422

    invalid = client.post(
        path,
        json={"answers": {"customer_type": "admin", "outcome": "order_received", "rating": 5}},
        headers={**csrf, "Idempotency-Key": "x3"},
    )
    assert invalid.status_code == 422

    locked = client.post(
        "/api/v1/game/missions/product-spotlight/completions",
        json={"answers": {"showcase": "new_product", "reaction": "loved_it", "rating": 4}},
        headers={**csrf, "Idempotency-Key": "x4"},
    )
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "MISSION_LOCKED"


def test_game_profile_draft_history_and_user_scope(client: TestClient, settings: Settings) -> None:
    login(client, settings, VISITOR)
    headers = csrf_header(client, settings)
    profile = client.patch(
        "/api/v1/game/profile", json={"name": "Alex", "avatar": "panda"}, headers=headers
    )
    assert profile.status_code == 200
    assert profile.json()["progress"]["player"]["name"] == "Alex"
    assert profile.json()["progress"]["player"]["avatar"] == "panda"

    draft = client.put(
        "/api/v1/game/missions/customer-visit-challenge/draft",
        json={"step_index": 1, "answers": {"customer_type": "existing"}},
        headers=headers,
    )
    assert draft.status_code == 200
    assert draft.json()["progress"]["drafts"]["customer-visit-challenge"]["stepIndex"] == 1

    completion = client.post(
        "/api/v1/game/missions/customer-visit-challenge/completions",
        json=completion_payload(),
        headers={**headers, "Idempotency-Key": "history-001"},
    )
    assert completion.status_code == 200
    history = client.get("/api/v1/game/history?limit=1")
    assert history.status_code == 200
    assert history.json()["items"][0]["missionId"] == "customer-visit-challenge"

    deleted = client.delete("/api/v1/game/missions/customer-visit-challenge/draft", headers=headers)
    assert deleted.status_code == 200
    assert "customer-visit-challenge" not in deleted.json()["progress"]["drafts"]

    login(client, settings, OTHER_VISITOR)
    other_progress = client.get("/api/v1/game/progress").json()["progress"]
    assert other_progress["xp"] == 0
    assert other_progress["player"]["name"] == ""
    assert client.get("/api/v1/game/history").json()["items"] == []


def test_game_api_restricts_staff_and_rejects_url_session_token(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, OPERATOR)
    staff = client.get("/api/v1/game/bootstrap")
    assert staff.status_code == 403

    login(client, settings, VISITOR)
    bootstrap = game_bootstrap(client)
    bad_url = client.get("/api/v1/game/bootstrap?s=not-accepted")
    assert bad_url.status_code == 400
    assert bootstrap["player"]["id"]


def test_idempotency_key_cannot_be_reused_for_different_answers(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, VISITOR)
    headers = {**csrf_header(client, settings), "Idempotency-Key": "same-key"}
    path = "/api/v1/game/missions/customer-visit-challenge/completions"
    first = client.post(path, json=completion_payload(), headers=headers)
    assert first.status_code == 200
    different = completion_payload()
    different["answers"]["outcome"] = "successful_meeting"
    reused = client.post(path, json=different, headers=headers)
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_completion_unlocks_next_server_owned_mission(
    client: TestClient, settings: Settings
) -> None:
    login(client, settings, VISITOR)
    csrf = csrf_header(client, settings)
    first = client.post(
        "/api/v1/game/missions/customer-visit-challenge/completions",
        json=completion_payload(),
        headers={**csrf, "Idempotency-Key": "unlock-first"},
    )
    assert first.status_code == 200
    next_mission = next(
        mission for mission in first.json()["missions"] if mission["id"] == "product-spotlight"
    )
    assert next_mission["status"] == "available"

    second = client.post(
        "/api/v1/game/missions/product-spotlight/completions",
        json={
            "answers": {
                "showcase": "new_product",
                "reaction": "loved_it",
                "rating": 4,
            }
        },
        headers={**csrf, "Idempotency-Key": "unlock-second"},
    )
    assert second.status_code == 200
    assert second.json()["progress"]["missions"]["product-spotlight"]["completions"] == 1

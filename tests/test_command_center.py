from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.test_kiloos_demo import (
    AMIR,
    MANAGEMENT,
    SUPERVISOR_1,
    import_and_process,
    login,
    user_id,
)

CUSTOMER_VISIT = {"customer_type": "new", "outcome": "order_received", "rating": 5}


@pytest.fixture
def demo_settings(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("KILOOS_DEMO_PROFILE", "kiloos")
    return settings


@pytest.fixture
def demo(demo_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(demo_settings)) as c:
        yield c


def play_one_mission_as_amir(client: TestClient, settings: Settings) -> None:
    login(client, settings, AMIR)
    csrf = client.get("/api/v1/game/bootstrap").json()["csrf_token"]
    response = client.post(
        "/api/v1/game/missions/customer-visit-challenge/completions",
        json={"answers": CUSTOMER_VISIT},
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "command-center-visit"},
    )
    assert response.status_code == 200, response.text


def test_management_command_center_counts_engagement_across_visible_reps(
    demo: TestClient, demo_settings: Settings
) -> None:
    import_and_process(demo, demo_settings)
    play_one_mission_as_amir(demo, demo_settings)
    login(demo, demo_settings, MANAGEMENT)

    overview = demo.get("/api/v1/mgmt/overview").json()
    center = overview["command_center"]
    assert center["label"] == "DEMO"
    assert center["reps"] == len(overview["reps"]) == 8
    assert center["players"] == 1
    assert center["active_players"] == 1
    assert (
        center["mission_completion"]["possible"]
        == 8 * center["mission_completion"]["missions_per_rep"]
    )
    assert center["mission_completion"]["done"] == 1
    assert 0 < center["mission_completion"]["pct"] < 100
    assert sum(level["reps"] for level in center["xp_distribution"]) == center["reps"]

    amir_id = user_id(demo_settings, AMIR)
    first_steps = [a for a in center["recent_achievements"] if a["achievement"] == "First Steps"]
    assert any(a["user_id"] == amir_id for a in first_steps)


def test_supervisor_command_center_counts_only_their_own_team(
    demo: TestClient, demo_settings: Settings
) -> None:
    import_and_process(demo, demo_settings)
    play_one_mission_as_amir(demo, demo_settings)  # VIS-002 belongs to SUP-01's team (Tehran)
    login(demo, demo_settings, SUPERVISOR_1)

    overview = demo.get("/api/v1/mgmt/overview").json()
    visible = {rep["id"] for rep in overview["reps"]}
    center = overview["command_center"]
    assert center["reps"] == len(visible) == 3
    assert center["players"] == 1
    assert {a["user_id"] for a in center["recent_achievements"]} <= visible
    assert {c["user_id"] for c in center["recent_claims"]} <= visible

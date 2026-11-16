from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import ranking
from app.config import Settings
from app.main import create_app
from tests.test_kiloos_demo import AMIR, ELHAM, import_and_process, login, user_id

WEDNESDAY = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
CUSTOMER_VISIT = {"customer_type": "new", "outcome": "order_received", "rating": 5}


@pytest.fixture
def demo_settings(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("KILOOS_DEMO_PROFILE", "kiloos")
    return settings


@pytest.fixture
def demo(demo_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(demo_settings)) as c:
        yield c


def board(client: TestClient, **params) -> dict:
    response = client.get("/api/v1/leaderboard", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.get("/api/v1/game/bootstrap").json()["csrf_token"]}


def test_window_bounds_are_utc_calendar_windows_with_inclusive_ends() -> None:
    weekly = ranking.window_bounds("weekly", WEDNESDAY)  # Monday 16th to Sunday 22nd
    assert weekly["start"] == "2026-11-16T00:00:00+00:00"
    assert weekly["end"] == "2026-11-22T23:59:59+00:00"
    assert weekly["previous_start"] == "2026-11-09T00:00:00+00:00"
    assert weekly["previous_end"] == "2026-11-15T23:59:59+00:00"

    daily = ranking.window_bounds("daily", WEDNESDAY)
    assert daily["start"] == "2026-11-18T00:00:00+00:00"
    assert daily["end"] == "2026-11-18T23:59:59+00:00"
    assert daily["previous_end"] == "2026-11-17T23:59:59+00:00"

    monthly = ranking.window_bounds("monthly", WEDNESDAY)
    assert monthly["start"] == "2026-11-01T00:00:00+00:00"
    assert monthly["end"] == "2026-11-30T23:59:59+00:00"
    assert monthly["previous_start"] == "2026-10-01T00:00:00+00:00"

    year_end = ranking.window_bounds("monthly", datetime(2026, 12, 31, 23, 0, tzinfo=UTC))
    assert year_end["start"] == "2026-12-01T00:00:00+00:00"
    assert year_end["previous_start"] == "2026-11-01T00:00:00+00:00"

    with pytest.raises(ValueError):
        ranking.window_bounds("season", WEDNESDAY)


def test_leaderboard_default_keeps_the_season_shape_and_scopes_add_up(
    demo: TestClient, demo_settings: Settings
) -> None:
    import_and_process(demo, demo_settings)  # signs in as the administrator
    login(demo, demo_settings, AMIR)

    individual = board(demo)
    assert individual["scope"] == "individual" and individual["window"] == "season"
    assert individual["period"] is None
    assert individual["competition"] is not None
    rows = individual["rows"]
    assert [row["rank"] for row in rows] == list(range(1, len(rows) + 1))
    assert {"user_id", "org_points", "game_xp", "level", "is_me"} <= rows[0].keys()
    me = [row for row in rows if row["is_me"]]
    assert len(me) == 1 and me[0]["employee_code"] == "VIS-002"
    assert individual["me"]["user_id"] == me[0]["user_id"]

    by_branch = board(demo, scope="branch")
    branches = {row["branch_code"]: row for row in by_branch["rows"]}
    assert branches["BR-TEH"]["members"] == 5
    assert branches["BR-ISF"]["members"] == 3
    tehran_points = sum(r["org_points"] for r in rows if r["branch_code"] == "BR-TEH")
    assert branches["BR-TEH"]["org_points"] == tehran_points
    assert branches["BR-TEH"]["in_my_group"] is True
    assert branches["BR-ISF"]["in_my_group"] is False

    by_team = board(demo, scope="team")
    teams = by_team["rows"]
    assert sum(team["members"] for team in teams) == len(rows)
    assert sum(team["org_points"] for team in teams) == sum(r["org_points"] for r in rows)
    mine = [team for team in teams if team["in_my_group"]]
    assert len(mine) == 1 and mine[0]["members"] == 3  # SUP-01 leads Tehran reps 001, 002, 004

    narrowed = board(demo, branch="BR-ISF")
    assert {row["branch_code"] for row in narrowed["rows"]} == {"BR-ISF"}


def test_daily_and_weekly_windows_count_recorded_xp_and_mark_new_movement(
    demo: TestClient, demo_settings: Settings
) -> None:
    import_and_process(demo, demo_settings)  # signs in as the administrator
    login(demo, demo_settings, AMIR)
    headers = csrf(demo)
    response = demo.post(
        "/api/v1/game/missions/customer-visit-challenge/completions",
        json={"answers": CUSTOMER_VISIT},
        headers={**headers, "Idempotency-Key": "rank-window-visit"},
    )
    assert response.status_code == 200, response.text
    progress_xp = demo.get("/api/v1/game/progress").json()["progress"]["xp"]

    daily = board(demo, window="daily")
    weekly = board(demo, window="weekly", scope="individual")
    assert daily["window"] == "daily" and daily["period"]["start"] <= daily["period"]["end"]
    me_daily = next(row for row in daily["rows"] if row["is_me"])
    me_weekly = next(row for row in weekly["rows"] if row["is_me"])
    # Everything this player earned happened today, so the window XP equals the progress XP.
    assert me_daily["game_xp"] == progress_xp
    assert me_weekly["game_xp"] == progress_xp
    # Nothing was ranked in the previous window, so movement is "new", not an invented change.
    assert me_weekly["previous_rank"] is None
    assert me_weekly["movement"] == "new"
    assert weekly["period"]["previous_end"] < weekly["period"]["start"]
    assert [r["rank"] for r in weekly["rows"]] == list(range(1, len(weekly["rows"]) + 1))


def test_previous_window_activity_produces_a_real_downward_movement(
    demo: TestClient, demo_settings: Settings
) -> None:
    import_and_process(demo, demo_settings)
    # Give ELHAM 500 game XP last week (written directly, as history). Only ELHAM was ranked there.
    last_week = ranking.window_bounds("weekly", datetime.now(UTC))["previous_start"]
    conn = sqlite3.connect(demo_settings.db_path)
    try:
        conn.execute(
            """INSERT INTO game_completions
               (id, user_id, mission_id, idempotency_key, request_sha256,
                response_json, completed_at)
               VALUES (?, ?, 'customer-visit-challenge', ?, ?, ?, ?)""",
            (
                "history-elham-last-week",
                user_id(demo_settings, ELHAM),
                "history-elham-last-week",
                "0" * 64,
                json.dumps({"entry": {"rewards": {"xp": 500}}}),
                last_week,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    weekly = board(demo, window="weekly")
    elham = next(row for row in weekly["rows"] if row["employee_code"] == "VIS-005")
    assert elham["previous_rank"] == 1
    assert elham["movement"] == "down"
    assert elham["places"] == elham["rank"] - 1
    assert elham["places"] > 0


def test_leaderboard_rejects_unknown_scope_or_window(
    demo: TestClient, demo_settings: Settings
) -> None:
    login(demo, demo_settings, AMIR)
    assert demo.get("/api/v1/leaderboard", params={"scope": "company"}).status_code == 422
    assert demo.get("/api/v1/leaderboard", params={"window": "yearly"}).status_code == 422

"""Kiloos demo vertical slice: import -> dashboards -> sales-gated mission -> ranking.

Mirrors the 20-step demo acceptance scenario at API level. All data is SAMPLE.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app import kiloos_demo
from app.config import Settings
from app.main import create_app

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ADMIN = "09120000005"
MANAGEMENT = "09120000100"
BRANCH_MANAGER_ISF = "09120000102"
SUPERVISOR_1 = "09120000004"  # SUP-01 (Tehran, 3 reps)
AMIR = "09120000002"  # VIS-002, 92% -> eligible
MARYAM = "09120000003"  # VIS-003, 68% -> not eligible
ELHAM = "09120000106"  # VIS-005, 55% -> not eligible


@pytest.fixture
def demo_settings(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("KILOOS_DEMO_PROFILE", "kiloos")
    return settings


@pytest.fixture
def demo(demo_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(demo_settings)) as c:
        yield c


def user_id(settings: Settings, mobile: str) -> str:
    conn = sqlite3.connect(settings.db_path)
    try:
        return conn.execute("SELECT id FROM users WHERE mobile = ?", (mobile,)).fetchone()[0]
    finally:
        conn.close()


def login(client: TestClient, settings: Settings, mobile: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/demo-login", json={"user_id": user_id(settings, mobile)})
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def upload(client: TestClient, headers: dict, raw: bytes, name: str = "kiloos-sample-sales.xlsx"):
    return client.post(
        "/api/v1/mgmt/imports", files={"file": (name, raw, XLSX)}, headers=headers
    )


def db_rows(settings: Settings, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def import_and_process(client, settings) -> dict:
    admin = login(client, settings, ADMIN)
    staged = upload(client, admin, kiloos_demo.sample_workbook_bytes())
    assert staged.status_code == 201, staged.text
    done = client.post(f"/api/v1/mgmt/imports/{staged.json()['id']}/process", headers=admin)
    assert done.status_code == 200, done.text
    return done.json()


def test_seed_has_required_demo_accounts_and_hierarchy(demo, demo_settings) -> None:
    body = demo.get("/api/v1/auth/demo-users").json()
    assert body["is_demo"] is True
    positions = [u["position"] for u in body["users"]]
    assert positions.count("admin") == 1
    assert positions.count("management") == 1
    assert positions.count("branch_manager") == 2
    assert positions.count("supervisor") == 3
    assert positions.count("rep") >= 3
    rep = next(u for u in body["users"] if u["employee_code"] == "VIS-002")
    assert rep["branch_code"] == "BR-TEH" and rep["experience"] == "game"
    assert not any("mobile" in u for u in body["users"])  # no personal data exposed


def test_import_workflow_validates_dedupes_and_processes_once(demo, demo_settings) -> None:
    admin = login(demo, demo_settings, ADMIN)
    staged = upload(demo, admin, kiloos_demo.sample_workbook_bytes())
    assert staged.status_code == 201
    preview = staged.json()
    assert preview["status"] == "validated" and preview["is_sample"] is True
    assert preview["counts"] == {
        "total": 155, "valid": 144, "pending": 144, "processed": 0, "rejected": 8, "duplicates": 3,
    }
    codes = {r["error_code"] for r in preview["problem_rows"]}
    assert {"E_USER_MAPPING", "E_DATE", "E_FUTURE_DATE", "E_QUANTITY", "E_SKU", "E_BRAND",
            "E_EXTERNAL_ID", "E_DUPLICATE_IN_FILE"} <= codes
    assert preview["targets"] == {"rows": 18, "valid": 16, "invalid": 2}
    assert {b["brand"] for b in preview["brands"]} == {"EFES", "MATADOR"}
    # Preview never scores or changes the dashboards.
    assert demo.get("/api/v1/mgmt/overview").json()["empty"] is True
    assert db_rows(demo_settings, "SELECT COUNT(*) n FROM score_events WHERE source_type='sales_record'")[0]["n"] == 0

    # Same file again is refused: no duplicate import.
    again = upload(demo, admin, kiloos_demo.sample_workbook_bytes())
    assert again.status_code == 409 and again.json()["error"]["code"] == "DUPLICATE_FILE"

    done = demo.post(f"/api/v1/mgmt/imports/{preview['id']}/process", headers=admin).json()
    assert done["result"]["created"] > 0 and done["result"]["targets_applied"] == 16
    assert done["import"]["status"] == "completed"
    assert done["import"]["reconciliation"] == {
        "rows_ok": True, "points_ok": True,
        "scored_points": done["import"]["reconciliation"]["scored_points"],
        "points_sum": done["import"]["reconciliation"]["scored_points"],
    }
    events = db_rows(demo_settings, "SELECT COUNT(*) n FROM score_events WHERE source_type='sales_record'")[0]["n"]

    # Re-processing is idempotent.
    repeat = demo.post(f"/api/v1/mgmt/imports/{preview['id']}/process", headers=admin).json()
    assert repeat["result"]["created"] == 0
    assert db_rows(demo_settings, "SELECT COUNT(*) n FROM score_events WHERE source_type='sales_record'")[0]["n"] == events

    # A different file that re-sends processed rows: only the new rows count.
    overlap = upload(demo, admin, kiloos_demo.overlap_workbook_bytes(), "overlap.xlsx").json()
    assert overlap["counts"]["duplicates"] == 10 and overlap["counts"]["pending"] == 5
    demo.post(f"/api/v1/mgmt/imports/{overlap['id']}/process", headers=admin)
    n = db_rows(demo_settings, "SELECT COUNT(*) n FROM sales_records WHERE status='scored'")[0]["n"]
    assert n == 144 + 5


def test_management_dashboard_totals_and_hierarchy_scope(demo, demo_settings) -> None:
    import_and_process(demo, demo_settings)
    admin_view = demo.get("/api/v1/mgmt/overview").json()
    assert admin_view["period"] == "2026-11" and admin_view["is_demo"] is True
    brands = {b["brand"]: b for b in admin_view["brands"]}
    assert set(brands) == {"EFES", "MATADOR"}
    assert sum(b["amount"] for b in brands.values()) == admin_view["totals"]["amount"]
    assert admin_view["totals"]["reps"] == 8
    assert admin_view["data_origin"]["sample"] == 144 and admin_view["data_origin"]["imported"] == 0
    assert {b["code"] for b in admin_view["branches"]} == {"BR-TEH", "BR-ISF"}
    amir = next(r for r in admin_view["reps"] if r["employee_code"] == "VIS-002")
    assert 91.5 <= amir["attainment_pct"] <= 92.5  # 92% of target by construction
    # Brand filter narrows the same data.
    efes = demo.get("/api/v1/mgmt/overview?brand=EFES").json()
    assert [b["brand"] for b in efes["brands"]] == ["EFES"]
    assert efes["totals"]["amount"] == brands["EFES"]["amount"]

    # Supervisor sees only their own three reps; branch manager only their branch.
    login(demo, demo_settings, SUPERVISOR_1)
    sup = demo.get("/api/v1/mgmt/overview").json()
    assert {r["employee_code"] for r in sup["reps"]} == {"VIS-001", "VIS-002", "VIS-004"}
    maryam = user_id(demo_settings, MARYAM)
    assert demo.get(f"/api/v1/mgmt/reps/{maryam}").status_code == 404
    login(demo, demo_settings, BRANCH_MANAGER_ISF)
    bm = demo.get("/api/v1/mgmt/overview").json()
    assert {r["branch_code"] for r in bm["reps"]} == {"BR-ISF"}
    assert demo.get("/api/v1/mgmt/branches/BR-TEH").status_code == 404
    detail = demo.get("/api/v1/mgmt/branches/BR-ISF").json()
    assert detail["branch"]["manager"] and len(detail["supervisors"]) == 1
    assert len(detail["supervisors"][0]["reps"]) == 3
    # Management sees everything; reps and anonymous users are refused.
    login(demo, demo_settings, MANAGEMENT)
    assert demo.get("/api/v1/mgmt/overview").json()["totals"]["reps"] == 8
    login(demo, demo_settings, AMIR)
    assert demo.get("/api/v1/mgmt/overview").status_code == 403
    demo.cookies.clear()
    assert demo.get("/api/v1/mgmt/overview").status_code == 401


def test_only_admin_can_import(demo, demo_settings) -> None:
    headers = login(demo, demo_settings, SUPERVISOR_1)
    response = upload(demo, headers, kiloos_demo.sample_workbook_bytes())
    assert response.status_code == 403
    assert db_rows(demo_settings, "SELECT COUNT(*) n FROM sales_imports")[0]["n"] == 0


def game_missions(client: TestClient) -> dict:
    body = client.get("/api/v1/game/bootstrap").json()
    return {m["id"]: m for m in body["missions"]}


def test_sales_mission_is_gated_by_processed_sales_and_awards_once(demo, demo_settings) -> None:
    # Before any import there is nothing to be eligible for.
    login(demo, demo_settings, AMIR)
    assert game_missions(demo)["target-sprint"]["status"] == "locked"
    import_and_process(demo, demo_settings)

    login(demo, demo_settings, ELHAM)  # 55% of target
    locked = game_missions(demo)["target-sprint"]
    assert locked["status"] == "locked" and "80%" in locked["lockReason"]
    answers = {"driver": "efes_push", "confidence": 4}
    denied = demo.post(
        "/api/v1/game/missions/target-sprint/completions",
        json={"answers": answers},
        headers={**{"X-CSRF-Token": demo.get("/api/v1/game/bootstrap").json()["csrf_token"]},
                 "Idempotency-Key": "elham-1"},
    )
    assert denied.status_code == 409 and denied.json()["error"]["code"] == "MISSION_LOCKED"

    headers = login(demo, demo_settings, AMIR)  # 92% of target
    amir = user_id(demo_settings, AMIR)
    mission = game_missions(demo)["target-sprint"]
    assert mission["status"] == "available"
    assert mission["salesGateInfo"]["eligible"] is True
    board_before = {r["user_id"]: r for r in demo.get("/api/v1/leaderboard").json()["rows"]}
    events_before = db_rows(demo_settings, "SELECT COUNT(*) n FROM score_events WHERE user_id=?", (amir,))[0]["n"]

    # The client cannot smuggle rewards: only "answers" is accepted.
    cheat = demo.post(
        "/api/v1/game/missions/target-sprint/completions",
        json={"answers": answers, "orgPoints": 9999},
        headers={**headers, "Idempotency-Key": "cheat"},
    )
    assert cheat.status_code == 422

    key = {"Idempotency-Key": "amir-sprint-1"}
    done = demo.post(
        "/api/v1/game/missions/target-sprint/completions", json={"answers": answers},
        headers={**headers, **key},
    )
    assert done.status_code == 200, done.text
    entry = done.json()["entry"]
    assert entry["rewards"]["xp"] == 120 and entry["xpAfter"] == 120
    assert entry["orgPoints"]["points"] == 100
    assert entry["orgPoints"]["approvalStatus"] == "PROPOSED" and entry["orgPoints"]["isDemo"]
    assert done.headers["idempotent-replay"] == "false"

    # Replay with the same key: same answer, nothing awarded twice.
    replay = demo.post(
        "/api/v1/game/missions/target-sprint/completions", json={"answers": answers},
        headers={**headers, **key},
    )
    assert replay.json()["entry"]["id"] == entry["id"]
    assert replay.headers["idempotent-replay"] == "true"
    # A fresh key in the same period is refused: once per period.
    second = demo.post(
        "/api/v1/game/missions/target-sprint/completions", json={"answers": answers},
        headers={**headers, "Idempotency-Key": "amir-sprint-2"},
    )
    assert second.status_code == 409
    mission_after = game_missions(demo)["target-sprint"]
    assert mission_after["status"] == "completed"

    # Ledger: exactly one new organizational event, with an explain payload; XP never hits it.
    events_after = db_rows(demo_settings, "SELECT COUNT(*) n FROM score_events WHERE user_id=?", (amir,))[0]["n"]
    assert events_after == events_before + 1
    ev = db_rows(
        demo_settings,
        "SELECT * FROM score_events WHERE user_id=? AND source_type='game_sales_mission'", (amir,),
    )
    assert len(ev) == 1 and ev[0]["rule_code"] == "GAME_SALES_TARGET_80_PROPOSED"
    assert '"approval_status": "PROPOSED"' in ev[0]["explain_json"]
    wallet = db_rows(demo_settings, "SELECT balance FROM point_wallets WHERE user_id=?", (amir,))[0]
    assert wallet["balance"] == sum(
        r["points"] for r in db_rows(demo_settings, "SELECT points FROM score_events WHERE user_id=?", (amir,))
    )

    # Leaderboard and management view reflect the same underlying data.
    board_after = {r["user_id"]: r for r in demo.get("/api/v1/leaderboard").json()["rows"]}
    assert board_after[amir]["org_points"] == board_before[amir]["org_points"] + 100
    assert board_after[amir]["game_xp"] == 120
    assert board_after[amir]["rank"] <= board_before[amir]["rank"]
    me = demo.get("/api/v1/me/performance").json()
    assert me["org_points"]["by_source"]["game_sales_mission"] == 100
    assert me["mission_gate"]["eligible"] is True

    login(demo, demo_settings, MANAGEMENT)
    rep = demo.get(f"/api/v1/mgmt/reps/{amir}").json()
    assert rep["rep"]["game"]["xp"] == 120 and rep["rep"]["game"]["missions_completed"] == 1
    assert rep["rep"]["org_points"] == board_after[amir]["org_points"]
    assert rep["rank"]["position"] == board_after[amir]["rank"]


def test_reset_and_load_sample_cli_are_deterministic(demo_settings, monkeypatch) -> None:
    kiloos_demo.reset(demo_settings)
    result = kiloos_demo.load_sample(demo_settings)
    assert result["created"] > 0
    first = db_rows(demo_settings, "SELECT user_external_id, SUM(amount) a FROM sales_records WHERE status='scored' GROUP BY user_external_id ORDER BY user_external_id")
    kiloos_demo.reset(demo_settings)
    kiloos_demo.load_sample(demo_settings)
    second = db_rows(demo_settings, "SELECT user_external_id, SUM(amount) a FROM sales_records WHERE status='scored' GROUP BY user_external_id ORDER BY user_external_id")
    assert [r["a"] for r in first] == [r["a"] for r in second]
    assert len(first) == 8

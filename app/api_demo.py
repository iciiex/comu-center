"""JSON API for the unified Kiloos demo (single origin, ``/api/v1/*``).

* ``/auth/*``        demo login for every account type (management + sales reps), CSRF header.
* ``/mgmt/*``        management dashboards, hierarchy-scoped; Excel import for admins.
* ``/me/performance``, ``/leaderboard``   employee dashboard and ranking.

All numbers come from processed sales (``perf``) and the append-only score ledger. Scope is
enforced here on the server from ``employee_positions``; the UI never filters data on its own.
Everything is DEMO: sample data is flagged ``data_origin`` and rules are PROPOSED.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from app import game, imports, kiloos_demo, perf, ranking, repo
from app.repo import DomainError
from app.security import (
    CurrentUser,
    clear_session,
    csrf_for,
    csrf_token,
    make_token,
    set_session,
)

DEMO_NOTICE = (
    "DEMO — sample data and PROPOSED rules. Not real Kiloos sales, not approved KPIs, "
    "and no financial reward is paid."
)
MGMT_POSITIONS = {"admin", "management", "branch_manager", "supervisor"}
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ----------------------------------------------------------------------------- identity
def member_profile(conn: sqlite3.Connection, user: CurrentUser) -> dict[str, Any]:
    row = conn.execute(
        """SELECT p.employee_code, p.position, p.title, p.branch_code, p.data_origin,
                  b.name AS branch_name
           FROM employee_positions p
           LEFT JOIN branches b ON b.organization_id = p.organization_id AND b.code = p.branch_code
           WHERE p.user_id = ?""",
        (user.id,),
    ).fetchone()
    if row:
        position, title = row["position"], row["title"]
    elif user.role == "admin":
        position, title = "admin", "System Administrator"
    elif user.role == "visitor":
        position, title = "rep", "Sales Representative"
    else:
        position, title = "staff", "Staff"
    return {
        "id": user.id,
        "name": user.full_name,
        "role": user.role,
        "position": position,
        "title": title,
        "employee_code": row["employee_code"] if row else None,
        "branch_code": row["branch_code"] if row else None,
        "branch_name": row["branch_name"] if row else None,
        "data_origin": row["data_origin"] if row else "sample",
        "experience": "game" if user.role == "visitor" else "management",
    }


def visible_rep_ids(conn: sqlite3.Connection, user: CurrentUser, profile: dict) -> set[str]:
    """Server-side visibility: the management hierarchy decides who a user may see."""
    position = profile["position"]
    base = """SELECT p.user_id FROM employee_positions p JOIN users u ON u.id = p.user_id
              WHERE p.organization_id = ? AND p.position = 'rep' AND u.is_active = 1"""
    if position in {"admin", "management"}:
        rows = conn.execute(base, (user.organization_id,)).fetchall()
    elif position == "branch_manager":
        rows = conn.execute(
            base + " AND p.branch_code = ?", (user.organization_id, profile["branch_code"])
        ).fetchall()
    elif position == "supervisor":
        rows = conn.execute(
            base + " AND p.supervisor_id = ?", (user.organization_id, user.id)
        ).fetchall()
    elif position == "rep":
        return {user.id}
    else:
        return set()
    return {r["user_id"] for r in rows}


# ---------------------------------------------------------------------------- read models
def _names(conn: sqlite3.Connection, org_id: str) -> dict[str, str]:
    rows = conn.execute("SELECT id, full_name FROM users WHERE organization_id = ?", (org_id,))
    return {r["id"]: r["full_name"] for r in rows}


def game_status(conn: sqlite3.Connection, user_ids: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not user_ids:
        return out
    levels = {lv["level"]: lv["title"] for lv in game.catalog()["game_config"]["levels"]}
    rows = conn.execute(
        f"SELECT user_id, state_json FROM game_progress WHERE user_id IN ({','.join('?' * len(user_ids))})",  # noqa: S608
        user_ids,
    ).fetchall()
    for row in rows:
        state = json.loads(row["state_json"])
        xp = int(state.get("xp", 0))
        level = game._level(xp)
        out[row["user_id"]] = {
            "started": True,
            "xp": xp,
            "coins": int(state.get("coins", 0)),
            "level": level,
            "level_title": levels.get(level, ""),
            "streak": int(state.get("streak", {}).get("count", 0)),
            "missions_completed": sum(
                1 for rec in state.get("missions", {}).values() if rec.get("completions", 0) > 0
            ),
            "achievements": len(state.get("achievements", {})),
        }
    for uid in user_ids:
        out.setdefault(
            uid,
            {"started": False, "xp": 0, "coins": 0, "level": 1, "level_title": "Rookie",
             "streak": 0, "missions_completed": 0, "achievements": 0},
        )
    return out


def _rep_rows(conn: sqlite3.Connection, org_id: str, ids: set[str]) -> list[sqlite3.Row]:
    rows = conn.execute(
        """SELECT p.user_id, p.employee_code, p.branch_code, p.supervisor_id,
                  p.branch_manager_id, p.data_origin, u.full_name, b.name AS branch_name
           FROM employee_positions p
           JOIN users u ON u.id = p.user_id
           LEFT JOIN branches b ON b.organization_id = p.organization_id AND b.code = p.branch_code
           WHERE p.organization_id = ? AND p.position = 'rep' AND u.is_active = 1
           ORDER BY p.branch_code, p.employee_code""",
        (org_id,),
    ).fetchall()
    return [r for r in rows if r["user_id"] in ids]


def _entry(r: sqlite3.Row, sales, targets, points, games, names) -> dict[str, Any]:
    summary = perf.rep_summary(sales, targets, r["user_id"])
    return {
        "id": r["user_id"],
        "name": r["full_name"],
        "employee_code": r["employee_code"],
        "branch_code": r["branch_code"],
        "branch_name": r["branch_name"],
        "supervisor": names.get(r["supervisor_id"]),
        "supervisor_id": r["supervisor_id"],
        "amount": summary["amount"],
        "target": summary["target"],
        "attainment_pct": summary["attainment_pct"],
        "brands": summary["brands"],
        "org_points": points.get(r["user_id"], 0),
        "game": games[r["user_id"]],
        "_amount": summary["_amount"],
        "_target": summary["_target"],
    }


def _strip(entry: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in entry.items() if not k.startswith("_")}


def _rollup(entries: list[dict[str, Any]]) -> dict[str, Any]:
    amount = sum((e["_amount"] for e in entries), perf.dec(0))
    target = sum((e["_target"] for e in entries), perf.dec(0))
    return {
        "amount": perf.money(amount),
        "target": perf.money(target),
        "attainment_pct": perf.pct(amount, target),
        "reps": len(entries),
        "org_points": sum(e["org_points"] for e in entries),
        "game_xp": sum(e["game"]["xp"] for e in entries),
    }


def _brand_rollup(conn, org_id, period, ids: list[str], brand: str | None) -> list[dict]:
    sales = perf.sales_by_user_brand(conn, org_id, period, ids, brand)
    targets = perf.targets_by_user_brand(conn, org_id, period, ids, brand)
    agg: dict[str, dict[str, Any]] = {}
    for per_brand in sales.values():
        for code, s in per_brand.items():
            a = agg.setdefault(code, {"amount": perf.dec(0), "qty": perf.dec(0), "t": perf.dec(0),
                                      "records": 0})
            a["amount"] += s["amount"]
            a["qty"] += s["quantity"]
            a["records"] += int(s["records"])
    for per_brand in targets.values():
        for code, t in per_brand.items():
            agg.setdefault(code, {"amount": perf.dec(0), "qty": perf.dec(0), "t": perf.dec(0),
                                  "records": 0})["t"] += t
    names = {r["code"]: r["name"] for r in conn.execute(
        "SELECT code, name FROM brands WHERE organization_id = ?", (org_id,))}
    return [
        {
            "brand": code,
            "name": names.get(code, code),
            "amount": perf.money(a["amount"]),
            "quantity": perf.money(a["qty"]),
            "records": a["records"],
            "target": perf.money(a["t"]),
            "attainment_pct": perf.pct(a["amount"], a["t"]),
        }
        for code, a in sorted(agg.items())
    ]


def _origins(conn, org_id: str, period: str, ids: list[str]) -> dict[str, int]:
    out = {"sample": 0, "imported": 0}
    if not ids:
        return out
    rows = conn.execute(
        f"""SELECT data_origin, COUNT(*) AS n FROM sales_records
            WHERE organization_id = ? AND status = 'scored' AND substr(sale_date, 1, 7) = ?
              AND user_id IN ({','.join('?' * len(ids))}) GROUP BY data_origin""",  # noqa: S608
        [org_id, period, *ids],
    ).fetchall()
    for row in rows:
        out[row["data_origin"]] = row["n"]
    return out


def leaderboard_rows(conn: sqlite3.Connection, org_id: str, viewer_id: str,
                     branch: str | None = None) -> dict[str, Any]:
    competition = repo.active_competition(conn, org_id)
    start = competition["starts_at"] if competition else "0000-01-01T00:00:00+00:00"
    end = competition["ends_at"] if competition else "9999-12-31T23:59:59+00:00"
    rows = conn.execute(
        """SELECT u.id, u.full_name, p.employee_code, p.branch_code,
                  COALESCE(SUM(se.points), 0) AS total, MIN(se.occurred_at) AS first_at
           FROM users u
           LEFT JOIN employee_positions p ON p.user_id = u.id
           LEFT JOIN score_events se
                  ON se.user_id = u.id AND se.occurred_at >= ? AND se.occurred_at <= ?
           WHERE u.organization_id = ? AND u.role = 'visitor' AND u.is_active = 1
           GROUP BY u.id""",
        (start, end, org_id),
    ).fetchall()
    ordered = sorted(rows, key=lambda r: (-int(r["total"]), r["first_at"] or "9999", r["full_name"]))
    games = game_status(conn, [r["id"] for r in ordered])
    board = []
    for rank, r in enumerate(ordered, start=1):
        if branch and r["branch_code"] != branch:
            continue
        board.append(
            {
                "rank": rank,
                "user_id": r["id"],
                "name": r["full_name"],
                "employee_code": r["employee_code"],
                "branch_code": r["branch_code"],
                "org_points": int(r["total"]),
                "game_xp": games[r["id"]]["xp"],
                "level": games[r["id"]]["level"],
                "is_me": r["id"] == viewer_id,
            }
        )
    return {
        "is_demo": True,
        "competition": (
            {"title": competition["title"], "starts_at": competition["starts_at"],
             "ends_at": competition["ends_at"], "is_sample": bool(competition["is_sample"])}
            if competition else None
        ),
        "rows": board,
        "note": "Ranked by organizational points (append-only ledger). Game XP is separate.",
    }


def rep_detail(conn: sqlite3.Connection, org_id: str, user_id: str, period: str | None) -> dict:
    ids = {user_id}
    rows = _rep_rows(conn, org_id, ids)
    if not rows:
        raise HTTPException(status_code=404, detail="Sales representative not found.")
    names = _names(conn, org_id)
    period = period or perf.latest_period(conn, org_id)
    r = rows[0]
    points = perf.org_points(conn, org_id, [user_id])
    games = game_status(conn, [user_id])
    sales = perf.sales_by_user_brand(conn, org_id, period, [user_id]) if period else {}
    targets = perf.targets_by_user_brand(conn, org_id, period, [user_id]) if period else {}
    entry = _entry(r, sales, targets, points, games, names)
    daily = []
    if period:
        for row in conn.execute(
            """SELECT sale_date, COALESCE(brand_code, 'UNASSIGNED') AS brand, SUM(amount) AS amount
               FROM sales_records WHERE organization_id = ? AND user_id = ? AND status = 'scored'
                 AND substr(sale_date, 1, 7) = ? GROUP BY sale_date, brand ORDER BY sale_date""",
            (org_id, user_id, period),
        ):
            if not daily or daily[-1]["date"] != row["sale_date"]:
                daily.append({"date": row["sale_date"], "amount": 0, "by_brand": {}})
            daily[-1]["amount"] += int(perf.dec(row["amount"]))
            daily[-1]["by_brand"][row["brand"]] = int(perf.dec(row["amount"]))
    competition = repo.active_competition(conn, org_id)
    start = competition["starts_at"] if competition else "0000-01-01T00:00:00+00:00"
    end = competition["ends_at"] if competition else "9999-12-31T23:59:59+00:00"
    by_source = {
        row["source_type"]: int(row["total"])
        for row in conn.execute(
            """SELECT source_type, SUM(points) AS total FROM score_events
               WHERE user_id = ? AND occurred_at >= ? AND occurred_at <= ?
               GROUP BY source_type""",
            (user_id, start, end),
        )
    }
    events = [
        {
            "id": e["id"],
            "source_type": e["source_type"],
            "rule_code": e["rule_code"],
            "points": int(e["points"]),
            "occurred_at": e["occurred_at"],
            "status": "PROPOSED" if e["rule_code"].endswith("_PROPOSED")
            else ("SAMPLE" if e["is_sample"] else "APPROVED"),
        }
        for e in conn.execute(
            """SELECT se.id, se.source_type, se.rule_code, se.points, se.occurred_at, rv.is_sample
               FROM score_events se JOIN scoring_rule_versions rv ON rv.id = se.rule_version_id
               WHERE se.user_id = ? AND se.corrects_event_id IS NULL
               ORDER BY se.occurred_at DESC, se.id DESC LIMIT 8""",
            (user_id,),
        )
    ]
    board = leaderboard_rows(conn, org_id, user_id)["rows"]
    mine = next((b for b in board if b["user_id"] == user_id), None)
    gate = perf.sales_gate(conn, org_id, user_id)
    return {
        "is_demo": True,
        "period": period,
        "rep": _strip(entry),
        "daily": daily,
        "org_points": {"total": entry["org_points"], "by_source": by_source, "recent": events},
        "rank": {"position": mine["rank"] if mine else None, "of": len(board)},
        "mission_gate": gate,
        "data_origin": _origins(conn, org_id, period, [user_id]) if period else {},
    }


# ------------------------------------------------------------------------------ routes
def register(app, *, settings, conn_dep, require_user, require_admin, csrf_guard,
             login_rate_limited) -> None:
    def err(status: int, code: str, message: str, **extra: Any) -> JSONResponse:
        return JSONResponse({"error": {"code": code, "message": message, **extra}}, status_code=status)

    def demo_only() -> None:
        if settings.env not in {"dev", "test"}:
            raise HTTPException(status_code=404, detail="Demo login is disabled in this environment.")

    def mgmt_context(user: CurrentUser, conn):
        profile = member_profile(conn, user)
        if profile["position"] not in MGMT_POSITIONS:
            raise HTTPException(status_code=403, detail="Management access is required.")
        return profile, visible_rep_ids(conn, user, profile)

    # ---- auth
    @app.get("/api/v1/auth/demo-users")
    def demo_users(conn: sqlite3.Connection = Depends(conn_dep)) -> JSONResponse:
        demo_only()
        rows = conn.execute(
            """SELECT u.id, u.full_name, u.role, p.employee_code, p.position, p.title,
                      p.branch_code, b.name AS branch_name
               FROM users u
               LEFT JOIN employee_positions p ON p.user_id = u.id
               LEFT JOIN branches b ON b.organization_id = u.organization_id AND b.code = p.branch_code
               WHERE u.is_active = 1"""
        ).fetchall()
        order = {"admin": 0, "management": 1, "branch_manager": 2, "supervisor": 3, "rep": 4}

        def position(row) -> str:
            if row["position"]:
                return row["position"]
            return {"admin": "admin", "visitor": "rep"}.get(row["role"], "staff")

        users = sorted(
            (
                {
                    "id": r["id"],
                    "name": r["full_name"],
                    "role": r["role"],
                    "position": position(r),
                    "title": r["title"] or {"admin": "System Administrator"}.get(r["role"], "Staff"),
                    "employee_code": r["employee_code"],
                    "branch_code": r["branch_code"],
                    "branch_name": r["branch_name"],
                    "experience": "game" if r["role"] == "visitor" else "management",
                }
                for r in rows
            ),
            key=lambda u: (order.get(u["position"], 9), u["branch_code"] or "", u["employee_code"] or "", u["name"]),
        )
        return JSONResponse({"is_demo": True, "notice": DEMO_NOTICE, "users": users})

    @app.post("/api/v1/auth/demo-login")
    async def demo_login(request: Request, conn: sqlite3.Connection = Depends(conn_dep)):
        demo_only()
        client_ip = request.client.host if request.client else "unknown"
        if login_rate_limited(client_ip):
            raise game.GameError(429, "RATE_LIMITED", "Too many demo login attempts; try again later.")
        try:
            payload = await request.json()
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(status_code=400, detail="Expected a JSON request body.") from None
        if not isinstance(payload, dict) or set(payload) != {"user_id"} or not isinstance(
            payload["user_id"], str
        ):
            raise HTTPException(status_code=422, detail="Request must contain user_id only.")
        row = conn.execute(
            "SELECT id, organization_id, full_name, role, is_active FROM users "
            "WHERE id = ? AND is_active = 1",
            (payload["user_id"],),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Demo user not found.")
        user = CurrentUser(row["id"], row["organization_id"], row["full_name"], row["role"], True)
        token = make_token(user.id, settings.secret)
        csrf = csrf_for(token, settings.secret)
        body = {"user": member_profile(conn, user), "csrf_token": csrf, "notice": DEMO_NOTICE}
        out = JSONResponse(body)
        set_session(out, user.id, settings.secret, token)
        out.headers["Cache-Control"] = "no-store"
        out.headers["X-CSRF-Token"] = csrf
        return out

    @app.get("/api/v1/auth/me")
    def me(request: Request, user: CurrentUser = Depends(require_user),
           conn: sqlite3.Connection = Depends(conn_dep)) -> JSONResponse:
        out = JSONResponse(
            {"user": member_profile(conn, user), "csrf_token": csrf_token(request),
             "notice": DEMO_NOTICE}
        )
        out.headers["Cache-Control"] = "no-store"
        return out

    @app.post("/api/v1/auth/logout", dependencies=[Depends(csrf_guard)])
    def logout(user: CurrentUser = Depends(require_user)) -> JSONResponse:
        out = JSONResponse({"logged_out": True})
        clear_session(out)
        out.headers["Cache-Control"] = "no-store"
        return out

    # ---- dashboards
    @app.get("/api/v1/mgmt/overview")
    def overview(
        period: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
        brand: str | None = Query(None, max_length=40),
        branch: str | None = Query(None, max_length=40),
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ) -> JSONResponse:
        profile, visible = mgmt_context(user, conn)
        org_id = user.organization_id
        all_periods = perf.periods(conn, org_id)
        period = period or (all_periods[0] if all_periods else None)
        last = conn.execute(
            """SELECT id, file_name, status, data_origin, created_at FROM sales_imports
               WHERE organization_id = ? ORDER BY created_at DESC LIMIT 1""",
            (org_id,),
        ).fetchone()
        base = {
            "is_demo": True,
            "notice": DEMO_NOTICE,
            "viewer": profile,
            "periods": all_periods,
            "period": period,
            "filters": {"brand": brand, "branch": branch},
            "last_import": dict(last) if last else None,
        }
        if period is None:
            return JSONResponse({**base, "empty": True, "brands": [], "branches": [], "reps": []})
        rows = [r for r in _rep_rows(conn, org_id, visible) if not branch or r["branch_code"] == branch]
        ids = [r["user_id"] for r in rows]
        sales = perf.sales_by_user_brand(conn, org_id, period, ids, brand)
        targets = perf.targets_by_user_brand(conn, org_id, period, ids, brand)
        points = perf.org_points(conn, org_id, ids)
        games = game_status(conn, ids)
        names = _names(conn, org_id)
        entries = [_entry(r, sales, targets, points, games, names) for r in rows]
        by_branch: dict[str, list[dict]] = {}
        for e in entries:
            by_branch.setdefault(e["branch_code"] or "—", []).append(e)
        branch_names = {r["code"]: r["name"] for r in conn.execute(
            "SELECT code, name FROM branches WHERE organization_id = ?", (org_id,))}
        managers = {
            r["branch_code"]: r["full_name"]
            for r in conn.execute(
                """SELECT p.branch_code, u.full_name FROM employee_positions p
                   JOIN users u ON u.id = p.user_id
                   WHERE p.organization_id = ? AND p.position = 'branch_manager'""",
                (org_id,),
            )
        }
        branches = [
            {"code": code, "name": branch_names.get(code, code), "manager": managers.get(code),
             **_rollup(es)}
            for code, es in sorted(by_branch.items())
        ]
        supervisors = []
        by_sup: dict[str | None, list[dict]] = {}
        for e in entries:
            by_sup.setdefault(e["supervisor_id"], []).append(e)
        for sid, es in by_sup.items():
            supervisors.append({"id": sid, "name": names.get(sid, "—"),
                                "branch_code": es[0]["branch_code"], **_rollup(es)})
        supervisors.sort(key=lambda s: (s["branch_code"] or "", s["name"]))
        game_users = [e for e in entries if e["game"]["started"]]
        return JSONResponse(
            {
                **base,
                "empty": False,
                "totals": _rollup(entries),
                "brands": _brand_rollup(conn, org_id, period, ids, brand),
                "branches": branches,
                "supervisors": supervisors,
                "reps": [_strip(e) for e in sorted(
                    entries, key=lambda e: -(e["attainment_pct"] or 0))],
                "gamification": {
                    "players": len(game_users),
                    "total_xp": sum(e["game"]["xp"] for e in entries),
                    "missions_completed": sum(e["game"]["missions_completed"] for e in entries),
                    "org_points": sum(e["org_points"] for e in entries),
                },
                "data_origin": _origins(conn, org_id, period, ids),
            }
        )

    @app.get("/api/v1/mgmt/branches/{code}")
    def branch_detail(
        code: str,
        period: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ) -> JSONResponse:
        profile, visible = mgmt_context(user, conn)
        org_id = user.organization_id
        branch = conn.execute(
            "SELECT code, name FROM branches WHERE organization_id = ? AND code = ?", (org_id, code)
        ).fetchone()
        rows = [r for r in _rep_rows(conn, org_id, visible) if r["branch_code"] == code]
        if branch is None or not rows:
            raise HTTPException(status_code=404, detail="Branch not found or outside your scope.")
        period = period or perf.latest_period(conn, org_id)
        ids = [r["user_id"] for r in rows]
        names = _names(conn, org_id)
        sales = perf.sales_by_user_brand(conn, org_id, period, ids) if period else {}
        targets = perf.targets_by_user_brand(conn, org_id, period, ids) if period else {}
        points = perf.org_points(conn, org_id, ids)
        games = game_status(conn, ids)
        entries = [_entry(r, sales, targets, points, games, names) for r in rows]
        sups: dict[str, list[dict]] = {}
        for e in entries:
            sups.setdefault(e["supervisor_id"], []).append(e)
        manager = conn.execute(
            """SELECT u.full_name FROM employee_positions p JOIN users u ON u.id = p.user_id
               WHERE p.organization_id = ? AND p.position = 'branch_manager' AND p.branch_code = ?""",
            (org_id, code),
        ).fetchone()
        return JSONResponse(
            {
                "is_demo": True,
                "period": period,
                "branch": {"code": branch["code"], "name": branch["name"],
                           "manager": manager["full_name"] if manager else None},
                "totals": _rollup(entries),
                "brands": _brand_rollup(conn, org_id, period, ids, None) if period else [],
                "supervisors": [
                    {"id": sid, "name": names.get(sid, "—"), **_rollup(es),
                     "reps": [_strip(e) for e in sorted(es, key=lambda e: -(e["attainment_pct"] or 0))]}
                    for sid, es in sorted(sups.items(), key=lambda kv: names.get(kv[0], ""))
                ],
                "data_origin": _origins(conn, org_id, period, ids) if period else {},
            }
        )

    @app.get("/api/v1/mgmt/reps/{rep_id}")
    def mgmt_rep(
        rep_id: str,
        period: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ) -> JSONResponse:
        profile, visible = mgmt_context(user, conn)
        if rep_id not in visible:
            raise HTTPException(status_code=404, detail="Sales representative not found.")
        return JSONResponse(rep_detail(conn, user.organization_id, rep_id, period))

    @app.get("/api/v1/me/performance")
    def my_performance(
        period: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ) -> JSONResponse:
        profile = member_profile(conn, user)
        if profile["position"] != "rep":
            raise HTTPException(status_code=403, detail="Only sales representatives have this view.")
        return JSONResponse({**rep_detail(conn, user.organization_id, user.id, period),
                             "viewer": profile})

    @app.get("/api/v1/leaderboard")
    def leaderboard(
        scope: str = Query("individual", pattern="^(individual|branch|team)$"),
        window: str = Query("season", pattern="^(season|daily|weekly|monthly)$"),
        branch: str | None = Query(None, max_length=40),
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ) -> JSONResponse:
        return JSONResponse(
            ranking.build(conn, user.organization_id, user.id, scope=scope, window=window, branch=branch)
        )

    # ---- imports (admin only)
    @app.get("/api/v1/mgmt/imports")
    def imports_list(user: CurrentUser = Depends(require_admin),
                     conn: sqlite3.Connection = Depends(conn_dep)) -> JSONResponse:
        return JSONResponse({"is_demo": True, "imports": imports.list_imports(conn, user.organization_id)})

    @app.post("/api/v1/mgmt/imports", dependencies=[Depends(csrf_guard)])
    async def imports_upload(
        file: UploadFile | None = File(None),
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ) -> JSONResponse:
        if file is None or not file.filename:
            return err(422, "NO_FILE", "No file was selected.")
        raw = await file.read(settings.sales_max_bytes + 1)
        try:
            row = imports.stage_import(
                conn, user, file.filename, raw,
                max_bytes=settings.sales_max_bytes, max_rows=settings.sales_max_rows,
            )
        except imports.ImportRejected as exc:
            extra = {"existing_import_id": exc.existing_id} if exc.existing_id else {}
            return err(exc.status_code, exc.code, exc.message, **extra)
        full = repo.sales_import(conn, row["id"], user.organization_id)
        return JSONResponse(imports.summarize(conn, full), status_code=201)

    @app.get("/api/v1/mgmt/imports/{import_id}")
    def import_detail(import_id: str, user: CurrentUser = Depends(require_admin),
                      conn: sqlite3.Connection = Depends(conn_dep)) -> JSONResponse:
        row = repo.sales_import(conn, import_id, user.organization_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Import not found.")
        return JSONResponse(imports.summarize(conn, row))

    @app.post("/api/v1/mgmt/imports/{import_id}/process", dependencies=[Depends(csrf_guard)])
    def import_process(import_id: str, user: CurrentUser = Depends(require_admin),
                       conn: sqlite3.Connection = Depends(conn_dep)) -> JSONResponse:
        row = repo.sales_import(conn, import_id, user.organization_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Import not found.")
        try:
            result = repo.process_sales_import(conn, row, user)
        except DomainError as exc:
            return err(409, exc.code, exc.message)
        fresh = repo.sales_import(conn, import_id, user.organization_id)
        return JSONResponse({"result": result, "import": imports.summarize(conn, fresh)})

    @app.get("/api/v1/mgmt/sample-workbook")
    def sample_workbook(variant: str = Query("main", pattern="^(main|overlap)$"),
                        user: CurrentUser = Depends(require_admin)) -> Response:
        data = (kiloos_demo.overlap_workbook_bytes() if variant == "overlap"
                else kiloos_demo.sample_workbook_bytes())
        name = "kiloos-sample-sales-overlap.xlsx" if variant == "overlap" else "kiloos-sample-sales.xlsx"
        return Response(content=data, media_type=XLSX,
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

"""Sales performance read-model (demo).

Single source for dashboards and for the sales-gated game mission, so the number a manager
sees is exactly the number the server uses to decide mission eligibility.

Rules (all PROPOSED / DEMO, nothing here is an approved KPI definition):
* only records with status ``scored`` count (imported, validated AND explicitly processed);
* the period of a sale is ``substr(sale_date, 1, 7)`` (Gregorian YYYY-MM in this demo);
* attainment = achieved amount / target amount for the same user, brand set and period;
* amounts are Decimal; nothing here uses floats for money.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from decimal import Decimal
from typing import Any

POSITION_ORDER = {"management": 0, "branch_manager": 1, "supervisor": 2, "rep": 3}


def dec(value: Any) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal(0)


def pct(achieved: Decimal, target: Decimal) -> float | None:
    if target <= 0:
        return None
    return float((achieved * 100 / target).quantize(Decimal("0.1")))


def money(value: Decimal) -> int | float:
    """JSON-friendly amount: integers stay integers (Rials), fractions stay exact enough."""
    return int(value) if value == value.to_integral_value() else float(value)


def latest_period(conn: sqlite3.Connection, org_id: str) -> str | None:
    row = conn.execute(
        """SELECT MAX(substr(sale_date, 1, 7)) AS p FROM sales_records
           WHERE organization_id = ? AND status = 'scored' AND sale_date IS NOT NULL""",
        (org_id,),
    ).fetchone()
    return row["p"] if row and row["p"] else None


def periods(conn: sqlite3.Connection, org_id: str) -> list[str]:
    rows = conn.execute(
        """SELECT DISTINCT substr(sale_date, 1, 7) AS p FROM sales_records
           WHERE organization_id = ? AND status = 'scored' AND sale_date IS NOT NULL
           ORDER BY p DESC""",
        (org_id,),
    ).fetchall()
    return [row["p"] for row in rows]


def _in_clause(user_ids: list[str] | None) -> tuple[str, list[str]]:
    if user_ids is None:
        return "", []
    if not user_ids:
        return " AND 1 = 0", []
    return f" AND user_id IN ({','.join('?' * len(user_ids))})", list(user_ids)


def sales_by_user_brand(
    conn: sqlite3.Connection,
    org_id: str,
    period: str,
    user_ids: list[str] | None = None,
    brand: str | None = None,
) -> dict[str, dict[str, dict[str, Decimal]]]:
    """{user_id: {brand: {amount, quantity, records}}} for processed sales in the period."""
    clause, params = _in_clause(user_ids)
    brand_clause = ""
    if brand:
        brand_clause = " AND brand_code = ?"
        params = [*params, brand]
    rows = conn.execute(
        f"""SELECT user_id, COALESCE(brand_code, 'UNASSIGNED') AS brand,
                   SUM(amount) AS amount, SUM(quantity) AS quantity, COUNT(*) AS records
            FROM sales_records
            WHERE organization_id = ? AND status = 'scored' AND substr(sale_date, 1, 7) = ?
                  AND user_id IS NOT NULL{clause}{brand_clause}
            GROUP BY user_id, brand""",  # noqa: S608 - clause is built from placeholders only
        [org_id, period, *params],
    ).fetchall()
    out: dict[str, dict[str, dict[str, Decimal]]] = defaultdict(dict)
    for row in rows:
        out[row["user_id"]][row["brand"]] = {
            "amount": dec(row["amount"]),
            "quantity": dec(row["quantity"]),
            "records": Decimal(row["records"]),
        }
    return out


def targets_by_user_brand(
    conn: sqlite3.Connection,
    org_id: str,
    period: str,
    user_ids: list[str] | None = None,
    brand: str | None = None,
) -> dict[str, dict[str, Decimal]]:
    clause, params = _in_clause(user_ids)
    if brand:
        clause += " AND brand_code = ?"
        params = [*params, brand]
    rows = conn.execute(
        f"""SELECT user_id, brand_code, amount FROM sales_targets
            WHERE organization_id = ? AND period = ?{clause}""",  # noqa: S608
        [org_id, period, *params],
    ).fetchall()
    out: dict[str, dict[str, Decimal]] = defaultdict(dict)
    for row in rows:
        out[row["user_id"]][row["brand_code"]] = dec(row["amount"])
    return out


def rep_summary(
    sales: dict[str, dict[str, dict[str, Decimal]]],
    targets: dict[str, dict[str, Decimal]],
    user_id: str,
) -> dict[str, Any]:
    brands = sorted(set(sales.get(user_id, {})) | set(targets.get(user_id, {})))
    by_brand = []
    total_amount = Decimal(0)
    total_target = Decimal(0)
    total_qty = Decimal(0)
    for code in brands:
        s = sales.get(user_id, {}).get(code, {})
        amount = s.get("amount", Decimal(0))
        qty = s.get("quantity", Decimal(0))
        target = targets.get(user_id, {}).get(code, Decimal(0))
        total_amount += amount
        total_target += target
        total_qty += qty
        by_brand.append(
            {
                "brand": code,
                "amount": money(amount),
                "quantity": money(qty),
                "target": money(target),
                "attainment_pct": pct(amount, target),
            }
        )
    return {
        "amount": money(total_amount),
        "quantity": money(total_qty),
        "target": money(total_target),
        "attainment_pct": pct(total_amount, total_target),
        "brands": by_brand,
        "_amount": total_amount,
        "_target": total_target,
    }


def org_points(
    conn: sqlite3.Connection, org_id: str, user_ids: list[str] | None = None
) -> dict[str, int]:
    """Organizational points inside the active competition window (same rule as /leaderboard)."""
    from app import repo

    competition = repo.active_competition(conn, org_id)
    start = competition["starts_at"] if competition else "0000-01-01T00:00:00+00:00"
    end = competition["ends_at"] if competition else "9999-12-31T23:59:59+00:00"
    clause, params = _in_clause(user_ids)
    rows = conn.execute(
        f"""SELECT user_id, SUM(points) AS total FROM score_events
            WHERE occurred_at >= ? AND occurred_at <= ?{clause}
            GROUP BY user_id""",  # noqa: S608
        [start, end, *params],
    ).fetchall()
    return {row["user_id"]: int(row["total"]) for row in rows}


# --------------------------------------------------------------------------- mission gate
SALES_GATE_MIN_PCT = Decimal("80")  # PROPOSED demo threshold (OD-14), shown in the UI


def sales_gate(conn: sqlite3.Connection, org_id: str, user_id: str) -> dict[str, Any]:
    """Server-side eligibility for the sales-driven mission.

    Eligible when the user's *processed* sales in the latest data period reach
    ``SALES_GATE_MIN_PCT`` % of that user's targets for the same period. The client never
    supplies any of these numbers.
    """
    period = latest_period(conn, org_id)
    base = {"minPct": float(SALES_GATE_MIN_PCT), "status": "PROPOSED"}
    if period is None:
        return {**base, "eligible": False, "period": None, "reason": "No processed sales yet"}
    sales = sales_by_user_brand(conn, org_id, period, [user_id])
    targets = targets_by_user_brand(conn, org_id, period, [user_id])
    summary = rep_summary(sales, targets, user_id)
    achieved, target = summary["_amount"], summary["_target"]
    attainment = pct(achieved, target)
    info = {
        **base,
        "period": period,
        "achieved": money(achieved),
        "target": money(target),
        "attainmentPct": attainment,
    }
    if target <= 0:
        return {**info, "eligible": False, "reason": f"No sales target for {period}"}
    if achieved * 100 < target * SALES_GATE_MIN_PCT:
        return {
            **info,
            "eligible": False,
            "reason": (
                f"Reach {SALES_GATE_MIN_PCT:g}% of your {period} target "
                f"(now {attainment}%) to unlock"
            ),
        }
    return {**info, "eligible": True, "reason": None}

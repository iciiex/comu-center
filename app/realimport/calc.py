"""Versioned calculation framework (first slice: brand × branch-manager level).

* Rule *types* are registered by name; every number (thresholds, step amounts) is data:
  thresholds live in ``ri_rule_sets.params_json`` (immutable per version), per-entity step amounts
  and targets come from the imported workbook (``ri_targets``) and are marked UNCONFIRMED.
* Rule sets can only be PROPOSED or UNCONFIRMED - nothing here, API included, can mark a rule
  APPROVED (that needs the business owner; see the decision register).
* Rewards are *indicative* numbers for reconciliation. No payment, settlement or XP/points link.
* Every result stores run id, batch id, rule version, brand, period, entity, input, target,
  achievement, reward, rule status, timestamp and links to the exact input facts.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections import defaultdict
from collections.abc import Callable
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from app import repo
from app.db import now_iso
from app.realimport.inspector import WorkbookError
from app.realimport.normalize import decimal_text, parse_decimal
from app.realimport.pipeline import get_batch

ALLOWED_RULE_STATUS = ("PROPOSED", "UNCONFIRMED")
RULE_TYPES: dict[str, Callable[..., dict[str, Any]]] = {}

SEED_RULE = {
    "code": "MGR_EFES_LADDER_PROPOSED",
    "rule_type": "achievement_ladder",
    "org_level": "branch_manager",
    "brand_code": "efes",
    "params": {
        "thresholds": ["0.97", "1.12", "1.22", "1.32"],
        "step_amounts": "target.extra.steps",
        "reward_unit": "rials as stored in the workbook (indicative)",
    },
    "notes": ("PROPOSED: thresholds read from the audit (§E.3: ladder 0.97/1.12/1.22/1.32); step amounts are the "
              "hard-coded per-row values of the manager sheet. Not approved by the business owner."),
}
# «مدیرکل» rows of the same sheet (general manager over lines G-P-A). The workbook uses the same
# ladder shape; whether it is the same rule for this level is unconfirmed, hence its own rule set.
SEED_RULE_GENERAL = {
    **SEED_RULE,
    "code": "MGR_GENERAL_EFES_LADDER_PROPOSED",
    "org_level": "general_manager",
    "notes": ("PROPOSED: same ladder shape as the branch-manager rule applied to the «مدیرکل» rows (lines G-P-A); "
              "thresholds copied, not confirmed for this level. Not approved by the business owner."),
}
SEED_RULES = (SEED_RULE, SEED_RULE_GENERAL)


def rule_type(name: str):
    def deco(fn):
        RULE_TYPES[name] = fn
        return fn
    return deco


class CalcError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


@rule_type("achievement_ladder")
def achievement_ladder(params: dict[str, Any], *, quantity: Decimal, target: Decimal | None, extra: dict[str, Any]) -> dict[str, Any]:
    """achievement = quantity / target; reward = amount of the highest step whose threshold is reached."""
    if target is None or target <= 0:
        raise CalcError("TARGET_INVALID", "Target is missing or not positive.")
    thresholds = [Decimal(t) for t in params["thresholds"]]
    steps = extra.get("steps") or []
    achievement = (quantity / target).quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)
    reached = [i for i, t in enumerate(thresholds) if achievement >= t]
    if not reached:
        return {"achievement": achievement, "reward": Decimal(0), "step": 0, "thresholds": [str(t) for t in thresholds]}
    step = reached[-1]
    amount = parse_decimal(steps[step]) if step < len(steps) else None
    if amount is None:
        raise CalcError("STEP_AMOUNT_MISSING", f"Step {step + 1} reached but the workbook has no amount for it.")
    return {"achievement": achievement, "reward": amount, "step": step + 1, "thresholds": [str(t) for t in thresholds]}


# ------------------------------------------------------------------------------- rule sets
def validate_params(rule_type_name: str, params: dict[str, Any]) -> None:
    if rule_type_name not in RULE_TYPES:
        raise WorkbookError("UNKNOWN_RULE_TYPE", f"Unknown rule type '{rule_type_name}'.")
    if rule_type_name == "achievement_ladder":
        th = params.get("thresholds")
        try:
            values = [Decimal(str(t)) for t in th]
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise WorkbookError("INVALID_PARAMS", "thresholds must be a list of decimal numbers.") from exc
        if not values or len(values) > 4 or values != sorted(values) or any(v <= 0 for v in values):
            raise WorkbookError("INVALID_PARAMS", "thresholds must be 1-4 ascending positive numbers.")


def seed_rule_sets(conn: sqlite3.Connection) -> None:
    for rule in SEED_RULES:
        conn.execute(
            """INSERT OR IGNORE INTO ri_rule_sets (code, version, rule_type, org_level, brand_code, params_json, status, notes, created_at)
               VALUES (?, 1, ?, ?, ?, ?, 'PROPOSED', ?, ?)""",
            (rule["code"], rule["rule_type"], rule["org_level"], rule["brand_code"],
             json.dumps(rule["params"], sort_keys=True), rule["notes"], now_iso()))
    conn.commit()


def create_rule_version(conn, user_id, code: str, rule_type_name: str, org_level: str, brand_code: str,
                        params: dict[str, Any], status: str, notes: str | None) -> sqlite3.Row:
    if status not in ALLOWED_RULE_STATUS:
        raise WorkbookError("RULE_STATUS_FORBIDDEN", "Rule sets can only be PROPOSED or UNCONFIRMED; approval is a business decision.", 403)
    validate_params(rule_type_name, params)
    version = (conn.execute("SELECT COALESCE(MAX(version), 0) AS v FROM ri_rule_sets WHERE code = ?", (code,)).fetchone()["v"]) + 1
    cur = conn.execute(
        """INSERT INTO ri_rule_sets (code, version, rule_type, org_level, brand_code, params_json, status, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (code, version, rule_type_name, org_level, brand_code.lower(), json.dumps(params, sort_keys=True), status, notes, now_iso()))
    repo.audit(conn, user_id, "ri.rule.created", "ri_rule_set", str(cur.lastrowid), {"code": code, "version": version, "status": status})
    conn.commit()
    return conn.execute("SELECT * FROM ri_rule_sets WHERE id = ?", (cur.lastrowid,)).fetchone()


def rule_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "code": row["code"], "version": row["version"], "rule_type": row["rule_type"],
            "org_level": row["org_level"], "brand": row["brand_code"], "params": json.loads(row["params_json"]),
            "status": row["status"], "notes": row["notes"], "created_at": row["created_at"]}


# ------------------------------------------------------------------------------------- runs
def _facts_by_cell(conn, batch_id: str, brand_id: int, sheet: str):
    """(branch_norm, line_code) -> list[(fact_id, net)] for valid facts of the brand on the basis sheet."""
    cells: dict[tuple[str, str], list[tuple[int, Decimal]]] = defaultdict(list)
    for r in conn.execute(
        """SELECT f.id, b.norm_key AS branch, l.norm_key AS line, f.net_cartons FROM ri_sales_facts f
           JOIN ri_branches b ON b.id = f.branch_id JOIN ri_sales_lines l ON l.id = f.sales_line_id
           WHERE f.batch_id = ? AND f.brand_id = ? AND f.source_sheet = ? AND f.status = 'valid' ORDER BY f.id""",
        (batch_id, brand_id, sheet)):
        cells[(r["branch"], r["line"])].append((r["id"], parse_decimal(r["net_cartons"]) or Decimal(0)))
    return cells


def run_calculation(conn: sqlite3.Connection, user_id: str | None, batch_id: str, rule_set_id: int):
    batch = get_batch(conn, batch_id)
    if batch["status"] != "confirmed":
        raise WorkbookError("BATCH_NOT_CONFIRMED", "Confirm the import batch before running a calculation.", 409)
    rule = conn.execute("SELECT * FROM ri_rule_sets WHERE id = ?", (rule_set_id,)).fetchone()
    if rule is None:
        raise WorkbookError("RULE_NOT_FOUND", "Rule set not found.", 404)
    if rule["status"] not in ALLOWED_RULE_STATUS:  # defensive: schema CHECK already forbids APPROVED
        raise WorkbookError("RULE_STATUS_FORBIDDEN", "Rule set has an unsupported status.", 409)
    fn = RULE_TYPES.get(rule["rule_type"])
    if fn is None:
        raise WorkbookError("UNKNOWN_RULE_TYPE", f"Unknown rule type '{rule['rule_type']}'.")
    cfg = json.loads(batch["config_json"])
    basis_role = cfg["carton_basis"]
    sheet = cfg["sheets"][basis_role]
    brand = conn.execute("SELECT id, norm_key FROM ri_brands WHERE norm_key = ?", (rule["brand_code"],)).fetchone()
    if brand is None:
        raise WorkbookError("BRAND_NOT_FOUND", f"Brand '{rule['brand_code']}' has no data in this batch.", 404)
    params = json.loads(rule["params_json"])
    targets = conn.execute(
        "SELECT * FROM ri_targets WHERE batch_id = ? AND brand_id = ? AND org_level = ? ORDER BY entity_key",
        (batch_id, brand["id"], rule["org_level"])).fetchall()
    cells = _facts_by_cell(conn, batch_id, brand["id"], sheet)
    known_lines = {r["norm_key"] for r in conn.execute("SELECT norm_key FROM ri_sales_lines")}

    fingerprint = {
        "basis": [basis_role, sheet], "rule": [rule["id"], hashlib.sha256(rule["params_json"].encode()).hexdigest()],
        "targets": [[t["entity_key"], t["target_cartons"], t["extra_json"]] for t in targets],
        "facts": sorted([b, ln, len(v), decimal_text(sum((x[1] for x in v), Decimal(0)))] for (b, ln), v in cells.items()),
    }
    input_hash = hashlib.sha256(json.dumps(fingerprint, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    existing = conn.execute(
        "SELECT * FROM ri_calc_runs WHERE batch_id=? AND rule_set_id=? AND brand_id=? AND org_level=? AND input_hash=?",
        (batch_id, rule["id"], brand["id"], rule["org_level"], input_hash)).fetchone()
    if existing is not None:
        return existing, True

    run_id, now = str(uuid.uuid4()), now_iso()
    conn.execute(
        "INSERT INTO ri_calc_runs (id, batch_id, rule_set_id, brand_id, org_level, input_basis, input_hash, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?)",
        (run_id, batch_id, rule["id"], brand["id"], rule["org_level"], f"{basis_role}:{sheet}", input_hash, now))
    ok = errors = 0
    for t in targets:
        branch_norm, _, line_label = t["entity_key"].partition("|")
        codes = set(line_label.split("-")) if line_label else set()
        extra = json.loads(t["extra_json"])
        facts = [f for (b, ln), v in cells.items() if b == branch_norm and ln in codes for f in v]
        quantity = sum((f[1] for f in facts), Decimal(0))
        target = parse_decimal(t["target_cartons"])
        label_row = conn.execute("SELECT source_value FROM ri_branches WHERE norm_key = ?", (branch_norm,)).fetchone()
        label = f"{label_row['source_value'] if label_row else branch_norm} · line {line_label or '?'}"
        explain: dict[str, Any] = {
            "formula": "achievement = input cartons ÷ target; reward = step amount of the highest reached threshold",
            "carton_basis": f"{basis_role}:{sheet}", "rule": {"code": rule["code"], "version": rule["version"], "status": rule["status"]},
            "target_source": t["source"], "target_status": t["status"], "facts": len(facts),
            "line_codes": sorted(codes), "workbook_row": extra.get("workbook_row"),
        }
        status, message, achievement, reward = "ok", None, None, None
        try:
            missing_lines = sorted(c for c in codes if c not in known_lines)
            if not codes or missing_lines:
                raise CalcError("LINE_GROUP_UNMAPPED", f"Line group has no matching sales line: {', '.join(missing_lines) or 'empty'}.")
            res = fn(params, quantity=quantity, target=target, extra=extra)
            achievement, reward = res["achievement"], res["reward"]
            explain.update(step=res["step"], thresholds=res["thresholds"], step_amounts=extra.get("steps"))
            ok += 1
        except CalcError as exc:
            status, message = "error", f"{exc.code}: {exc.message}"
            explain["error"] = exc.code
            errors += 1
        cur = conn.execute(
            """INSERT INTO ri_calc_results (run_id, batch_id, rule_set_id, rule_version, brand_id, period_year, period_month, org_level,
               entity_key, entity_label, input_quantity, target, achievement, reward_rials, rule_status, result_status, error_message,
               explain_json, calculated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, batch_id, rule["id"], rule["version"], brand["id"], batch["period_year"], batch["period_month"], rule["org_level"],
             t["entity_key"], label, decimal_text(quantity), t["target_cartons"], decimal_text(achievement), decimal_text(reward),
             rule["status"], status, message, json.dumps(explain, ensure_ascii=False), now))
        conn.executemany("INSERT INTO ri_calc_result_inputs (result_id, fact_id) VALUES (?, ?)", [(cur.lastrowid, f[0]) for f in facts])
    conn.execute("UPDATE ri_calc_runs SET result_count = ?, error_count = ? WHERE id = ?", (ok + errors, errors, run_id))
    repo.audit(conn, user_id, "ri.run.completed", "ri_calc_run", run_id,
               {"batch": batch_id, "rule": f"{rule['code']}@{rule['version']}", "results": ok + errors, "errors": errors})
    conn.commit()
    return conn.execute("SELECT * FROM ri_calc_runs WHERE id = ?", (run_id,)).fetchone(), False


def run_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    rule = conn.execute("SELECT * FROM ri_rule_sets WHERE id = ?", (row["rule_set_id"],)).fetchone()
    brand = conn.execute("SELECT norm_key FROM ri_brands WHERE id = ?", (row["brand_id"],)).fetchone()
    totals = conn.execute("SELECT input_quantity, target, reward_rials, result_status FROM ri_calc_results WHERE run_id = ?", (row["id"],)).fetchall()
    ok = [r for r in totals if r["result_status"] == "ok"]
    return {
        "id": row["id"], "batch_id": row["batch_id"], "brand": brand["norm_key"], "org_level": row["org_level"],
        "input_basis": row["input_basis"], "status": row["status"], "created_at": row["created_at"],
        "result_count": row["result_count"], "error_count": row["error_count"],
        "rule": {"id": rule["id"], "code": rule["code"], "version": rule["version"], "status": rule["status"]},
        "totals": {
            "input_cartons": decimal_text(sum((parse_decimal(r["input_quantity"]) or Decimal(0) for r in ok), Decimal(0))),
            "target_cartons": decimal_text(sum((parse_decimal(r["target"]) or Decimal(0) for r in ok), Decimal(0))),
            "indicative_reward_rials": decimal_text(sum((parse_decimal(r["reward_rials"]) or Decimal(0) for r in ok), Decimal(0))),
        },
    }


def result_dicts(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    out = []
    for r in conn.execute("SELECT * FROM ri_calc_results WHERE run_id = ? ORDER BY entity_key", (run_id,)):
        brand = conn.execute("SELECT norm_key FROM ri_brands WHERE id = ?", (r["brand_id"],)).fetchone()
        out.append({
            "id": r["id"], "run_id": r["run_id"], "import_batch_id": r["batch_id"], "rule_set_id": r["rule_set_id"],
            "rule_version": r["rule_version"], "brand": brand["norm_key"],
            "period": {"calendar": "jalali", "year": r["period_year"], "month": r["period_month"]},
            "org_level": r["org_level"], "entity": r["entity_label"], "entity_key": r["entity_key"],
            "input_quantity": r["input_quantity"], "target": r["target"], "achievement": r["achievement"],
            "reward_rials": r["reward_rials"], "rule_status": r["rule_status"], "result_status": r["result_status"],
            "error": r["error_message"], "calculated_at": r["calculated_at"], "explain": json.loads(r["explain_json"]),
        })
    return out

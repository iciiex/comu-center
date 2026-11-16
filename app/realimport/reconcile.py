"""Reconciliation: import-level (primary vs derived sheet) and run-level (prototype vs workbook figures).

Principles: variances are computed, never rounded away; a difference is only labelled ``explained``
when the explanation is *verified* row by row; a run is never reported as reproducing the workbook
unless every compared entity matches.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import Any

from app.db import now_iso
from app.realimport.normalize import decimal_text, parse_decimal

TOLERANCE = Decimal("0.0005")
ROUNDING_EXPLANATION = (
    "SalesData is a Power Query output that casts net cartons to Int64 (convention detected from the data: {mode}) "
    "while the base sheet keeps fractional cartons. Verified per business key: every differing key equals "
    "the sum of its individually rounded rows. The difference is a rounding artefact of the derived sheet, "
    "not missing sales. It is shown, not hidden; the carton basis used for calculation is configurable (BD-05)."
)


def _dec(text: str | None) -> Decimal:
    return parse_decimal(text) or Decimal(0)


def _pct(variance: Decimal, reference: Decimal) -> Decimal | None:
    return None if reference == 0 else (variance.copy_abs() / reference.copy_abs() * 100)


def _check(code: str, title: str, *, reference=None, prototype=None, matched=None, missing=None, duplicates=None,
           unresolved=None, status: str, explanation: str = "", detail: dict | None = None) -> dict[str, Any]:
    variance = pct = None
    if reference is not None and prototype is not None:
        variance = (prototype - reference).copy_abs()
        pct = _pct(variance, reference)
    return {
        "check_code": code, "title": title,
        "reference_value": decimal_text(reference) if reference is not None else None,
        "prototype_value": decimal_text(prototype) if prototype is not None else None,
        "abs_variance": decimal_text(variance) if variance is not None else None,
        "pct_variance": None if pct is None else format(pct.quantize(Decimal("0.0001")), "f"),
        "matched": matched, "missing": missing, "duplicates": duplicates, "unresolved": unresolved,
        "status": status, "explanation": explanation, "detail": detail or {},
    }


def _sheet_facts(conn: sqlite3.Connection, batch_id: str, sheet: str):
    return conn.execute(
        "SELECT id, business_key_hash, net_cartons, gross_cartons, invoice_count FROM ri_sales_facts "
        "WHERE batch_id = ? AND source_sheet = ? AND status = 'valid'", (batch_id, sheet)).fetchall()


def _aggregate(rows) -> dict[str, dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = {}
    for r in rows:
        a = agg.setdefault(r["business_key_hash"], {"net": Decimal(0), "gross": Decimal(0), "inv": 0, "rows": 0, "rounded": Decimal(0), "rounded_even": Decimal(0)})
        net = _dec(r["net_cartons"])
        a["net"] += net
        a["gross"] += _dec(r["gross_cartons"])
        a["inv"] += r["invoice_count"] or 0
        a["rows"] += 1
        a["rounded"] += net.quantize(Decimal(1), rounding=ROUND_HALF_UP)
        a["rounded_even"] += net.quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
    return agg


def compute_import_checks(conn: sqlite3.Connection, batch_id: str) -> list[dict[str, Any]]:
    batch = conn.execute("SELECT * FROM ri_import_batches WHERE id = ?", (batch_id,)).fetchone()
    cfg = json.loads(batch["config_json"])
    counts = json.loads(batch["counts_json"])
    sheets = counts.get("sheets", {})
    checks: list[dict[str, Any]] = []

    # completeness: every source row is accounted for (valid + rejected == rows read)
    for role, s in sheets.items():
        accounted = s["valid"] + s["rejected"]
        ok = accounted == s["rows_read"]
        explanation = "All rows read were stored as valid or rejected facts." if ok else "Rows were lost between raw and normalised layers."
        if ok and s["rejected"]:
            explanation = f"{s['rejected']} rows were rejected: {s['rejected_by_code']}. They are excluded and listed in the preview."
        checks.append(_check(
            f"IMP-ROWS-{role}", f"Rows read vs stored — {s['sheet']}",
            reference=Decimal(s["rows_read"]), prototype=Decimal(accounted), matched=s["valid"], missing=s["rows_read"] - accounted,
            duplicates=s["duplicate_key_rows"], status="error" if not ok else ("warning" if s["rejected"] else "match"),
            explanation=explanation, detail={"rejected_by_code": s["rejected_by_code"]}))

    primary_rows = _sheet_facts(conn, batch_id, cfg["sheets"]["sales_primary"])
    derived_name = cfg["sheets"].get("sales_derived")
    derived_rows = _sheet_facts(conn, batch_id, derived_name) if "sales_derived" in sheets else []
    primary, derived = _aggregate(primary_rows), _aggregate(derived_rows)

    for role, agg in (("sales_primary", primary), ("sales_derived", derived)):
        if role in sheets:
            dup_keys = sum(1 for a in agg.values() if a["rows"] > 1)
            extra = sum(a["rows"] - 1 for a in agg.values())
            checks.append(_check(
                f"IMP-DUPKEYS-{role}", f"Duplicate business keys — {sheets[role]['sheet']}",
                reference=Decimal(0), prototype=Decimal(dup_keys), duplicates=extra,
                status="warning" if dup_keys else "match",
                explanation=("There is no invoice id, so duplicate keys cannot be told apart from separate lines. "
                             "Policy keep_flagged: every row is kept with an ordinal and a flag (BD-07)." if dup_keys else "No duplicate keys."),
                detail={"keys_with_duplicates": dup_keys, "extra_rows": extra}))

    if derived:
        only_p = set(primary) - set(derived)
        only_d = set(derived) - set(primary)
        checks.append(_check(
            "IMP-KEYS", "Business keys: base sheet vs derived sheet", reference=Decimal(len(derived)), prototype=Decimal(len(primary)),
            matched=len(set(primary) & set(derived)), missing=len(only_p) + len(only_d),
            status="match" if not only_p and not only_d else "error",
            explanation=("Both sheets carry the same keys." if not only_p and not only_d else
                         f"{len(only_p)} keys only in the base sheet, {len(only_d)} only in the derived sheet.")))
        for code, title, field, unit in (("IMP-GROSS", "Gross cartons Σ", "gross", "cartons"), ("IMP-INVOICES", "Invoice count Σ", "inv", "invoices")):
            ref = sum((Decimal(a[field]) for a in derived.values()), Decimal(0))
            proto = sum((Decimal(a[field]) for a in primary.values()), Decimal(0))
            differing = sum(1 for k in primary if k in derived and abs(primary[k][field] - derived[k][field]) > TOLERANCE)
            checks.append(_check(code, f"{title} (derived sheet = reference, base sheet = prototype)", reference=ref, prototype=proto,
                                 matched=len(primary) - differing, missing=len(only_p),
                                 status="match" if differing == 0 and abs(proto - ref) <= TOLERANCE else "warning",
                                 explanation=f"Compared per business key; {differing} keys differ." if differing else f"Identical per key ({unit})."))
        # net cartons: the known rounding discrepancy, verified per key
        ref_net = sum((a["net"] for a in derived.values()), Decimal(0))
        proto_net = sum((a["net"] for a in primary.values()), Decimal(0))
        differing = [k for k in primary if k in derived and abs(primary[k]["net"] - derived[k]["net"]) > TOLERANCE]
        # Which integer-cast convention does the derived sheet follow? Test both against the data, keep the better one.
        by_mode = {
            mode: [k for k in differing if abs(primary[k][field] - derived[k]["net"]) <= TOLERANCE]
            for mode, field in (("half_away_from_zero", "rounded"), ("half_to_even", "rounded_even"))
        }
        rounding_mode = max(by_mode, key=lambda m: len(by_mode[m]))
        explained = by_mode[rounding_mode]
        unexplained = len(differing) - len(explained)
        delta = proto_net - ref_net
        if not differing and abs(delta) <= TOLERANCE:
            status, why = "match", "Net cartons are identical on both sheets."
        elif differing and unexplained == 0:
            status, why = "explained", ROUNDING_EXPLANATION.format(mode=rounding_mode.replace("_", " "))
        else:
            status, why = "warning", f"{unexplained} differing keys are NOT explained by integer rounding; investigate before relying on either basis."
        checks.append(_check(
            "IMP-NET", "Net cartons Σ (derived sheet = reference, base sheet = prototype)", reference=ref_net, prototype=proto_net,
            matched=len(primary) - len(differing), missing=unexplained, status=status, explanation=why,
            detail={"signed_variance": decimal_text(delta), "differing_keys": len(differing), "explained_by_rounding": len(explained),
                    "rounding_mode_tested": {m: len(v) for m, v in by_mode.items()}, "rounding_mode": rounding_mode,
                    "unexplained": unexplained, "fractional_rows_primary": sum(1 for r in primary_rows if _dec(r["net_cartons"]) % 1 != 0),
                    "negative_rows_primary": sum(1 for r in primary_rows if _dec(r["net_cartons"]) < 0)}))

    issue_rows = conn.execute(
        "SELECT issue_type, COUNT(*) AS n FROM ri_mapping_issues WHERE batch_id = ? AND severity IN ('warning','error') GROUP BY issue_type",
        (batch_id,)).fetchall()
    unresolved = sum(r["n"] for r in issue_rows)
    checks.append(_check(
        "IMP-MAPPINGS", "Unresolved mappings (warnings and errors)", reference=Decimal(0), prototype=Decimal(unresolved), unresolved=unresolved,
        status="warning" if unresolved else "match",
        explanation="Each item needs a business decision before the corresponding rule can be confirmed (see decision register)." if unresolved else "No open mapping warnings.",
        detail={r["issue_type"]: r["n"] for r in issue_rows}))
    return checks


def store_checks(conn: sqlite3.Connection, batch_id: str, run_id: str | None, checks: list[dict[str, Any]], prefix: str) -> None:
    conn.execute("DELETE FROM ri_reconciliation_checks WHERE batch_id = ? AND COALESCE(run_id, '') = COALESCE(?, '') AND check_code LIKE ?",
                 (batch_id, run_id, prefix + "%"))
    for c in checks:
        conn.execute(
            """INSERT INTO ri_reconciliation_checks (batch_id, run_id, check_code, title, reference_value, prototype_value, abs_variance,
               pct_variance, matched, missing, duplicates, unresolved, status, explanation, detail_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (batch_id, run_id, c["check_code"], c["title"], c["reference_value"], c["prototype_value"], c["abs_variance"], c["pct_variance"],
             c["matched"], c["missing"], c["duplicates"], c["unresolved"], c["status"], c["explanation"], json.dumps(c["detail"]), now_iso()))


def refresh_import_checks(conn: sqlite3.Connection, batch_id: str) -> list[dict[str, Any]]:
    checks = compute_import_checks(conn, batch_id)
    store_checks(conn, batch_id, None, checks, "IMP-")
    conn.commit()
    return checks


def compute_run_checks(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    run = conn.execute("SELECT r.*, b.norm_key AS brand_code FROM ri_calc_runs r JOIN ri_brands b ON b.id = r.brand_id WHERE r.id = ?", (run_id,)).fetchone()
    results = conn.execute("SELECT entity_key, input_quantity, reward_rials, result_status FROM ri_calc_results WHERE run_id = ?", (run_id,)).fetchall()
    refs: dict[str, dict[str, Decimal]] = defaultdict(dict)
    for r in conn.execute("SELECT ref_code, value FROM ri_workbook_references WHERE batch_id = ? AND brand_code = ? AND org_level = ? AND ref_code LIKE 'mgr|%'",
                          (run["batch_id"], run["brand_code"], run["org_level"])):  # like for like: same org level only
        _, _, rest = r["ref_code"].split("|", 2)  # mgr|<brand>|<branch>|<line group>|<kind>
        entity, kind = rest.rsplit("|", 1)
        refs[entity][kind] = _dec(r["value"])
    by_entity = {r["entity_key"]: r for r in results}
    checks = []

    def compare(code, title, kind, proto_field, explanation_ok, explanation_diff):
        ref_total = proto_total = Decimal(0)
        matched = mism = 0
        for entity, values in refs.items():
            if kind not in values:
                continue
            res = by_entity.get(entity)
            ref_total += values[kind]
            if res is None or res["result_status"] != "ok":
                continue
            proto = _dec(res[proto_field])
            proto_total += proto
            if abs(proto - values[kind]) <= TOLERANCE:
                matched += 1
            else:
                mism += 1
        missing = sum(1 for e, v in refs.items() if kind in v and (e not in by_entity or by_entity[e]["result_status"] != "ok"))
        extra = sum(1 for e in by_entity if e not in refs)
        all_ok = mism == 0 and missing == 0 and matched > 0  # an empty comparison is never a match
        if matched + mism == 0 and not missing:
            explanation_diff = "No workbook reference figures were found for this run, so nothing could be compared."
        checks.append(_check(code, title, reference=ref_total, prototype=proto_total, matched=matched, missing=missing + extra,
                             status="match" if all_ok else "warning", explanation=explanation_ok if all_ok else explanation_diff,
                             detail={"entities_compared": matched + mism, "entities_differing": mism,
                                     "entities_without_result": missing, "results_without_reference": extra}))

    compare("RUN-SALES", "Input cartons vs workbook «فروش قطعی»", "sales", "input_quantity",
            "Every entity's input equals the workbook figure.",
            "Workbook definitive sales are hard-coded and may include manual adjustments or the rounded basis "
            "(audit §D: 32 of 49 manager rows reproduce). Differences are listed, not forced to match.")
    compare("RUN-REWARD", "Indicative reward vs workbook «مبلغ»", "reward", "reward_rials",
            "Every entity's indicative reward equals the workbook amount (rule still PROPOSED).",
            "Rule parameters are PROPOSED and the relief («ارفاق») adjustment is not modelled; "
            "the prototype does not claim to reproduce the workbook until this check matches (BD-09).")
    return checks


def refresh_run_checks(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    run = conn.execute("SELECT batch_id FROM ri_calc_runs WHERE id = ?", (run_id,)).fetchone()
    checks = compute_run_checks(conn, run_id)
    store_checks(conn, run["batch_id"], run_id, checks, "RUN-")
    conn.commit()
    return checks


def list_checks(conn: sqlite3.Connection, batch_id: str) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM ri_reconciliation_checks WHERE batch_id = ? ORDER BY run_id IS NOT NULL, check_code", (batch_id,)).fetchall()
    return [{**{k: r[k] for k in r.keys() if k != "detail_json"}, "detail": json.loads(r["detail_json"])} for r in rows]

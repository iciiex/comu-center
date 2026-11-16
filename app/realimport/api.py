"""JSON API of the real-import spike: ``/api/v1/ri/*`` (admin only, CSRF on writes).

Registered only when KILOOS_REAL_IMPORT=1. Every payload is built from pseudonymised read models;
``assert_clean`` re-checks each response against the raw personal values of the batch.
"""

from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from typing import Any

from fastapi import Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from app import db as appdb
from app.realimport import calc, decisions, pipeline, reconcile
from app.realimport import profile as P
from app.realimport.inspector import WorkbookError
from app.realimport.normalize import decimal_text, parse_decimal
from app.realimport.pseudo import assert_clean, pseudonym
from app.realimport.synthetic import synthetic_workbook_bytes

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
NOTICE = ("PROTOTYPE — real-workbook import spike. Rule sets are PROPOSED, targets and mappings UNCONFIRMED. "
          "Quantities are cartons; nothing is converted to Rials; no reward is paid.")
STATUS_LEGEND = {
    "confirmed": "Confirmed by the business owner",
    "proposed": "Proposed — configurable prototype value",
    "unconfirmed": "Unconfirmed — taken from the workbook, owner unknown",
    "reconciliation_warning": "Prototype and workbook differ and the difference is not (fully) explained",
    "calculation_error": "The calculation could not be completed for this entity",
}


def _raw_values(conn: sqlite3.Connection) -> list[str]:
    """Personal source values currently in the database (for the response leak guard)."""
    vals = [r[0] for r in conn.execute("SELECT visitor_key_source FROM ri_visitor_assignments")]
    vals += [r[0] for r in conn.execute("SELECT personnel_code FROM ri_employees")]
    vals += [r[0] for r in conn.execute("SELECT source_value FROM ri_customers")]
    return vals


def _workbook(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "file_name": row["file_name"], "sha256": row["sha256"], "size_bytes": row["size_bytes"],
            "data_origin": row["data_origin"], "created_at": row["created_at"], "inspection": json.loads(row["inspection_json"])}


def register(app, *, settings, conn_dep, require_admin, csrf_guard) -> None:
    boot = appdb.connect(settings.db_path)
    try:
        decisions.seed_decisions(boot)
        calc.seed_rule_sets(boot)
    finally:
        boot.close()

    def out(conn: sqlite3.Connection, payload: Any, status: int = 200) -> JSONResponse:
        assert_clean(payload, _raw_values(conn))
        return JSONResponse(payload, status_code=status, headers={"Cache-Control": "no-store"})

    @app.exception_handler(WorkbookError)
    async def _workbook_error(request: Request, exc: WorkbookError) -> JSONResponse:
        return JSONResponse({"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status_code)

    @app.exception_handler(calc.CalcError)
    async def _calc_error(request: Request, exc: calc.CalcError) -> JSONResponse:
        return JSONResponse({"error": {"code": exc.code, "message": exc.message}}, status_code=422)

    base = "/api/v1/ri"

    @app.get(f"{base}/meta")
    def meta(user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        return out(conn, {
            "enabled": True, "notice": NOTICE, "status_legend": STATUS_LEGEND,
            "default_config": P.default_config(), "rule_types": sorted(calc.RULE_TYPES),
            "max_upload_mb": settings.real_import_max_bytes // (1024 * 1024),
        })

    @app.get(f"{base}/synthetic-workbook")
    def synthetic_workbook(user=Depends(require_admin)) -> Response:
        return Response(synthetic_workbook_bytes(), media_type=XLSX,
                        headers={"Content-Disposition": 'attachment; filename="kiloos-synthetic-real-layout.xlsx"'})

    # ---- workbooks and batches
    @app.post(f"{base}/workbooks", dependencies=[Depends(csrf_guard)])
    async def upload(file: UploadFile | None = File(None), user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        if file is None or not file.filename:
            raise WorkbookError("NO_FILE", "No file was selected.")
        raw = await file.read(settings.real_import_max_bytes + 1)
        wb_row, replayed = pipeline.upload_workbook(conn, settings, user.id, file.filename, raw)
        batch, batch_replayed = pipeline.create_batch(conn, settings, user.id, wb_row["id"], None)
        return out(conn, {"workbook": _workbook(wb_row), "batch": pipeline.batch_dict(conn, batch),
                          "replayed": replayed and batch_replayed}, 200 if replayed else 201)

    @app.get(f"{base}/workbooks")
    def workbooks(user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        rows = conn.execute("SELECT * FROM ri_workbooks ORDER BY created_at DESC, rowid DESC").fetchall()
        return out(conn, {"workbooks": [_workbook(r) for r in rows]})

    @app.post(f"{base}/batches", dependencies=[Depends(csrf_guard)])
    async def create_batch(request: Request, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(status_code=400, detail="Expected a JSON request body.") from None
        if not isinstance(body, dict) or not isinstance(body.get("workbook_id"), str):
            raise HTTPException(status_code=422, detail="workbook_id is required.")
        batch, replayed = pipeline.create_batch(conn, settings, user.id, body["workbook_id"], body.get("config"))
        return out(conn, {"batch": pipeline.batch_dict(conn, batch), "replayed": replayed}, 200 if replayed else 201)

    @app.get(f"{base}/batches")
    def batches(user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        rows = conn.execute("SELECT * FROM ri_import_batches ORDER BY created_at DESC, rowid DESC").fetchall()
        return out(conn, {"batches": [pipeline.batch_dict(conn, r) for r in rows]})

    @app.get(f"{base}/batches/{{batch_id}}")
    def batch(batch_id: str, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        row = pipeline.get_batch(conn, batch_id)
        inspection = json.loads(conn.execute("SELECT inspection_json FROM ri_workbooks WHERE id = ?", (row["workbook_id"],)).fetchone()[0])
        return out(conn, {"batch": pipeline.batch_dict(conn, row), "inspection": inspection})

    @app.post(f"{base}/batches/{{batch_id}}/validate", dependencies=[Depends(csrf_guard)])
    def validate(batch_id: str, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        row, replayed = pipeline.stage_batch(conn, settings, user.id, batch_id)
        if not replayed:
            reconcile.refresh_import_checks(conn, batch_id)
        return out(conn, {"batch": pipeline.batch_dict(conn, row), "replayed": replayed})

    @app.get(f"{base}/batches/{{batch_id}}/preview")
    def preview(batch_id: str, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        return out(conn, pipeline.preview(conn, settings, batch_id))

    @app.post(f"{base}/batches/{{batch_id}}/confirm", dependencies=[Depends(csrf_guard)])
    def confirm(batch_id: str, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        row, replayed = pipeline.confirm_batch(conn, user.id, batch_id)
        return out(conn, {"batch": pipeline.batch_dict(conn, row), "replayed": replayed})

    # ---- mappings
    @app.get(f"{base}/batches/{{batch_id}}/mappings")
    def mappings(batch_id: str, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        pipeline.get_batch(conn, batch_id)
        issues = [
            {"type": r["issue_type"], "label": pipeline.ISSUE_LABELS.get(r["issue_type"], r["issue_type"]), "severity": r["severity"],
             "entity": r["entity_ref"], "detail": json.loads(r["detail_json"]), "status": r["status"]}
            for r in conn.execute("SELECT * FROM ri_mapping_issues WHERE batch_id = ? ORDER BY severity DESC, issue_type, entity_ref", (batch_id,))
        ]
        schemes = []
        for s in conn.execute("SELECT * FROM ri_branch_group_schemes WHERE code LIKE ? || ':%' ORDER BY code", (batch_id,)):
            members = conn.execute(
                "SELECT b.source_value AS branch, m.group_code FROM ri_branch_group_members m JOIN ri_branches b ON b.id = m.branch_id "
                "WHERE m.scheme_id = ? ORDER BY b.source_value", (s["id"],)).fetchall()
            schemes.append({"code": s["code"].split(":", 1)[1], "title": s["title"], "source": s["source"], "status": s["status"],
                            "members": [{"branch": m["branch"], "group": m["group_code"]} for m in members]})
        groups = [dict(r) for r in conn.execute(
            "SELECT source_value, main_group, mapping_status FROM ri_customer_groups ORDER BY source_value")]
        assignments = conn.execute(
            """SELECT va.pseudonym, va.seller_type_norm, b.source_value AS branch, l.norm_key AS line, e.pseudonym AS employee
               FROM ri_visitor_assignments va LEFT JOIN ri_branches b ON b.id = va.branch_id
               LEFT JOIN ri_sales_lines l ON l.id = va.sales_line_id LEFT JOIN ri_employees e ON e.id = va.employee_id
               WHERE va.batch_id = ? ORDER BY e.pseudonym, va.pseudonym LIMIT 200""", (batch_id,)).fetchall()
        return out(conn, {
            "status_note": "All mappings are UNCONFIRMED until a business owner approves them (decision register).",
            "issues": issues, "branch_group_schemes": schemes, "customer_groups": groups,
            "assignments": [{"visitor": a["pseudonym"], "employee": a["employee"], "seller_type": a["seller_type_norm"],
                             "branch": a["branch"], "sales_line": a["line"]} for a in assignments],
            "roster": json.loads(pipeline.get_batch(conn, batch_id)["counts_json"]).get("roster", {}),
        })

    # ---- rules and runs
    @app.get(f"{base}/rules")
    def rules(user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        return out(conn, {"rules": [calc.rule_dict(r) for r in conn.execute("SELECT * FROM ri_rule_sets ORDER BY code, version")],
                          "note": "Rule sets can only be PROPOSED or UNCONFIRMED. APPROVED requires the business owner."})

    @app.post(f"{base}/rules", dependencies=[Depends(csrf_guard)])
    async def create_rule(request: Request, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(status_code=400, detail="Expected a JSON request body.") from None
        need = ("code", "rule_type", "org_level", "brand", "params", "status")
        if not isinstance(body, dict) or any(k not in body for k in need) or not isinstance(body["params"], dict):
            raise HTTPException(status_code=422, detail=f"Required fields: {', '.join(need)}.")
        row = calc.create_rule_version(conn, user.id, str(body["code"]), str(body["rule_type"]), str(body["org_level"]),
                                       str(body["brand"]), body["params"], str(body["status"]), body.get("notes"))
        return out(conn, {"rule": calc.rule_dict(row)}, 201)

    @app.post(f"{base}/batches/{{batch_id}}/runs", dependencies=[Depends(csrf_guard)])
    async def start_run(batch_id: str, request: Request, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(status_code=400, detail="Expected a JSON request body.") from None
        if not isinstance(body, dict) or not isinstance(body.get("rule_set_id"), int):
            raise HTTPException(status_code=422, detail="rule_set_id (integer) is required.")
        run, replayed = calc.run_calculation(conn, user.id, batch_id, body["rule_set_id"])
        if not replayed:
            reconcile.refresh_run_checks(conn, run["id"])
        return out(conn, {"run": calc.run_dict(conn, run), "replayed": replayed}, 200 if replayed else 201)

    @app.get(f"{base}/batches/{{batch_id}}/runs")
    def runs(batch_id: str, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        pipeline.get_batch(conn, batch_id)
        rows = conn.execute("SELECT * FROM ri_calc_runs WHERE batch_id = ? ORDER BY created_at DESC, rowid DESC", (batch_id,)).fetchall()
        return out(conn, {"runs": [calc.run_dict(conn, r) for r in rows]})

    @app.get(f"{base}/runs/{{run_id}}")
    def run_detail(run_id: str, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        row = conn.execute("SELECT * FROM ri_calc_runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise WorkbookError("RUN_NOT_FOUND", "Calculation run not found.", 404)
        return out(conn, {"run": calc.run_dict(conn, row), "results": calc.result_dicts(conn, run_id),
                          "reconciliation": [c for c in reconcile.list_checks(conn, row["batch_id"]) if c["run_id"] == run_id]})

    @app.get(f"{base}/results/{{result_id}}/inputs")
    def result_inputs(result_id: int, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                      user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        res = conn.execute("SELECT * FROM ri_calc_results WHERE id = ?", (result_id,)).fetchone()
        if res is None:
            raise WorkbookError("RESULT_NOT_FOUND", "Result not found.", 404)
        total = conn.execute("SELECT COUNT(*) FROM ri_calc_result_inputs WHERE result_id = ?", (result_id,)).fetchone()[0]
        rows = conn.execute(
            """SELECT f.id, rr.row_number, f.source_sheet, f.visitor_key_norm, f.net_cartons, f.gross_cartons, f.dup_ordinal,
                      f.issues_json, b.source_value AS branch, l.norm_key AS line, s.code AS sku, c.pseudonym AS customer
               FROM ri_calc_result_inputs i JOIN ri_sales_facts f ON f.id = i.fact_id JOIN ri_raw_rows rr ON rr.id = f.raw_row_id
               LEFT JOIN ri_branches b ON b.id = f.branch_id LEFT JOIN ri_sales_lines l ON l.id = f.sales_line_id
               LEFT JOIN ri_skus s ON s.id = f.sku_id LEFT JOIN ri_customers c ON c.id = f.customer_id
               WHERE i.result_id = ? ORDER BY f.id LIMIT ? OFFSET ?""", (result_id, limit, offset)).fetchall()
        rule = conn.execute("SELECT code, version, status FROM ri_rule_sets WHERE id = ?", (res["rule_set_id"],)).fetchone()
        return out(conn, {
            "result_id": result_id, "run_id": res["run_id"], "import_batch_id": res["batch_id"],
            "rule": {"code": rule["code"], "version": res["rule_version"], "status": rule["status"]},
            "total": total, "limit": limit, "offset": offset,
            "inputs": [{"fact_id": r["id"], "source_sheet": r["source_sheet"], "row_number": r["row_number"], "branch": r["branch"],
                        "sales_line": r["line"], "sku": r["sku"], "customer": r["customer"],
                        "visitor": pseudonym("visitor", r["visitor_key_norm"], settings.pseudonym_key),
                        "gross_cartons": r["gross_cartons"], "net_cartons": r["net_cartons"],
                        "duplicate_ordinal": r["dup_ordinal"], "flags": json.loads(r["issues_json"])} for r in rows],
        })

    # ---- reconciliation, summary, decisions
    @app.get(f"{base}/batches/{{batch_id}}/reconciliation")
    def reconciliation(batch_id: str, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        batch = pipeline.get_batch(conn, batch_id)
        checks = reconcile.list_checks(conn, batch_id)
        if not checks and batch["status"] in ("validated", "confirmed"):
            reconcile.refresh_import_checks(conn, batch_id)
            checks = reconcile.list_checks(conn, batch_id)
        order = ["match", "explained", "warning", "error"]
        worst = max((c["status"] for c in checks), key=order.index, default="match")
        return out(conn, {"batch_id": batch_id, "checks": checks, "overall": worst,
                          "claim": ("The prototype reproduces the workbook ONLY where a check says 'match'. "
                                    "Explained differences are verified, not ignored." if checks else "No checks yet — validate the batch.")})

    @app.get(f"{base}/batches/{{batch_id}}/summary")
    def summary(batch_id: str, user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        batch = pipeline.get_batch(conn, batch_id)
        counts = json.loads(batch["counts_json"])
        cfg = json.loads(batch["config_json"])
        basis = cfg["sheets"][cfg["carton_basis"]]
        brands = []
        for b in conn.execute(
            """SELECT br.norm_key AS brand, COUNT(*) AS rows, br.id FROM ri_sales_facts f JOIN ri_brands br ON br.id = f.brand_id
               WHERE f.batch_id = ? AND f.source_sheet = ? AND f.status = 'valid' GROUP BY br.id ORDER BY br.norm_key""", (batch_id, basis)):
            net = sum((parse_decimal(r[0]) or Decimal(0) for r in conn.execute(
                "SELECT net_cartons FROM ri_sales_facts WHERE batch_id = ? AND source_sheet = ? AND status = 'valid' AND brand_id = ?",
                (batch_id, basis, b["id"]))), Decimal(0))
            levels = []
            for run in conn.execute(
                "SELECT * FROM ri_calc_runs WHERE batch_id = ? AND brand_id = ? ORDER BY created_at DESC, rowid DESC", (batch_id, b["id"])):
                d = calc.run_dict(conn, run)
                levels.append({"org_level": d["org_level"], "run_id": d["id"], "rule": d["rule"], "results": d["result_count"],
                               "errors": d["error_count"], **d["totals"]})
            brands.append({"brand": b["brand"], "rows": b["rows"], "net_cartons": decimal_text(net), "levels": levels})
        return out(conn, {"batch": pipeline.batch_dict(conn, batch), "basis": basis, "brands": brands,
                          "issues": counts.get("issues", {}), "notice": NOTICE})

    @app.get(f"{base}/decisions")
    def decision_register(user=Depends(require_admin), conn: sqlite3.Connection = Depends(conn_dep)):
        return out(conn, {"decisions": decisions.list_decisions(conn),
                          "note": "Read-only: a decision becomes CONFIRMED only through the business owner, not through this application."})

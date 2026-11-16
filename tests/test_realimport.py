"""Real-import spike: normalisation, pipeline, idempotency, privacy, calculation, reconciliation, isolation.

Synthetic workbook only (fictional data). The opt-in test against the real workbook lives in
test_realimport_real_workbook.py and asserts aggregates only.
"""

from __future__ import annotations

import json
import re
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.realimport import calc
from app.realimport import profile as P
from app.realimport.inspector import WorkbookError
from app.realimport.normalize import decimal_text, fold_text, parse_decimal
from app.realimport.pseudo import PiiLeak, assert_clean, pseudonym
from app.realimport.synthetic import build_synthetic_workbook

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
BASE = "/api/v1/ri"
RAW_MARKERS = ("Demo Seller", "Fictional", "9000001", "5000100")  # fictional raw values that must never be served


@pytest.fixture(scope="module")
def synthetic() -> tuple[bytes, dict]:
    return build_synthetic_workbook()


def upload(client, headers, raw: bytes, name: str = "synthetic.xlsx"):
    return client.post(f"{BASE}/workbooks", files={"file": (name, raw, XLSX)}, headers=headers)


def post(client, headers, path: str, body: dict | None = None):
    return client.post(f"{BASE}{path}", json=body or {}, headers=headers)


def pipeline_to_confirmed(client, headers, raw: bytes) -> str:
    batch_id = upload(client, headers, raw).json()["batch"]["id"]
    assert post(client, headers, f"/batches/{batch_id}/validate").status_code == 200
    assert post(client, headers, f"/batches/{batch_id}/confirm").status_code == 200
    return batch_id


def table_counts(settings: Settings, tables: tuple[str, ...]) -> dict[str, int]:
    conn = sqlite3.connect(settings.db_path)
    try:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}  # noqa: S608
    finally:
        conn.close()


RI_TABLES = ("ri_workbooks", "ri_import_batches", "ri_raw_rows", "ri_sales_facts", "ri_visitor_assignments", "ri_customers",
             "ri_employees", "ri_mapping_issues", "ri_targets", "ri_workbook_references", "ri_calc_runs", "ri_calc_results",
             "ri_calc_result_inputs", "ri_reconciliation_checks")


# ------------------------------------------------------------------------------ normalisation
def test_folding_matches_arabic_and_persian_letters() -> None:
    assert fold_text("كرج") == fold_text("کرج")  # Karaj: Arabic kaf vs Persian kaf (audit defect 1)
    assert fold_text("لاين يک") == fold_text("لاین یک")
    assert fold_text("می‌شود") == fold_text("می شود")  # ZWNJ behaves like a space
    assert fold_text("۱۲۳") == "123"
    assert fold_text(None) == ""


def test_decimals_keep_fractions_and_negatives() -> None:
    assert parse_decimal(5.833333333333333) == Decimal("5.833333333333333")
    assert parse_decimal("-44") == Decimal(-44)
    assert parse_decimal("۱٬۲۰۰") == Decimal(1200)
    assert parse_decimal("#N/A") is None and parse_decimal(True) is None and parse_decimal("abc") is None
    assert decimal_text(Decimal("12.500")) == "12.5" and decimal_text(Decimal("-0")) == "0"


def test_line_codes_and_manager_line_groups() -> None:
    assert P.line_code("لاين يک") == "1" and P.line_code("لاین دو") == "2" and P.line_code("لاين G") == "G"
    assert P.line_code(1.0) == "1" and P.line_code("p") == "P"
    assert P.line_group_codes(" 1-2") == {"1", "2"} and P.line_group_codes("G") == {"G"} and P.line_group_codes(2) == {"2"}


def test_pseudonyms_are_deterministic_keyed_and_leak_guarded() -> None:
    a = pseudonym("visitor", "x", "key-1")
    assert a == pseudonym("visitor", "x", "key-1") and a != pseudonym("visitor", "x", "key-2") and a.startswith("V-")
    assert pseudonym("employee", "x", "key-1").startswith("E-") and pseudonym("customer", "x", "k").startswith("C-")
    with pytest.raises(PiiLeak):
        assert_clean({"a": ["1-Real Name_R"]}, ["1-Real Name_R"])
    with pytest.raises(PiiLeak):
        assert_clean({"a": "owner 1-Real Name_R here"}, ["1-Real Name_R"])
    assert_clean({"count": 27946, "x": "27946.5"}, ["27946"])  # numeric codes only match whole string values


def test_calculation_error_for_invalid_target() -> None:
    with pytest.raises(calc.CalcError) as exc:
        calc.achievement_ladder({"thresholds": ["1"]}, quantity=Decimal(5), target=Decimal(0), extra={})
    assert exc.value.code == "TARGET_INVALID"
    with pytest.raises(calc.CalcError) as exc:
        calc.achievement_ladder({"thresholds": ["1"]}, quantity=Decimal(5), target=Decimal(1), extra={"steps": [None]})
    assert exc.value.code == "STEP_AMOUNT_MISSING"
    ok = calc.achievement_ladder({"thresholds": ["0.97", "1.12"]}, quantity=Decimal(100), target=Decimal(100), extra={"steps": ["10", "20"]})
    assert ok["reward"] == Decimal(10) and ok["step"] == 1
    assert calc.achievement_ladder({"thresholds": ["0.97"]}, quantity=Decimal(50), target=Decimal(100), extra={})["reward"] == 0


# ---------------------------------------------------------------------------------- isolation
def test_generated_workbooks_are_byte_identical_across_calls() -> None:
    import time

    from app import kiloos_demo

    first = (build_synthetic_workbook()[0], kiloos_demo.sample_workbook_bytes())
    time.sleep(1.1)  # openpyxl stamps wall-clock seconds; deterministic_xlsx must neutralise that
    assert first == (build_synthetic_workbook()[0], kiloos_demo.sample_workbook_bytes())


def test_feature_flag_off_means_no_routes(client: TestClient) -> None:
    assert client.get(f"{BASE}/meta").status_code == 404


def test_migration_only_adds_prefixed_tables() -> None:
    sql = (Path(__file__).resolve().parent.parent / "db" / "migrations" / "0008_real_import_spike.sql").read_text(encoding="utf-8")
    assert "ALTER TABLE" not in sql.upper() and "DROP " not in sql.upper()
    names = re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", sql)
    assert names and all(n.startswith("ri_") for n in names)
    rule_sets_ddl = sql.split("CREATE TABLE IF NOT EXISTS ri_rule_sets")[1].split(");")[0]
    assert "'APPROVED'" not in rule_sets_ddl  # the schema cannot even store an approved rule


def test_demo_tables_untouched_by_full_flow(ri, ri_settings: Settings, synthetic) -> None:
    client, headers = ri
    guarded = ("sales_records", "sales_imports", "score_events", "point_transactions", "point_wallets", "game_progress")
    before = table_counts(ri_settings, guarded)
    batch_id = pipeline_to_confirmed(client, headers, synthetic[0])
    rule_id = client.get(f"{BASE}/rules", headers=headers).json()["rules"][0]["id"]
    assert post(client, headers, f"/batches/{batch_id}/runs", {"rule_set_id": rule_id}).status_code == 201
    assert table_counts(ri_settings, guarded) == before


def test_original_workbook_is_stored_by_hash_and_never_changed(ri, ri_settings: Settings, synthetic) -> None:
    client, headers = ri
    body = upload(client, headers, synthetic[0]).json()
    stored = (ri_settings.real_import_dir / f"{body['workbook']['sha256']}.xlsx")
    assert stored.read_bytes() == synthetic[0]
    pipeline_to_confirmed(client, headers, synthetic[0])
    assert stored.read_bytes() == synthetic[0]


# ------------------------------------------------------------------------------------ pipeline
def test_upload_inspects_workbook_and_flags_synthetic_origin(ri, synthetic) -> None:
    client, headers = ri
    response = upload(client, headers, synthetic[0])
    assert response.status_code == 201
    body = response.json()
    assert body["workbook"]["data_origin"] == "synthetic" and body["batch"]["data_origin"] == "synthetic"
    assert body["batch"]["period"] == {"calendar": "jalali", "year": 1405, "month": 6, "label": "شهریور"}
    roles = body["workbook"]["inspection"]["roles"]
    assert roles["sales_primary"]["found"] and not roles["sales_primary"]["columns_missing"]
    assert roles["roster"]["found"] and roles["manager_efes"]["found"]
    assert {s["name"] for s in body["workbook"]["inspection"]["sheets"]} >= {"فروش", "SalesData", "تیم"}


def test_rejects_non_xlsx_and_corrupt_files(ri) -> None:
    client, headers = ri
    assert upload(client, headers, b"hello", "notes.txt").json()["error"]["code"] == "INVALID_FILE_TYPE"
    assert upload(client, headers, b"not a zip", "bad.xlsx").json()["error"]["code"] == "INVALID_WORKBOOK"
    assert upload(client, headers, b"", "empty.xlsx").json()["error"]["code"] == "EMPTY_FILE"


def test_validation_counts_rejections_duplicates_and_mappings(ri, synthetic) -> None:
    client, headers = ri
    raw, manifest = synthetic
    batch_id = upload(client, headers, raw).json()["batch"]["id"]
    batch = post(client, headers, f"/batches/{batch_id}/validate").json()["batch"]
    assert batch["status"] == "validated"
    sheets = batch["counts"]["sheets"]
    primary = sheets["sales_primary"]
    assert primary["rows_read"] == manifest["rows_primary"] and primary["valid"] == manifest["valid_primary"]
    assert primary["rejected"] == manifest["rejected_primary"]
    assert primary["rejected_by_code"] == {"E_PERIOD": 1, "E_REQUIRED": 1, "E_NET": 1}
    assert primary["duplicate_keys"] == 1 and primary["duplicate_key_rows"] == manifest["duplicate_key_rows"]
    assert sheets["sales_derived"]["rows_read"] == manifest["rows_derived"]
    issues = batch["counts"]["issues"]
    assert issues["visitor_not_in_roster"] == 1 and issues["employee_code_missing"] == 1
    assert issues["shared_personnel_code"] == 2 and issues["head_missing"] == 2
    assert issues["factor_header_swapped"] == 1 and issues["factor_duplicate_code"] == 1
    assert issues["branch_spelling_variants"] == 1  # Karaj spelled with Arabic and Persian kaf
    assert batch["counts"]["roster"]["employees_with_multiple_assignments"] == 2  # employee != visitor assignment


def test_fractional_and_negative_cartons_are_preserved(ri, ri_settings: Settings, synthetic) -> None:
    client, headers = ri
    pipeline_to_confirmed(client, headers, synthetic[0])
    conn = sqlite3.connect(ri_settings.db_path)
    try:
        nets = [r[0] for r in conn.execute("SELECT net_cartons FROM ri_sales_facts WHERE source_sheet = 'فروش' AND status = 'valid'")]
    finally:
        conn.close()
    assert any("." in n and Decimal(n) % 1 != 0 for n in nets) and any(Decimal(n) < 0 for n in nets)
    assert "5.833333333333333" in nets  # exact, not binary-float noise or rounded


def test_original_source_values_survive_next_to_normalised_keys(ri, ri_settings: Settings, synthetic) -> None:
    client, headers = ri
    pipeline_to_confirmed(client, headers, synthetic[0])
    conn = sqlite3.connect(ri_settings.db_path)
    try:
        branch = conn.execute("SELECT norm_key, source_value, variants_json FROM ri_branches WHERE norm_key = ?", (fold_text("کرج"),)).fetchone()
        raw = conn.execute("SELECT raw_json FROM ri_raw_rows WHERE sheet = 'فروش' AND raw_json LIKE '%كرج%' LIMIT 1").fetchone()
    finally:
        conn.close()
    assert branch is not None and len(json.loads(branch[2])) == 2  # both spellings recorded
    assert raw is not None  # the raw layer still holds the Arabic-kaf source value untouched


def test_preview_shows_normalised_pseudonymised_rows(ri, synthetic) -> None:
    client, headers = ri
    batch_id = upload(client, headers, synthetic[0]).json()["batch"]["id"]
    assert client.get(f"{BASE}/batches/{batch_id}/preview", headers=headers).json()["valid_rows"] == []  # nothing before validation
    post(client, headers, f"/batches/{batch_id}/validate")
    preview = client.get(f"{BASE}/batches/{batch_id}/preview", headers=headers).json()
    assert len(preview["valid_rows"]) == 15 and len(preview["rejected_rows"]) >= 3
    row = preview["valid_rows"][0]
    assert row["visitor"].startswith("V-") and row["customer"].startswith("C-") and row["sku"].startswith("AVE_")
    assert {e["code"] for r in preview["rejected_rows"] for e in r["errors"]} >= {"E_PERIOD", "E_REQUIRED", "E_NET"}
    assert preview["issues"]


def test_confirm_requires_validation(ri, synthetic) -> None:
    client, headers = ri
    batch_id = upload(client, headers, synthetic[0]).json()["batch"]["id"]
    response = post(client, headers, f"/batches/{batch_id}/confirm")
    assert response.status_code == 409 and response.json()["error"]["code"] == "BATCH_NOT_VALIDATED"


# ----------------------------------------------------------------------------- idempotency
def test_repeating_the_import_creates_no_duplicates(ri, ri_settings: Settings, synthetic) -> None:
    client, headers = ri
    batch_id = pipeline_to_confirmed(client, headers, synthetic[0])
    rule_id = client.get(f"{BASE}/rules", headers=headers).json()["rules"][0]["id"]
    first_run = post(client, headers, f"/batches/{batch_id}/runs", {"rule_set_id": rule_id}).json()
    before = table_counts(ri_settings, RI_TABLES)

    again = upload(client, headers, synthetic[0])
    assert again.status_code == 200 and again.json()["replayed"] is True and again.json()["batch"]["id"] == batch_id
    assert post(client, headers, f"/batches/{batch_id}/validate").json()["replayed"] is True
    assert post(client, headers, f"/batches/{batch_id}/confirm").json()["replayed"] is True
    second_run = post(client, headers, f"/batches/{batch_id}/runs", {"rule_set_id": rule_id})
    assert second_run.status_code == 200 and second_run.json()["replayed"] is True
    assert second_run.json()["run"]["id"] == first_run["run"]["id"]
    assert table_counts(ri_settings, RI_TABLES) == before


def test_different_period_config_is_a_separate_editable_batch(ri, ri_settings: Settings, synthetic) -> None:
    client, headers = ri
    first = upload(client, headers, synthetic[0]).json()
    wb_id = first["workbook"]["id"]
    other = post(client, headers, "/batches", {"workbook_id": wb_id, "config": {"period": {"year": 1405, "month": 7}}})
    assert other.status_code == 201 and other.json()["batch"]["id"] != first["batch"]["id"]
    assert other.json()["batch"]["period"]["label"] == "مهر"
    validated = post(client, headers, f"/batches/{other.json()['batch']['id']}/validate").json()["batch"]
    # every row says Shahrivar, so with the configured period Mehr they are all rejected (never silently accepted)
    assert validated["counts"]["sheets"]["sales_primary"]["valid"] == 1  # only the row labelled «مهر»
    bad = post(client, headers, "/batches", {"workbook_id": wb_id, "config": {"period": {"year": 1405, "month": 13}}})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "INVALID_CONFIG"


# ------------------------------------------------------------------------------------ privacy
def test_no_raw_personal_value_in_any_api_response(ri, synthetic) -> None:
    client, headers = ri
    batch_id = pipeline_to_confirmed(client, headers, synthetic[0])
    rule_id = client.get(f"{BASE}/rules", headers=headers).json()["rules"][0]["id"]
    run = post(client, headers, f"/batches/{batch_id}/runs", {"rule_set_id": rule_id}).json()["run"]
    results = client.get(f"{BASE}/runs/{run['id']}", headers=headers).json()["results"]
    paths = ["/meta", "/workbooks", "/batches", f"/batches/{batch_id}", f"/batches/{batch_id}/preview", f"/batches/{batch_id}/mappings",
             "/rules", f"/batches/{batch_id}/runs", f"/runs/{run['id']}", f"/results/{results[0]['id']}/inputs?limit=500",
             f"/batches/{batch_id}/reconciliation", f"/batches/{batch_id}/summary", "/decisions"]
    for path in paths:
        response = client.get(f"{BASE}{path}", headers=headers)
        assert response.status_code == 200, path
        for marker in RAW_MARKERS:
            assert marker not in response.text, (path, marker)
    mappings = client.get(f"{BASE}/batches/{batch_id}/mappings", headers=headers).json()
    assert all(a["visitor"].startswith("V-") for a in mappings["assignments"])
    assert any(a["employee"] and a["employee"].startswith("E-") for a in mappings["assignments"])


def test_endpoints_require_admin(client: TestClient, ri_settings: Settings) -> None:
    with TestClient(create_app(ri_settings)) as anonymous:
        assert anonymous.get(f"{BASE}/meta").status_code == 401
        assert anonymous.post(f"{BASE}/workbooks").status_code in (401, 403)


# ------------------------------------------------------------------------------- calculation
def test_run_requires_confirmed_batch(ri, synthetic) -> None:
    client, headers = ri
    batch_id = upload(client, headers, synthetic[0]).json()["batch"]["id"]
    post(client, headers, f"/batches/{batch_id}/validate")
    rule_id = client.get(f"{BASE}/rules", headers=headers).json()["rules"][0]["id"]
    response = post(client, headers, f"/batches/{batch_id}/runs", {"rule_set_id": rule_id})
    assert response.status_code == 409 and response.json()["error"]["code"] == "BATCH_NOT_CONFIRMED"


def test_calculation_is_traceable_and_labelled_proposed(ri, ri_settings: Settings, synthetic) -> None:
    client, headers = ri
    raw, manifest = synthetic
    batch_id = pipeline_to_confirmed(client, headers, raw)
    rule = client.get(f"{BASE}/rules", headers=headers).json()["rules"][0]
    assert rule["status"] == "PROPOSED" and rule["code"] == "MGR_EFES_LADDER_PROPOSED" and rule["version"] == 1
    run = post(client, headers, f"/batches/{batch_id}/runs", {"rule_set_id": rule["id"]}).json()["run"]
    detail = client.get(f"{BASE}/runs/{run['id']}", headers=headers).json()
    results = detail["results"]
    assert len(results) == manifest["manager_rows"] and run["error_count"] == 0
    for r in results:  # every required traceability field is present
        assert r["run_id"] == run["id"] and r["import_batch_id"] == batch_id and r["rule_version"] == 1
        assert r["brand"] == "efes" and r["period"] == {"calendar": "jalali", "year": 1405, "month": 6}
        assert r["org_level"] == "branch_manager" and r["entity"] and r["calculated_at"]
        assert r["rule_status"] == "PROPOSED" and r["input_quantity"] is not None and r["target"] is not None
        assert r["achievement"] is not None and r["reward_rials"] is not None
        assert r["explain"]["target_status"] == "UNCONFIRMED" and r["explain"]["carton_basis"] == "sales_primary:فروش"
    # trace: each result links to its exact input facts and the inputs add up to the stored quantity
    for r in results:
        inputs = client.get(f"{BASE}/results/{r['id']}/inputs?limit=500", headers=headers).json()
        assert inputs["rule"]["version"] == 1 and inputs["total"] == r["explain"]["facts"]
        assert sum(Decimal(i["net_cartons"]) for i in inputs["inputs"]) == Decimal(r["input_quantity"])
        assert all(i["source_sheet"] == "فروش" for i in inputs["inputs"])
    # rewards equal the independent ladder applied to the same figures, except the one hand-adjusted row
    expected = manifest["expected_rewards"]
    differing = [r for r in results if Decimal(r["reward_rials"]) != Decimal(expected[_pretty(r["entity_key"], expected)])]
    assert len(differing) <= manifest["adjusted_manager_rows"]


def _pretty(entity_key: str, expected: dict[str, int]) -> str:
    branch, _, group = entity_key.partition("|")
    return next(k for k in expected if fold_text(k.split("|")[0]) == branch and k.split("|")[1] == group)


def test_rule_sets_can_never_be_approved_through_the_api(ri) -> None:
    client, headers = ri
    body = {"code": "X_RULE", "rule_type": "achievement_ladder", "org_level": "branch_manager", "brand": "efes",
            "params": {"thresholds": ["0.9", "1.1"]}, "status": "APPROVED"}
    denied = post(client, headers, "/rules", body)
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "RULE_STATUS_FORBIDDEN"
    ok = post(client, headers, "/rules", {**body, "status": "UNCONFIRMED"})
    assert ok.status_code == 201 and ok.json()["rule"]["version"] == 1
    assert post(client, headers, "/rules", {**body, "status": "PROPOSED"}).json()["rule"]["version"] == 2  # versions, never edits
    assert post(client, headers, "/rules", {**body, "status": "PROPOSED", "params": {"thresholds": ["2", "1"]}}).status_code == 422


def test_schema_refuses_an_approved_rule_set(ri, ri_settings: Settings) -> None:
    conn = sqlite3.connect(ri_settings.db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO ri_rule_sets (code, version, rule_type, org_level, brand_code, params_json, status, created_at) "
                "VALUES ('Z', 1, 'achievement_ladder', 'branch_manager', 'efes', '{}', 'APPROVED', 'now')")
    finally:
        conn.close()


def test_changed_rule_params_create_a_distinct_run(ri, synthetic) -> None:
    client, headers = ri
    batch_id = pipeline_to_confirmed(client, headers, synthetic[0])
    seed = client.get(f"{BASE}/rules", headers=headers).json()["rules"][0]
    v2 = post(client, headers, "/rules", {"code": seed["code"], "rule_type": "achievement_ladder", "org_level": "branch_manager",
                                          "brand": "efes", "params": {"thresholds": ["0.5", "1.0"]}, "status": "PROPOSED"}).json()["rule"]
    run1 = post(client, headers, f"/batches/{batch_id}/runs", {"rule_set_id": seed["id"]}).json()["run"]
    run2 = post(client, headers, f"/batches/{batch_id}/runs", {"rule_set_id": v2["id"]}).json()["run"]
    assert run1["id"] != run2["id"] and run1["rule"]["version"] == 1 and run2["rule"]["version"] == 2
    # history is newest-first even when both runs were created within the same second (stable tiebreaker)
    listed = client.get(f"{BASE}/batches/{batch_id}/runs", headers=headers).json()["runs"]
    assert [r["id"] for r in listed][:2] == [run2["id"], run1["id"]]


# ----------------------------------------------------------------------------- reconciliation
def test_reconciliation_explains_the_rounding_gap_instead_of_hiding_it(ri, ri_settings: Settings, synthetic) -> None:
    client, headers = ri
    batch_id = pipeline_to_confirmed(client, headers, synthetic[0])
    body = client.get(f"{BASE}/batches/{batch_id}/reconciliation", headers=headers).json()
    checks = {c["check_code"]: c for c in body["checks"]}
    net = checks["IMP-NET"]
    assert net["status"] == "explained" and Decimal(net["abs_variance"]) > 0  # variance is shown, not rounded away
    conn = sqlite3.connect(ri_settings.db_path)
    try:
        sums = {s: sum(Decimal(r[0]) for r in conn.execute(
            "SELECT net_cartons FROM ri_sales_facts WHERE source_sheet = ? AND status = 'valid'", (s,))) for s in ("فروش", "SalesData")}
    finally:
        conn.close()
    assert Decimal(net["abs_variance"]) == abs(sums["فروش"] - sums["SalesData"])
    assert Decimal(net["pct_variance"]) > 0
    assert net["detail"]["unexplained"] == 0 and net["detail"]["differing_keys"] == net["detail"]["explained_by_rounding"] > 0
    assert "Int64" in net["explanation"]
    assert checks["IMP-GROSS"]["status"] == "match" and checks["IMP-KEYS"]["status"] == "match"
    assert checks["IMP-DUPKEYS-sales_primary"]["duplicates"] == 1 and checks["IMP-DUPKEYS-sales_primary"]["status"] == "warning"
    assert checks["IMP-MAPPINGS"]["unresolved"] == 5 and checks["IMP-MAPPINGS"]["status"] == "warning"
    assert checks["IMP-ROWS-sales_primary"]["matched"] == 86 and checks["IMP-ROWS-sales_primary"]["status"] == "warning"  # 3 rejected rows
    assert body["overall"] == "warning" and "ONLY where a check says 'match'" in body["claim"]


def test_run_reconciliation_flags_the_hand_adjusted_figure(ri, synthetic) -> None:
    client, headers = ri
    raw, manifest = synthetic
    batch_id = pipeline_to_confirmed(client, headers, raw)
    rule_id = client.get(f"{BASE}/rules", headers=headers).json()["rules"][0]["id"]
    run = post(client, headers, f"/batches/{batch_id}/runs", {"rule_set_id": rule_id}).json()["run"]
    checks = {c["check_code"]: c for c in client.get(f"{BASE}/runs/{run['id']}", headers=headers).json()["reconciliation"]}
    sales = checks["RUN-SALES"]
    assert sales["status"] == "warning" and sales["detail"]["entities_differing"] == manifest["adjusted_manager_rows"]
    assert sales["matched"] == manifest["manager_rows"] - manifest["adjusted_manager_rows"]
    assert abs(Decimal(sales["abs_variance"]) - Decimal("3.5")) < Decimal("0.001")  # the one hand-adjusted figure
    assert "RUN-REWARD" in checks
    summary = client.get(f"{BASE}/batches/{batch_id}/summary", headers=headers).json()
    efes = next(b for b in summary["brands"] if b["brand"] == "efes")
    assert efes["levels"][0]["org_level"] == "branch_manager" and efes["levels"][0]["rule"]["status"] == "PROPOSED"


def test_general_manager_level_reports_a_calculation_error_not_a_guess(ri, synthetic) -> None:
    client, headers = ri
    batch_id = pipeline_to_confirmed(client, headers, synthetic[0])
    rules = {r["code"]: r for r in client.get(f"{BASE}/rules", headers=headers).json()["rules"]}
    general = rules["MGR_GENERAL_EFES_LADDER_PROPOSED"]
    assert general["status"] == "PROPOSED" and general["org_level"] == "general_manager"
    run = post(client, headers, f"/batches/{batch_id}/runs", {"rule_set_id": general["id"]}).json()["run"]
    assert run["result_count"] == 1 and run["error_count"] == 1
    result = client.get(f"{BASE}/runs/{run['id']}", headers=headers).json()["results"][0]
    # fixture has no P/A sales lines: the entity cannot be calculated, and says so instead of returning 0
    assert result["result_status"] == "error" and "LINE_GROUP_UNMAPPED" in result["error"]
    assert result["achievement"] is None and result["reward_rials"] is None
    net = client.get(f"{BASE}/batches/{batch_id}/reconciliation", headers=headers).json()["checks"]
    assert next(c for c in net if c["check_code"] == "IMP-NET")["detail"]["rounding_mode"] in {"half_away_from_zero", "half_to_even"}


def test_decision_register_is_complete_and_never_claims_approval(ri) -> None:
    client, headers = ri
    items = client.get(f"{BASE}/decisions", headers=headers).json()["decisions"]
    assert len(items) >= 14
    assert all(i["question"] and i["impact"] and i["status"] and i["approver"] for i in items)
    assert not any(i["status"] == "APPROVED" for i in items)
    assert next(i for i in items if i["id"] == "BD-01")["status"] == "CONFIRMED"  # period Shahrivar 1405 confirmed by the business
    assert "carton" in next(i for i in items if i["id"] == "BD-05")["question"].lower()


def test_workbook_error_type_is_exposed_for_api_clients() -> None:
    assert WorkbookError("X", "m").status_code == 422

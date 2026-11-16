"""Opt-in: the REAL operational workbook, read-only. Asserts aggregates only (no personal data).

Skipped unless KILOOS_REAL_WORKBOOK points at the file, e.g.

    docker run --rm -v <path>\\workbook.xlsx:/wb/workbook.xlsx:ro -e KILOOS_REAL_WORKBOOK=/wb/workbook.xlsx \\
        kiloos-spike-test pytest tests/test_realimport_real_workbook.py

Expected figures come from the audit (REAL-WORKBOOK-AUDIT.md §D, §E.4); they are facts about the file,
not approved business numbers.
"""

from __future__ import annotations

import hashlib
import os
from decimal import Decimal
from pathlib import Path

import pytest

from app.config import Settings
from app.realimport import cli

PATH = os.getenv("KILOOS_REAL_WORKBOOK")
WORKBOOK_SHA256 = "f9f3a8d80ca2b6805088aea83e837d593f24aac61be0dbd9bb2cde809384e5b5"

pytestmark = pytest.mark.skipif(not PATH or not Path(PATH or "").is_file(), reason="KILOOS_REAL_WORKBOOK not set")


@pytest.fixture(scope="module")
def result(tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp = tmp_path_factory.mktemp("real")
    settings = Settings(env="test", db_path=tmp / "ri.db", evidence_dir=tmp / "ev", secret="test-secret-that-is-long-enough-1234567890",
                        real_import_enabled=True, real_import_dir=tmp / "wb", pseudonym_key="test-pseudonym-key-1234567890")
    return cli.run_import(Path(PATH), settings)


def checks(result: dict) -> dict:
    return {c["check_code"]: c for c in result["reconciliation"]}


def test_workbook_identity_is_the_audited_file() -> None:
    assert hashlib.sha256(Path(PATH).read_bytes()).hexdigest() == WORKBOOK_SHA256


def test_row_counts_keys_and_totals_match_the_audit(result: dict) -> None:
    sheets = result["batch"]["counts"]["sheets"]
    for role in ("sales_primary", "sales_derived"):
        s = sheets[role]
        assert (s["rows_read"], s["valid"], s["rejected"]) == (27946, 27946, 0)
        assert (s["distinct_keys"], s["duplicate_keys"], s["invoice_count"]) == (27941, 5, 25141)
        assert Decimal(s["gross_cartons"]).quantize(Decimal("0.01")) == Decimal("139722.75")
    assert Decimal(sheets["sales_primary"]["net_cartons"]).quantize(Decimal("0.001")) == Decimal("112244.583")
    assert Decimal(sheets["sales_derived"]["net_cartons"]) == Decimal(112189)
    assert result["workbook"]["origin"] == "real"


def test_roster_keeps_employee_and_visitor_assignment_separate(result: dict) -> None:
    roster = result["batch"]["counts"]["roster"]
    assert roster["assignments"] == 1006 and roster["employees_with_multiple_assignments"] == 76


def test_the_55_583_carton_gap_is_shown_and_verified_as_rounding(result: dict) -> None:
    net = checks(result)["IMP-NET"]
    assert net["status"] == "explained"
    assert Decimal(net["abs_variance"]).quantize(Decimal("0.001")) == Decimal("55.583")
    assert net["detail"]["differing_keys"] == 294 and net["detail"]["unexplained"] == 0
    assert net["detail"]["rounding_mode"] == "half_to_even"
    assert checks(result)["IMP-GROSS"]["status"] == "match" and checks(result)["IMP-KEYS"]["status"] == "match"


def test_calculation_runs_cover_all_manager_rows_and_reproduce_reported_rewards(result: dict) -> None:
    runs = {r["org_level"]: r for r in result["runs"]}
    assert runs["branch_manager"]["result_count"] == 47 and runs["general_manager"]["result_count"] == 2
    assert all(r["error_count"] == 0 and r["rule"]["status"] == "PROPOSED" for r in runs.values())
    assert Decimal(runs["branch_manager"]["totals"]["indicative_reward_rials"]) == 2_280_000_000
    assert Decimal(runs["general_manager"]["totals"]["indicative_reward_rials"]) == 280_000_000  # 2.56 B together (audit §E.4)
    rewards = [c for c in result["reconciliation"] if c["check_code"] == "RUN-REWARD"]
    assert len(rewards) == 2 and all(c["status"] == "match" for c in rewards)


def test_input_sales_do_not_fully_reproduce_and_say_so(result: dict) -> None:
    sales = [c for c in result["reconciliation"] if c["check_code"] == "RUN-SALES"]
    assert sales and all(c["status"] == "warning" for c in sales)  # hand-adjusted workbook figures: reported, never forced
    branch = next(c for c in sales if c["matched"] == 31)
    assert branch["detail"]["entities_differing"] == 16


def test_rerunning_the_import_is_a_no_op(result: dict, tmp_path: Path) -> None:
    again = cli.run_import(Path(PATH), Settings(env="test", db_path=tmp_path / "ri.db", evidence_dir=tmp_path / "ev",
                                                secret="test-secret-that-is-long-enough-1234567890", real_import_enabled=True,
                                                real_import_dir=tmp_path / "wb", pseudonym_key="test-pseudonym-key-1234567890"))
    twice = cli.run_import(Path(PATH), Settings(env="test", db_path=tmp_path / "ri.db", evidence_dir=tmp_path / "ev",
                                                secret="test-secret-that-is-long-enough-1234567890", real_import_enabled=True,
                                                real_import_dir=tmp_path / "wb", pseudonym_key="test-pseudonym-key-1234567890"))
    assert again["batch"]["id"] == twice["batch"]["id"] and twice["batch"]["replayed"] is True
    assert all(r["replayed"] for r in twice["runs"]) and twice["workbook"]["replayed"] is True

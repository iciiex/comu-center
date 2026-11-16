"""Workbook profile: where things are, how headers are matched, and the editable import config.

Nothing here is a business rule. It only describes the *layout* of the operational workbook
(audit §A/§B) so the importer is configuration-driven instead of hard-coded. Header matching is
exact-after-folding first, then prefix (the real headers carry unit suffixes such as
"(کارتن)" and stray spaces).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.jalali import JALALI_MONTHS
from app.realimport.normalize import fold_text, header_key

# Sheet roles -> default sheet names (matched after folding/trimming).
DEFAULT_SHEETS: dict[str, str] = {
    "sales_primary": "فروش",          # base extract, fractional cartons
    "sales_derived": "SalesData",     # Power Query output, integer-cast net cartons
    "roster": "تیم",                   # master roster (hierarchy source)
    "box_conversion": "ضرایب کارتنی",   # carton conversion factors
    "branch_groups": "گروه شعب",       # hand-maintained branch groups
    "customer_groups": "CustomerGroup",
    "manager_efes": "مدیر افس",        # EFES branch managers: targets + workbook-reported results
}
OPTIONAL_ROLES = {"sales_derived", "box_conversion", "branch_groups", "customer_groups", "manager_efes", "roster"}

# canonical field -> accepted header keys (folded). Order = priority.
SALES_FIELDS: dict[str, tuple[str, ...]] = {
    "branch": ("شعبه پخش",),
    "month": ("ماه",),
    "visitor": ("ویزیتور",),
    "customer_group": ("گروه مشتری",),
    "sales_line": ("کانال فروش",),
    "customer": ("کد مشتری",),
    "brand": ("برند",),
    "sku_name": ("نام کالا",),
    "sku_code": ("کد کالا",),
    "gross": ("کارتن ناخالص منهای برگشتی",),
    "net": ("کارتن خالص منهای برگشتی",),
    "invoice_count": ("تعداد فاکتور",),
}
SALES_REQUIRED = ("branch", "month", "visitor", "customer_group", "sales_line", "customer", "brand", "sku_code", "net")
# The business key (audit §D): one row per branch × month × visitor × customer group × sales line
# × customer × brand × SKU. There is no invoice id.
BUSINESS_KEY_FIELDS = ("branch", "month", "visitor", "customer_group", "sales_line", "customer", "brand", "sku_code")

ROSTER_FIELDS: dict[str, tuple[str, ...]] = {
    "branch": ("شعبه",),
    "visitor": ("ویزیتور",),
    "sales_line": ("لاین فروش",),
    "seller_type": ("نوع فروشنده",),
    "st": ("st",),
    "personnel_code": ("کد پرسنلی ویزیتور",),
    "hire_date": ("تاریخ استخدام",),
    "supervisor_code": ("کد پرسنلی سرپرست",),
    "head_code": ("کد پرسنلی رئیس",),
    "type_letter": ("نوع",),
}
ROSTER_REQUIRED = ("branch", "visitor", "sales_line", "personnel_code")
# Name columns exist in the roster but are deliberately never read (data minimisation).

FACTOR_FIELDS = {"brand": ("برند",), "col_a": ("کد کالا",), "col_b": ("نام کالا",), "factor": ("ضریب کارتن",)}
BRANCH_GROUP_FIELDS = {"branch": ("شعبه",), "group1": ("گروه",), "group2": ("گروه 2",)}
CUSTOMER_GROUP_FIELDS = {"customer_group": ("گروه مشتری",), "main_group": ("گروه اصلی",)}
# Manager sheet: header row 3, data from row 4. Name columns (مدیر, مدیرکل, معاون منطقه) are never read.
MANAGER_FIELDS = {
    "month": ("ماه",), "brand": ("برند",), "branch": ("شعبه",), "line": ("لاین",), "level": ("سطح",),
    "target": ("هدف ماه",), "definitive_sales": ("فروش قطعی",), "achievement": ("تحقق قطعی",),
    "relief": ("ارفاق",), "reward": ("مبلغ",),
    "step1": ("پله 1",), "step2": ("پله 2",), "step3": ("پله 3",), "step4": ("پله 4",),
}
MANAGER_HEADER_ROW = 3

# Persian main customer group labels (audit §E.1). Mapping status stays UNCONFIRMED.
MAIN_GROUPS = {"خرده": "retail", "عمده": "wholesale", "هورکا": "horeca"}
# Brand spellings used on report sheets vs the sales extract (UNCONFIRMED convenience mapping).
BRAND_ALIASES = {"افس": "efes", "ماتادور": "matador"}

MONTH_NUMBERS = {fold_text(name): i for i, name in enumerate(JALALI_MONTHS, start=1)}

SYNTHETIC_MARKER_SHEET = "SYNTHETIC-FIXTURE"


def default_config(year: int = 1405, month: int = 6) -> dict[str, Any]:
    """Explicit, editable import configuration. Period default = confirmed Shahrivar 1405."""
    return {
        "period": {"calendar": "jalali", "year": year, "month": month},
        "sheets": dict(DEFAULT_SHEETS),
        "carton_basis": "sales_primary",        # which sheet feeds calculations (BD-05)
        "duplicate_key_policy": "keep_flagged",  # keep every row, ordinal + warning (BD-07)
    }


def normalise_config(config: dict[str, Any] | None) -> dict[str, Any]:
    base = default_config()
    if config:
        period = {**base["period"], **config.get("period", {})}
        if period.get("calendar") != "jalali":
            raise ValueError("Only the Jalali calendar is supported.")
        year, month = int(period["year"]), int(period["month"])
        if not (1300 <= year <= 1500 and 1 <= month <= 12):
            raise ValueError("Period must be a valid Jalali year (1300-1500) and month (1-12).")
        base["period"] = {"calendar": "jalali", "year": year, "month": month}
        base["sheets"] = {**base["sheets"], **config.get("sheets", {})}
        for key in ("carton_basis", "duplicate_key_policy"):
            if key in config:
                base[key] = config[key]
    if base["carton_basis"] not in {"sales_primary", "sales_derived"}:
        raise ValueError("carton_basis must be sales_primary or sales_derived.")
    if base["duplicate_key_policy"] != "keep_flagged":
        raise ValueError("Only duplicate_key_policy=keep_flagged is implemented.")
    return base


def config_hash(config: dict[str, Any]) -> str:
    canonical = json.dumps(config, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def match_headers(header_cells: list[Any], fields: dict[str, tuple[str, ...]]) -> dict[str, int]:
    """Map canonical field -> column index. Exact folded match wins over prefix match."""
    keys = [header_key(c) for c in header_cells]
    found: dict[str, int] = {}
    for field, aliases in fields.items():
        wanted = [header_key(a) for a in aliases]
        hit = next((i for i, k in enumerate(keys) if k in wanted and i not in found.values()), None)
        if hit is None:
            hit = next(
                (i for i, k in enumerate(keys) if i not in found.values() and any(k.startswith(w + " ") for w in wanted)),
                None,
            )
        if hit is not None:
            found[field] = hit
    return found


def line_code(value: Any) -> str:
    """Short sales-line code from a line label: 'لاين يک' -> '1', 'لاين دو' -> '2', 'لاين G' -> 'G', '1' -> '1'."""
    text = fold_text(value)
    if not text:
        return ""
    last = text.split(" ")[-1]
    if last.endswith(".0") and last[:-2].isdigit():
        last = last[:-2]  # numeric cell 1.0
    mapping = {"یک": "1", "دو": "2", "سه": "3", "1": "1", "2": "2", "3": "3"}
    if last in mapping:
        return mapping[last]
    return last.upper() if len(last) == 1 else last


def line_group_codes(label: Any) -> set[str]:
    """Manager-sheet line label ' 1-2' -> {'1', '2'}; 'G' -> {'G'}."""
    text = fold_text(label).replace("/", "-").replace("،", "-")
    return {line_code(p) for p in text.split("-") if p.strip()}

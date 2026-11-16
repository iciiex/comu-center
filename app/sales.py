"""XLSX sales import: parse and validate (EP-07).

Contract is SAMPLE until the employer provides a real export (OD-03):
``external_id, user_external_id, sale_date, sku_code, quantity, amount`` and the
optional ``customer_external_id, branch_code``.

Rules that matter:
* file-level problems reject the file (nothing is stored as valid);
* row-level problems never reject the file — the row is reported and skipped;
* a user id is only mapped through ``sales_user_map`` (explicit, never guessed);
* parsing never writes points. Scoring happens later, explicitly, per row.
"""

from __future__ import annotations

import io
from datetime import UTC, date, datetime
from decimal import ROUND_FLOOR, Decimal, InvalidOperation
from typing import Any

REQUIRED_COLUMNS = (
    "external_id",
    "user_external_id",
    "sale_date",
    "sku_code",
    "quantity",
    "amount",
)
OPTIONAL_COLUMNS = ("customer_external_id", "branch_code", "brand_code")
KNOWN_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

# Header aliases: the single place to adapt the importer to the real operational workbook
# (OD-03) without touching the pipeline. Keys are lower-cased, trimmed headers.
# SAMPLE: only English synonyms are listed; Persian headers of the real workbook go here.
HEADER_ALIASES: dict[str, str] = {
    "brand": "brand_code",
    "branch": "branch_code",
    "rep_id": "user_external_id",
    "rep_code": "user_external_id",
    "invoice_id": "external_id",
    "date": "sale_date",
    "sku": "sku_code",
    "qty": "quantity",
}

# Sheet names the importer prefers; falls back to the workbook's active sheet.
SALES_SHEET_NAMES = ("salesdata", "sales", "sales-sample", "فروش")
TARGET_SHEET_NAMES = ("targets", "target", "اهداف", "تارگت")
TARGET_COLUMNS = ("user_external_id", "brand_code", "period", "target_amount")


class SalesFileError(Exception):
    """File-level problem: the whole upload is rejected."""


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
        return number if number.is_finite() else None
    cleaned = str(value).strip().replace(",", "").replace("٬", "").replace(" ", "")
    if not cleaned:
        return None
    try:
        number = Decimal(cleaned)
        return number if number.is_finite() else None
    except InvalidOperation:
        return None


def _sale_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _text(value)
    if not text:
        return None
    head = text.split("T")[0].split(" ")[0].replace("/", "-")
    try:
        return date.fromisoformat(head)
    except ValueError:
        return None


def _raw(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _pick_sheet(workbook, preferred: tuple[str, ...]):
    for sheet in workbook.worksheets:
        if sheet.title.strip().lower() in preferred:
            return sheet
    return workbook.active if preferred is SALES_SHEET_NAMES else None


def detect_origin(raw: bytes) -> str:
    """'sample' when any sheet name contains SAMPLE (the synthetic workbook declares itself).

    A real operational workbook has no such sheet and is tagged 'imported'. This keeps sample
    and real data distinguishable end to end (demo rule: never present sample data as real).
    """
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception:
        return "imported"
    return "sample" if any("sample" in s.title.lower() for s in workbook.worksheets) else "imported"


def parse_targets(raw: bytes, max_rows: int = 5000) -> list[dict[str, Any]]:
    """Read the optional ``Targets`` sheet (SAMPLE contract; real Team/Targets mapping is OD-03)."""
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception:
        return []
    sheet = _pick_sheet(workbook, TARGET_SHEET_NAMES)
    if sheet is None:
        return []
    rows = sheet.iter_rows(values_only=True)
    header = next(rows, None)
    if header is None:
        return []
    headers = [_text(cell).lower() for cell in header]
    if any(column not in headers for column in TARGET_COLUMNS):
        raise SalesFileError("ستون‌های شیت Targets: " + "، ".join(TARGET_COLUMNS))
    out: list[dict[str, Any]] = []
    for number, values in enumerate(rows, start=2):
        if values is None or all(c is None or _text(c) == "" for c in values):
            continue
        record = {
            name: (values[headers.index(name)] if headers.index(name) < len(values) else None)
            for name in TARGET_COLUMNS
        }
        record["row_number"] = number
        out.append(record)
        if len(out) > max_rows:
            raise SalesFileError(f"شیت Targets بیش از {max_rows} ردیف دارد.")
    return out


def validate_targets(
    rows: list[dict[str, Any]], user_map: dict[str, str], brands: set[str]
) -> list[dict[str, Any]]:
    """Pure validation of target rows; a bad row is reported, never fatal."""
    import re

    seen: set[tuple[str, str, str]] = set()
    checked: list[dict[str, Any]] = []
    for row in rows:
        ext = _text(row.get("user_external_id"))
        brand = _text(row.get("brand_code")).upper()
        period = _text(row.get("period"))
        amount = _decimal(row.get("target_amount"))
        error: str | None = None
        if ext not in user_map:
            error = "Sales representative code not found in organization"
        elif brands and brand not in brands:
            error = "Unknown brand"
        elif not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", period):
            error = "Period must look like YYYY-MM"
        elif amount is None or amount < 0:
            error = "Invalid target amount"
        elif (ext, brand, period) in seen:
            error = "Duplicate target in this file"
        seen.add((ext, brand, period))
        checked.append(
            {
                "row_number": row["row_number"],
                "user_external_id": ext,
                "user_id": user_map.get(ext),
                "brand_code": brand,
                "period": period,
                "amount": str(amount) if amount is not None else None,
                "status": "invalid" if error else "valid",
                "error_message": error,
            }
        )
    return checked


def parse_workbook(raw: bytes, max_rows: int = 5000) -> list[dict[str, Any]]:
    """Read the first sheet into row dicts; raise ``SalesFileError`` on file problems."""
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises several unrelated types
        raise SalesFileError(
            "فایل اکسل قابل خواندن نیست؛ مطمئن شوید یک فایل xlsx سالم است."
        ) from exc

    sheet = _pick_sheet(workbook, SALES_SHEET_NAMES)
    if sheet is None:
        raise SalesFileError("فایل هیچ شیتی ندارد.")

    rows = sheet.iter_rows(values_only=True)
    header = next(rows, None)
    if header is None:
        raise SalesFileError("فایل خالی است.")

    headers = [HEADER_ALIASES.get(_text(cell).lower(), _text(cell).lower()) for cell in header]
    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        raise SalesFileError("ستون‌های الزامی موجود نیست: " + "، ".join(missing))

    index = {name: position for position, name in enumerate(headers) if name in KNOWN_COLUMNS}
    parsed: list[dict[str, Any]] = []
    for number, values in enumerate(rows, start=2):
        if values is None:
            continue
        if all(cell is None or _text(cell) == "" for cell in values):
            continue
        record: dict[str, Any] = {"row_number": number}
        for name, position in index.items():
            record[name] = values[position] if position < len(values) else None
        record["raw"] = {
            name: _raw(values[position])
            for name, position in index.items()
            if position < len(values)
        }
        parsed.append(record)
        if len(parsed) > max_rows:
            raise SalesFileError(f"فایل بیش از {max_rows} ردیف داده دارد؛ آن را تقسیم کنید.")
    if not parsed:
        raise SalesFileError("فایل هیچ ردیف داده‌ای ندارد (فقط سرصفحه).")
    return parsed


def validate_rows(
    rows: list[dict[str, Any]],
    user_map: dict[str, str],
    *,
    existing_ids: set[str] | None = None,
    today: date | None = None,
    brands: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Attach status/error/user to every parsed row (pure function, no writes).

    ``brands``: when the organization defines brands (kilos demo profile), every row must carry
    a known brand code (E_BRAND). With no brands configured the column stays optional.
    """
    existing_ids = existing_ids or set()
    brands = brands or set()
    today = today or datetime.now(tz=UTC).date()
    seen: set[str] = set()
    checked: list[dict[str, Any]] = []

    for row in rows:
        external_id = _text(row.get("external_id"))
        user_external_id = _text(row.get("user_external_id"))
        sale_day = _sale_date(row.get("sale_date"))
        quantity = _decimal(row.get("quantity"))
        amount = _decimal(row.get("amount"))
        sku = _text(row.get("sku_code"))
        brand = _text(row.get("brand_code")).upper()

        status = _row_status(
            external_id=external_id,
            user_external_id=user_external_id,
            mapped=user_external_id in user_map,
            sale_day=sale_day,
            today=today,
            quantity=quantity,
            amount=amount,
            sku=sku,
            already_seen=external_id in seen,
            exists=external_id in existing_ids,
        )
        if status["status"] == "valid" and brands and brand not in brands:
            status = _invalid("E_BRAND", "برند خالی یا ناشناخته است.")

        checked.append(
            {
                "row_number": row["row_number"],
                "external_id": external_id,
                "user_external_id": user_external_id,
                "user_id": user_map.get(user_external_id),
                "sale_date": sale_day.isoformat() if sale_day else None,
                "sku_code": sku,
                "quantity": str(quantity) if quantity is not None else None,
                "amount": str(amount) if amount is not None else None,
                "customer_external_id": _text(row.get("customer_external_id")) or None,
                "branch_code": _text(row.get("branch_code")) or None,
                "brand_code": brand or None,
                "raw": row.get("raw", {}),
                **status,
            }
        )
        if external_id:
            seen.add(external_id)
    return checked


def _row_status(
    *,
    external_id: str,
    user_external_id: str,
    mapped: bool,
    sale_day: date | None,
    today: date,
    quantity: Decimal | None,
    amount: Decimal | None,
    sku: str,
    already_seen: bool,
    exists: bool,
) -> dict[str, str | None]:
    if not external_id:
        return _invalid("E_EXTERNAL_ID", "شناسه یکتای ردیف خالی است.")
    if not user_external_id:
        return _invalid("E_USER_ID", "شناسه ویزیتور خالی است.")
    if already_seen:
        return _duplicate("E_DUPLICATE_IN_FILE", "این شناسه در همین فایل تکرار شده است.")
    if exists:
        return _duplicate("E_DUPLICATE_EXISTING", "این رکورد در import قبلی ثبت شده است.")
    if not mapped:
        return _invalid("E_USER_MAPPING", "شناسه ویزیتور در نگاشت سازمان وجود ندارد.")
    if sale_day is None:
        return _invalid("E_DATE", "تاریخ فروش نامعتبر است.")
    if sale_day > today:
        return _invalid("E_FUTURE_DATE", "تاریخ فروش در آینده است.")
    if quantity is None or quantity <= 0:
        return _invalid("E_QUANTITY", "مقدار باید عددی بزرگ‌تر از صفر باشد.")
    if amount is None or amount < 0:
        return _invalid("E_AMOUNT", "مبلغ باید عددی نامنفی باشد.")
    if not sku:
        return _invalid("E_SKU", "کد محصول خالی است.")
    return {"status": "valid", "error_code": None, "error_message": None}


def _invalid(code: str, message: str) -> dict[str, str]:
    return {"status": "invalid", "error_code": code, "error_message": message}


def _duplicate(code: str, message: str) -> dict[str, str]:
    return {"status": "duplicate", "error_code": code, "error_message": message}


def money_points(amount: Decimal, unit_size: Decimal, points_per_unit: int) -> int:
    """SAMPLE formula shared by the engine and the UI preview."""
    if unit_size <= 0:
        return 0
    return int((amount / unit_size).to_integral_value(rounding=ROUND_FLOOR)) * points_per_unit

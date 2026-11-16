"""Text and number normalisation for matching. Source values are always preserved elsewhere.

Folding is for *matching only* (audit §H defect 1/14: Arabic ك/ي vs Persian ک/ی silently broke
joins, e.g. the Karaj branch group). Nothing here is ever written back over a source value.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

_FOLD = str.maketrans(
    {
        "ك": "ک",  # ك -> ک
        "ي": "ی",  # ي -> ی
        "ى": "ی",  # ى -> ی
        "ۀ": "ه",  # ۀ -> ه
        "ة": "ه",  # ة -> ه
        "ؤ": "و",  # ؤ -> و
        "أ": "ا",  # أ -> ا
        "إ": "ا",  # إ -> ا
        "آ": "ا",  # آ -> ا
    }
)
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_STRIP = re.compile("[‌‍‎‏ـً-ٟ﻿]")  # ZWNJ/ZWJ/marks, tatweel, harakat
_SPACES = re.compile(r"\s+")


def fold_text(value: Any) -> str:
    """Matching key: folded Arabic/Persian letters, Latin digits, no ZWNJ/tatweel, collapsed
    whitespace, casefolded. Empty string for None."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.translate(_FOLD).translate(_DIGITS)
    text = text.replace("‌", " ")  # ZWNJ behaves like a space for matching
    text = _STRIP.sub("", text)
    return _SPACES.sub(" ", text).strip().casefold()


def source_text(value: Any) -> str:
    """Trimmed source value, unchanged otherwise ('' for None)."""
    return "" if value is None else str(value).strip()


def is_error_cell(value: Any) -> bool:
    return isinstance(value, str) and value.strip().upper() in {"#N/A", "#REF!", "#VALUE!", "#DIV/0!", "#NAME?"}


def parse_decimal(value: Any) -> Decimal | None:
    """Exact decimal from a cell (int/float/str, Persian digits, thousands separators).

    Returns None for blanks, booleans and non-numeric text. Negative and fractional values are
    preserved (net cartons can be negative or fractional)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return value if value.is_finite() else None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        # repr gives the shortest round-trip form (5.833333333333333, not binary noise)
        number = Decimal(repr(value))
        return number if number.is_finite() else None
    text = str(value).translate(_DIGITS).strip().replace(",", "").replace("٬", "").replace(" ", "")
    text = text.replace("٫", ".")
    if not text or is_error_cell(text):
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def decimal_text(value: Decimal | None) -> str | None:
    """Canonical TEXT form for storage (no exponent, no trailing zeros)."""
    if value is None:
        return None
    text = format(value.normalize(), "f")
    return "0" if text in {"-0", ""} else text


def header_key(value: Any) -> str:
    """Header matching key: folded, punctuation collapsed. Used for prefix matching, because the
    real workbook has truncated/padded headers (e.g. 'کارتن ناخالص منهای برگ...')."""
    return re.sub(r"[\s_\-\.\(\)]+", " ", fold_text(value)).strip()

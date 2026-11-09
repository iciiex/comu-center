"""Gregorian → Jalali conversion for display only (Asia/Tehran dates, no tz math)."""

from __future__ import annotations

from datetime import date, datetime

JALALI_MONTHS = (
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
)
PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_persian_digits(value: object) -> str:
    return str(value).translate(PERSIAN_DIGITS)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """Convert a Gregorian date to the Jalali calendar (arithmetic algorithm)."""
    g_days_in_month = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    gy2, gm2, gd2 = gy - 1600, gm - 1, gd - 1
    g_day_no = (
        365 * gy2
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        + g_days_in_month[gm2]
        + gd2
    )
    if gm > 2 and ((gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0):
        g_day_no += 1

    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    month_days = (31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29)
    jm = 0
    while jm < 12 and j_day_no >= month_days[jm]:
        j_day_no -= month_days[jm]
        jm += 1
    return jy, jm + 1, j_day_no + 1


def format_jalali(value: str | datetime | date | None, *, with_time: bool = False) -> str:
    """Format an ISO string/date as e.g. «۲۷ آبان ۱۴۰۵»."""
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    elif isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime(value.year, value.month, value.day)

    jy, jm, jd = gregorian_to_jalali(parsed.year, parsed.month, parsed.day)
    text = f"{to_persian_digits(jd)} {JALALI_MONTHS[jm - 1]} {to_persian_digits(jy)}"
    if with_time:
        text += f" · {to_persian_digits(parsed.strftime('%H:%M'))}"
    return text

from app.jalali import format_jalali, gregorian_to_jalali, to_persian_digits


def test_known_dates() -> None:
    assert gregorian_to_jalali(2026, 11, 9) == (1405, 8, 18)
    assert gregorian_to_jalali(2026, 11, 18) == (1405, 8, 27)
    assert gregorian_to_jalali(2026, 12, 21) == (1405, 9, 30)
    assert gregorian_to_jalali(2024, 3, 20) == (1403, 1, 1)


def test_formatting_uses_persian_digits() -> None:
    assert format_jalali("2026-11-18T09:30:00+00:00") == "۲۷ آبان ۱۴۰۵"
    assert format_jalali("2026-11-18T09:30:00+00:00", with_time=True).endswith("۰۹:۳۰")
    assert format_jalali(None) == "—"


def test_digits() -> None:
    assert to_persian_digits("2026") == "۲۰۲۶"

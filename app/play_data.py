"""Shared queries and invariants for the isolated Kilos Play demonstration."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app import db
from app.jalali import format_jalali, to_persian_digits

TEHRAN = ZoneInfo("Asia/Tehran")
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
ADMIN = "demo-admin"
VISITOR = "visitor-ali"
PRIMARY = "member-maryam"
PRIMARY_FAMILY = "family-rezaei"
AVATARS = {
    "fox": "روباه",
    "bear": "خرس",
    "lion": "شیر",
    "owl": "جغد",
    "cat": "گربه",
    "panda": "پاندا",
    "rabbit": "خرگوش",
    "frog": "قورباغه",
}
REGIONS = ("تهران شمال", "تهران غرب", "البرز", "گیلان", "فارس", "اصفهان", "خراسان رضوی", "مازندران")
CARDS = {
    "customer": "مشتری",
    "product": "محصول",
    "feature": "ویژگی",
    "limitation": "محدودیت",
    "event": "اتفاق غیرمنتظره",
}
DIFFICULTIES = {"easy": "آسان", "medium": "متوسط", "hard": "سخت"}
WORD_MODES = {"guess": "حدس کلمه", "forbidden": "کلمات ممنوعه", "speed": "چالش سرعت"}
EVENTS = {
    "sale": "پاداش فروش",
    "entry": "ورود به بازی",
    "issue": "صدور نمایشی",
    "deduct": "کسر نمایشی",
    "correct": "اصلاح موجودی",
}
METRICS = {"games": "تعداد بازی تکمیل‌شده", "sales": "تعداد فروش تأییدشده", "amount": "مبلغ فروش"}
ART = {
    "shir": {
        "genre": "خلاقیت و کارت",
        "color": "orange",
        "icon": "cards",
        "tag": "بازی ویژه",
        "steps": (
            "برای یک مشتری خیالی با کارت‌های دستت پیشنهاد بساز.",
            "وقتی همه آماده شدند، پیشنهادها یکی‌یکی نمایش داده می‌شوند.",
            "به پیشنهاد محبوبت رأی بده؛ به پیشنهاد خودت نمی‌شود رأی داد.",
        ),
    },
    "quiz": {
        "genre": "دانش و سرگرمی",
        "color": "green",
        "icon": "brain",
        "tag": "دانستنی‌ها",
        "steps": (
            "در اتاق، دسته یا سختی پرسش‌ها را انتخاب کن.",
            "هر بازیکن فقط یک پاسخ برای هر پرسش دارد.",
            "پاسخ درست امتیاز دارد؛ پس از هر پرسش پاسخ درست نمایش داده می‌شود.",
        ),
    },
    "words": {
        "genre": "کلمات و سرعت",
        "color": "purple",
        "icon": "bolt",
        "tag": "سرعتی",
        "steps": (
            "در حدس کلمه، از راهنما برای حدس واژه استفاده کن.",
            "در کلمات ممنوعه، به نوبت سرنخ بده؛ خود واژه و واژه‌های ممنوعه مجاز نیستند.",
            "در چالش سرعت، اولین پاسخ درست امتیاز می‌گیرد.",
        ),
    },
}


class PlayError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.message = message
        self.status = status


def now() -> int:
    return int(datetime.now(TEHRAN).timestamp())


def day(moment: int | None = None) -> date:
    return datetime.fromtimestamp(now() if moment is None else moment, TEHRAN).date()


def epoch(iso: str | date) -> int:
    return int(
        datetime.combine(
            date.fromisoformat(iso) if isinstance(iso, str) else iso, time.min, TEHRAN
        ).timestamp()
    )


def month_bounds(today: date) -> tuple[date, date]:
    """Iranian calendar month bounds, used by sales and the monthly competition."""
    from app.jalali import gregorian_to_jalali

    jy, jm, jd = gregorian_to_jalali(today.year, today.month, today.day)
    start = today - timedelta(days=jd - 1)
    leap_probe = start + timedelta(days=29)
    same_month = gregorian_to_jalali(leap_probe.year, leap_probe.month, leap_probe.day)[:2]
    length = 31 if jm <= 6 else 30 if jm < 12 or same_month == (jy, jm) else 29
    return start, start + timedelta(days=length)


def fmt(value: int | None) -> str:
    if value is None:
        return "—"
    return to_persian_digits(f"{value:,}".replace(",", "٬"))


def when(value: int | None) -> str:
    return format_jalali(datetime.fromtimestamp(value, TEHRAN), with_time=True) if value else "—"


def uid() -> str:
    return uuid.uuid4().hex


def dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def one(conn, sql, *params) -> dict | None:
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row is not None else None


def rows(conn, sql, *params) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, params)]


def scalar(conn, sql, *params) -> int:
    return conn.execute(sql, params).fetchone()[0]


def need(row: dict | None, reason: str = "این مورد پیدا نشد.") -> dict:
    if row is None:
        raise PlayError(reason, 404)
    return row


def text(value, label: str, maximum: int = 100, *, optional: bool = False) -> str:
    value = str(value or "").strip()
    if len(value) > maximum or (not optional and not value):
        raise PlayError(f"«{label}» را وارد کنید (حداکثر {fmt(maximum)} نویسه).")
    return value


def integer(value, label: str, minimum: int, maximum: int) -> int:
    cleaned = str(value if value is not None else "").strip().translate(DIGITS)
    cleaned = cleaned.replace("٬", "").replace(",", "")
    if not re.fullmatch(r"-?[0-9]{1,14}", cleaned):
        raise PlayError(f"«{label}» باید یک عدد باشد.")
    number = int(cleaned)
    if not minimum <= number <= maximum:
        raise PlayError(f"«{label}» باید بین {fmt(minimum)} و {fmt(maximum)} باشد.")
    return number


def choice(value, options, label: str):
    if value not in options:
        raise PlayError(f"یک «{label}» معتبر انتخاب کنید.")
    return value


def iso_date(value, label: str) -> str:
    try:
        parsed = date.fromisoformat(str(value or "").translate(DIGITS))
        if not 2000 <= parsed.year <= 2100:
            raise ValueError
        return parsed.isoformat()
    except ValueError:
        raise PlayError(f"«{label}» معتبر نیست.") from None


def request_id(value) -> str:
    if value and re.fullmatch(r"[a-f0-9]{32}", str(value)):
        return str(value)
    raise PlayError("شناسهٔ درخواست معتبر نیست. صفحه را دوباره باز کنید.", 400)


def percent(current: int, target: int) -> int:
    return max(0, min(100, current * 100 // max(1, target)))


@contextmanager
def writing(conn: sqlite3.Connection) -> Iterator[None]:
    """Serialize ledger and room updates; rolls back every related write on failure."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def initialize(path: Path) -> None:
    from app.play_seed import seed

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = db.connect(path)
    try:
        # Inspect the marker before changing an existing file's journal or applying migrations.
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        unexpected = (
            names
            - {"schema_migrations"}
            - {name for name in names if name.startswith(("play_", "sqlite_"))}
        )
        if unexpected or (names - {"schema_migrations"} and "play_meta" not in names):
            raise RuntimeError("Expected an isolated Kilos Play demo database")
        if "play_meta" in names and one(
            conn, "SELECT value FROM play_meta WHERE key='isolation'"
        ) != {"value": "kilos-play-demo"}:
            raise RuntimeError("Expected an isolated Kilos Play demo database")
        conn.execute("PRAGMA journal_mode=WAL")
        db.apply_migrations(conn, Path(__file__).with_name("play_migrations"))
        with writing(conn):
            if one(conn, "SELECT value FROM play_meta WHERE key='isolation'") is None:
                seed(conn)
    finally:
        conn.close()


def reset(conn) -> None:
    from app.play_seed import seed

    if scalar(conn, "SELECT value FROM play_meta WHERE key='isolation'") != "kilos-play-demo":
        raise PlayError("این پایگاه، محیط نمایشی کیلوس پلی نیست.", 409)
    # Explicit whitelist and dependency order; the legacy database is never opened here.
    tables = (
        "play_audit",
        "play_invites",
        "play_badges",
        "play_competitions",
        "play_rewards",
        "play_claims",
        "play_missions",
        "play_scores",
        "play_results",
        "play_room_members",
        "play_rooms",
        "play_words",
        "play_questions",
        "play_cards",
        "play_games",
        "play_notices",
        "play_wallet_events",
        "play_sales",
        "play_campaign_members",
        "play_campaigns",
        "play_token_rules",
        "play_sessions",
        "play_accounts",
        "play_families",
        "play_meta",
    )
    for table in tables:
        conn.execute(f"DELETE FROM {table}")  # noqa: S608 (constant allowlist)
    seed(conn)


def balance(conn, family: str) -> int:
    return scalar(
        conn, "SELECT COALESCE(SUM(amount),0) FROM play_wallet_events WHERE family_id=?", family
    )


def ledger(conn, family=None, selected=None, limit=100) -> list[dict]:
    return rows(
        conn,
        """SELECT e.*, f.name AS family, a.name AS actor
        FROM play_wallet_events e JOIN play_families f ON f.id=e.family_id
        LEFT JOIN play_accounts a ON a.id=e.actor_id
        WHERE (? IS NULL OR e.family_id=?) AND (? IS NULL OR e.id=?)
        ORDER BY e.created_at DESC, e.rowid DESC LIMIT ?""",
        family,
        family,
        selected,
        selected,
        limit,
    )


def wallet_event(conn, family, kind, source, amount, reason, actor=None, at=None) -> None:
    if not amount:
        return
    old = one(conn, "SELECT * FROM play_wallet_events WHERE kind=? AND source_id=?", kind, source)
    if old:
        if (old["family_id"], old["amount"], old["reason"], old["actor_id"]) != (
            family,
            amount,
            reason,
            actor,
        ):
            raise PlayError("این شناسه قبلاً برای رویداد دیگری استفاده شده است.", 409)
        return
    if amount < 0 and balance(conn, family) + amount < 0:
        raise PlayError("موجودی کیف خانواده برای این تغییر کافی نیست.", 409)
    conn.execute(
        """INSERT INTO play_wallet_events
        (id,family_id,kind,source_id,amount,created_at,reason,actor_id) VALUES (?,?,?,?,?,?,?,?)""",
        (uid(), family, kind, source, amount, at if at is not None else now(), reason, actor),
    )


def audit(conn, actor, action, summary, at=None) -> None:
    conn.execute(
        "INSERT INTO play_audit VALUES (?,?,?,?,?)",
        (uid(), actor, action, summary, at if at is not None else now()),
    )


def notify(conn, account_id, title, message) -> None:
    conn.execute(
        "INSERT INTO play_notices VALUES (?,?,?,?,?,NULL)",
        (uid(), account_id, title, message, now()),
    )


def grant_badge(conn, account_id, code, source_id="once", at=None) -> bool:
    result = conn.execute(
        """INSERT INTO play_badges (id,account_id,code,source_id,created_at)
        SELECT ?,?,code,?,? FROM play_rewards WHERE code=? AND active=1
        ON CONFLICT(account_id,code,source_id) DO NOTHING""",
        (uid(), account_id, source_id, at if at is not None else now(), code),
    )
    return result.rowcount == 1


def add_score(conn, account, family, source_type, source_id, amount, at=None) -> None:
    conn.execute(
        """INSERT INTO play_scores VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(account_id,source_type,source_id) DO NOTHING""",
        (uid(), account, family, source_type, source_id, amount, at if at is not None else now()),
    )


def family_stats(conn, family: str) -> dict:
    totals = one(
        conn,
        """SELECT COUNT(*) AS played,
        COALESCE(SUM(amount),0) AS score FROM play_scores
        WHERE family_id=? AND source_type IN ('game','mission')""",
        family,
    )
    score = totals["score"]
    return {
        "score": score,
        "level": 1 + score // 100,
        "level_progress": score % 100,
        "played": scalar(conn, "SELECT COUNT(*) FROM play_results WHERE family_id=?", family),
        "balance": balance(conn, family),
    }


def family_members(conn, family: str, only_active: bool = True) -> list[dict]:
    return rows(
        conn,
        """SELECT a.*,
        (SELECT COUNT(*) FROM play_scores s WHERE s.account_id=a.id AND s.source_type='game') games,
        (SELECT COALESCE(SUM(s.amount),0) FROM play_scores s WHERE s.account_id=a.id) score,
        (SELECT COUNT(*) FROM play_badges b WHERE b.account_id=a.id) badges
        FROM play_accounts a WHERE family_id=? AND role='member' AND (active=1 OR ?=0)
        ORDER BY a.active DESC,a.age,a.created_at,a.rowid""",
        family,
        only_active,
    )


def achievements(conn, family: str, account: str | None = None) -> list[dict]:
    return rows(
        conn,
        """SELECT b.*,r.title,r.description,r.icon,a.name FROM play_badges b
        JOIN play_rewards r ON b.code=r.code JOIN play_accounts a ON a.id=b.account_id
        WHERE a.family_id=? AND (? IS NULL OR a.id=?) ORDER BY b.created_at DESC,b.rowid DESC""",
        family,
        account,
        account,
    )


def history(conn, family: str | None = None, limit: int = 40) -> list[dict]:
    records = rows(
        conn,
        """SELECT p.*,f.name AS family,g.title AS game, r.code
        FROM play_results p JOIN play_families f ON f.id=p.family_id
        JOIN play_games g ON p.game_key=g.key LEFT JOIN play_rooms r ON r.id=p.room_id
        WHERE (? IS NULL OR p.family_id=?) ORDER BY p.created_at DESC,p.rowid DESC LIMIT ?""",
        family,
        family,
        limit,
    )
    for item in records:
        item["result"] = json.loads(item.pop("details_json"))
    return records


def ranking(conn, period: str) -> list[dict]:
    today = day()
    week = today - timedelta(days=(today.weekday() + 2) % 7)
    start, end = month_bounds(today) if period == "month" else (week, week + timedelta(days=7))
    return rank_between(conn, epoch(start), epoch(end))


def rank_between(conn, start, end) -> list[dict]:
    result = rows(
        conn,
        """WITH score AS (
        SELECT family_id, SUM(amount) AS points, SUM(source_type='game') AS turns,
               COUNT(DISTINCT date(created_at + 12600,'unixepoch')) AS days
        FROM play_scores WHERE created_at>=? AND created_at<? AND source_type IN ('game','mission')
        GROUP BY family_id
    ), badge AS (
        SELECT a.family_id,COUNT(*) AS badges FROM play_badges b
        JOIN play_accounts a ON a.id=b.account_id WHERE b.created_at>=? AND b.created_at<?
        GROUP BY a.family_id
    ) SELECT f.id,f.name,COALESCE(score.turns,0) AS games,COALESCE(score.days,0) AS days,
        COALESCE(badge.badges,0) AS badges,
        COALESCE(score.points,0)+COALESCE(score.turns,0)*2+
          COALESCE(score.days,0)*3+COALESCE(badge.badges,0)*5 AS points
        FROM play_families f LEFT JOIN score ON f.id=score.family_id
        LEFT JOIN badge ON f.id=badge.family_id
        ORDER BY points DESC,f.name,f.id""",
        start,
        end,
        start,
        end,
    )
    for index, row in enumerate(result, 1):
        row["rank"] = index
    return result


def visitor_ranks(conn) -> list[dict]:
    start, end = month_bounds(day())
    result = rows(
        conn,
        """SELECT a.id,a.name,a.avatar,COALESCE(SUM(s.amount),0) AS amount
        FROM play_accounts a LEFT JOIN play_sales s
          ON s.visitor_id=a.id AND s.approved_at IS NOT NULL
          AND s.sold_on>=? AND s.sold_on<? WHERE a.role='visitor' AND a.active=1
        GROUP BY a.id ORDER BY amount DESC,a.name,a.id""",
        start.isoformat(),
        end.isoformat(),
    )
    for index, row in enumerate(result, 1):
        row["rank"] = index
    return result


def sales_list(conn, visitor=None, limit=100) -> list[dict]:
    return rows(
        conn,
        """SELECT s.*,a.name AS visitor,c.title AS campaign FROM play_sales s
        JOIN play_accounts a ON a.id=s.visitor_id LEFT JOIN play_campaigns c ON c.id=s.campaign_id
        WHERE (? IS NULL OR s.visitor_id=?) ORDER BY s.created_at DESC,s.rowid DESC LIMIT ?""",
        visitor,
        visitor,
        limit,
    )


def visitor_stats(conn, who: dict) -> dict:
    stats = next((r for r in visitor_ranks(conn) if r["id"] == who["id"]), None)
    total = stats["amount"] if stats else 0
    tokens = scalar(
        conn, "SELECT COALESCE(SUM(token_amount),0) FROM play_sales WHERE visitor_id=?", who["id"]
    )
    return {
        "amount": total,
        "rank": stats["rank"] if stats else None,
        "tokens": tokens,
        "target_pct": percent(total, who["monthly_target"]),
    }


def campaigns(conn, visitor=None) -> list[dict]:
    items = rows(
        conn,
        """SELECT c.*,
        (SELECT COUNT(*) FROM play_campaign_members m WHERE m.campaign_id=c.id) AS participants,
        (SELECT COUNT(*) FROM play_sales s WHERE s.campaign_id=c.id AND s.approved_at IS NOT NULL
            AND (? IS NULL OR s.visitor_id=?)) AS approvals,
        COALESCE((SELECT SUM(s.amount) FROM play_sales s WHERE s.campaign_id=c.id
            AND s.approved_at IS NOT NULL AND (? IS NULL OR s.visitor_id=?)),0) AS volume,
        (SELECT COUNT(*) FROM play_missions p WHERE p.campaign_id=c.id) AS missions
        FROM play_campaigns c WHERE (? IS NULL OR EXISTS (
            SELECT 1 FROM play_campaign_members m WHERE m.campaign_id=c.id AND m.account_id=?))
        ORDER BY c.starts_on DESC,c.title""",
        visitor,
        visitor,
        visitor,
        visitor,
        visitor,
        visitor,
    )
    today = day().isoformat()
    for item in items:
        item["status"] = (
            "پایان‌یافته"
            if item["ends_on"] < today
            else "غیرفعال"
            if not item["active"]
            else "در راه"
            if item["starts_on"] > today
            else "فعال"
        )
    return items


def competitions(conn, family: str | None = None, public: bool = False) -> list[dict]:
    items = rows(
        conn,
        """SELECT c.*,r.title AS reward FROM play_competitions c
        LEFT JOIN play_rewards r ON c.reward_code=r.code
        WHERE ?=0 OR (c.active=1 AND ? BETWEEN c.starts_on AND c.ends_on)
        ORDER BY c.active DESC,c.starts_on DESC,c.rowid DESC""",
        public,
        day().isoformat(),
    )
    for item in items:
        if item["kind"] == "community":
            start, end = (
                epoch(item["starts_on"]),
                epoch(date.fromisoformat(item["ends_on"]) + timedelta(days=1)),
            )
            item["progress"] = scalar(
                conn,
                """SELECT COUNT(*) FROM play_results
                WHERE created_at>=? AND created_at<?""",
                start,
                end,
            )
            item["contribution"] = scalar(
                conn,
                """SELECT COUNT(*) FROM play_results
                WHERE created_at>=? AND created_at<? AND family_id=?""",
                start,
                end,
                family,
            )
            item["remaining"] = max(0, item["target"] - item["progress"])
            item["percent"] = percent(item["progress"], item["target"])
        else:
            start, end = (
                epoch(item["starts_on"]),
                epoch(date.fromisoformat(item["ends_on"]) + timedelta(days=1)),
            )
            item["board"] = rank_between(conn, start, end)
    return items


def missions(conn, actor: dict) -> list[dict]:
    today = day().isoformat()
    items = rows(
        conn,
        """SELECT p.*,c.title AS campaign, EXISTS(
        SELECT 1 FROM play_claims a WHERE a.mission_id=p.id AND a.account_id=?) AS claimed
        FROM play_missions p LEFT JOIN play_campaigns c ON c.id=p.campaign_id
        WHERE p.audience=? AND p.active=1 AND ? BETWEEN p.starts_on AND p.ends_on
        AND (p.campaign_id IS NULL OR (c.active=1 AND ? BETWEEN c.starts_on AND c.ends_on
            AND EXISTS(SELECT 1 FROM play_campaign_members m
                JOIN play_accounts a ON a.id=m.account_id
                WHERE m.campaign_id=c.id AND a.family_id=? AND a.active=1)))
        ORDER BY p.ends_on,p.rowid""",
        actor["id"],
        actor["role"],
        today,
        today,
        actor["family_id"],
    )
    for item in items:
        if item["metric"] == "games":
            item["progress"] = scalar(
                conn,
                """SELECT COUNT(*) FROM play_scores
                WHERE account_id=? AND source_type='game' AND created_at>=? AND created_at<?""",
                actor["id"],
                epoch(item["starts_on"]),
                epoch(date.fromisoformat(item["ends_on"]) + timedelta(days=1)),
            )
        else:
            totals = one(
                conn,
                """SELECT COUNT(*) AS n,COALESCE(SUM(amount),0) AS amount
                FROM play_sales WHERE visitor_id=? AND approved_at IS NOT NULL
                  AND sold_on BETWEEN ? AND ? AND (? IS NULL OR campaign_id=?)""",
                actor["id"],
                item["starts_on"],
                item["ends_on"],
                item["campaign_id"],
                item["campaign_id"],
            )
            item["progress"] = totals["n" if item["metric"] == "sales" else "amount"]
        item["percent"] = percent(item["progress"], item["goal"])
        item["ready"] = item["progress"] >= item["goal"] and not item["claimed"]
    return items

"""Server-authoritative Sales Quest Arena game BFF domain.

This is deliberately separate from Kiloos organizational score_events/wallet.
"""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from app import db, game_quests, perf, scoring

CATALOG_PATH = Path(__file__).with_name("game_catalog.json")
STORE_CATALOG_PATH = Path(__file__).with_name("game_store_catalog.json")
SALES_CATALOG_PATH = Path(__file__).with_name("game_sales_catalog.json")
AVATARS = {"fox", "bear", "cat", "bunny", "panda", "frog"}


class GameError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


@lru_cache(maxsize=1)
def catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def store_catalog() -> dict[str, Any]:
    return json.loads(STORE_CATALOG_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def sales_catalog() -> dict[str, Any]:
    return json.loads(SALES_CATALOG_PATH.read_text(encoding="utf-8"))


def _all_missions() -> list[dict[str, Any]]:
    missions = [*catalog()["missions"], *sales_catalog()["missions"]]
    base_by_id = {mission["id"]: mission for mission in missions}
    for offer in store_catalog()["offers"]:
        template = base_by_id.get(offer["template_mission_id"])
        if template is None:
            raise RuntimeError(f"Store offer has unknown template mission: {offer['id']}")
        special = copy.deepcopy(template)
        special.update(offer["mission"])
        special["unlock"] = {"storeOfferId": offer["id"]}
        special["storePriceCoins"] = int(offer["price_coins"])
        missions.append(special)
    return missions


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _day_key(now: datetime) -> str:
    return now.astimezone(UTC).date().isoformat()


def _date_diff(first: str, second: str) -> int:
    return (date.fromisoformat(second) - date.fromisoformat(first)).days


def _level(xp: int) -> int:
    current = 1
    for level in catalog()["game_config"]["levels"]:
        if xp >= level["minXp"]:
            current = level["level"]
    return current


def _initial_progress(full_name: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or _now()
    return {
        "version": 1,
        "player": {
            "name": "",
            "avatar": "fox",
            "onboarded": False,
            "createdAt": now.isoformat(),
        },
        "xp": 0,
        "coins": 0,
        "streak": {"count": 0, "best": 0, "lastActiveDate": None},
        "missions": {},
        "drafts": {},
        "daily": None,
        "achievements": {},
        "history": [],
        "_accountName": full_name,
    }


def _mission_map() -> dict[str, dict[str, Any]]:
    return {mission["id"]: mission for mission in _all_missions()}


def _daily_mission(progress: dict[str, Any], day_key: str) -> str:
    # Daily picks remain in the original six-mission game; paid demos are opt-in only.
    missions = catalog()["missions"]
    available = [m for m in missions if not _lock_reason(m, progress)]
    pool = available or [missions[0]]
    # Mirrors the frontend's 32-bit JS string hash. IDs/date keys are ASCII.
    value = 0
    for char in day_key:
        value = (value * 31 + ord(char)) & 0xFFFFFFFF
    return pool[value % len(pool)]["id"]


def _ensure_daily(progress: dict[str, Any], day_key: str) -> dict[str, Any]:
    daily = progress.get("daily")
    if daily and daily.get("date") == day_key and daily.get("missionId") in _mission_map():
        return progress
    next_progress = dict(progress)
    next_progress["daily"] = {
        "date": day_key,
        "missionId": _daily_mission(progress, day_key),
        "completed": False,
    }
    return next_progress


def _lock_reason(mission: dict[str, Any], progress: dict[str, Any]) -> str | None:
    if mission["id"] in progress.get("_admin", {}).get("hidden", []):
        return "این مأموریت در حال حاضر برای شما فعال نیست."
    unlock = mission.get("unlock", {})
    store_offer = unlock.get("storeOfferId")
    if store_offer and store_offer not in progress.get("storeUnlocks", []):
        return perf.fa_digits(f"با {int(mission.get('storePriceCoins', 0))} سکه در فروشگاه نمایشی باز می‌شود")
    after = unlock.get("afterMission")
    if after and int(progress.get("missions", {}).get(after, {}).get("completions", 0)) < 1:
        prerequisite = _mission_map().get(after)
        title = prerequisite["title"] if prerequisite else after
        return f"برای باز شدن ابتدا «{title}» را کامل کنید"
    min_level = unlock.get("minLevel")
    if min_level and _level(int(progress.get("xp", 0))) < int(min_level):
        return perf.fa_digits(f"برای باز شدن به سطح {min_level} برسید")
    if unlock.get("salesGate"):
        gate = progress.get("_sales", {}).get(mission["id"])
        if gate is None:
            return "فقط برای ویزیتورهای دارای داده فروش پردازش‌شده"
        if gate["reason"]:
            return gate["reason"]
    return None


def _mission_views(
    progress: dict[str, Any], day_key: str, *, include_special: bool = False
) -> list[dict[str, Any]]:
    views: list[dict[str, Any]] = []
    if include_special:
        definitions = _all_missions()
    else:
        enabled = progress.get("_sales", {})
        definitions = [
            *catalog()["missions"],
            *[m for m in sales_catalog()["missions"] if m["id"] in enabled],
            *progress.get("_admin", {}).get("custom", []),
        ]
        hidden = progress.get("_admin", {}).get("hidden", [])
        definitions = [m for m in definitions if m["id"] not in hidden]
    for definition in sorted(definitions, key=lambda m: m["order"]):
        record = progress.get("missions", {}).get(definition["id"], {})
        draft = progress.get("drafts", {}).get(definition["id"])
        lock_reason = _lock_reason(definition, progress)
        gate = progress.get("_sales", {}).get(definition["id"])
        if lock_reason and gate and gate.get("done"):
            status = "completed"
        elif lock_reason:
            status = "locked"
        elif draft:
            status = "in_progress"
        elif int(record.get("completions", 0)) > 0:
            status = "completed"
        else:
            status = "available"
        daily = progress.get("daily") or {}
        view = dict(definition)
        view.update(
            status=status,
            completions=int(record.get("completions", 0)),
            bestRating=record.get("bestRating"),
            lockReason=lock_reason,
            draftProgress=(min(1, draft["stepIndex"] / len(definition["steps"])) if draft else 0),
            isDaily=daily.get("date") == day_key and daily.get("missionId") == definition["id"],
            dailyDone=(
                daily.get("date") == day_key
                and daily.get("missionId") == definition["id"]
                and bool(daily.get("completed"))
            ),
        )
        if gate:
            view["salesGateInfo"] = gate["info"]
        views.append(view)
    return views


def _special_mission_views(progress: dict[str, Any], day_key: str) -> list[dict[str, Any]]:
    return [
        mission
        for mission in _mission_views(progress, day_key, include_special=True)
        if mission.get("storeOfferId")
    ]


def _attach_sales(conn, user_id: str, state: dict[str, Any]) -> dict[str, Any]:
    """Transient server-computed sales gate for sales representatives (never persisted).

    Only users with an employee position of 'rep' see sales missions; eligibility is derived
    from processed sales and targets, so the client cannot influence it.
    """
    row = conn.execute(
        """SELECT p.organization_id FROM employee_positions p
           WHERE p.user_id = ? AND p.position = 'rep'""",
        (user_id,),
    ).fetchone()
    state = dict(state)
    state.pop("_sales", None)
    if row is None:
        return state
    org_id = row["organization_id"]
    gate = perf.sales_gate(conn, org_id, user_id)
    entries: dict[str, Any] = {}
    for mission in sales_catalog()["missions"]:
        done = False
        reason = None if gate["eligible"] else gate["reason"]
        award = mission.get("orgAward")
        if gate["eligible"] and award and award.get("oncePerPeriod"):
            key = f"game.sales_mission:{user_id}:{mission['id']}:{gate['period']}"
            if conn.execute(
                "SELECT 1 FROM score_events WHERE idempotency_key = ?", (key,)
            ).fetchone():
                done = True
                reason = perf.fa_digits(f"برای دورهٔ {gate['period']} انجام شد؛ مأموریت بعدی با فروش جدید باز می‌شود")
        entries[mission["id"]] = {"reason": reason, "done": done, "info": gate}
    state["_sales"] = entries
    return state


def _attach_admin(conn, user_id: str, state: dict[str, Any]) -> dict[str, Any]:
    """Transient, server-computed administrator settings for this user (never persisted)."""
    from app import admin_missions

    state = dict(state)
    state.pop("_admin", None)
    row = conn.execute("SELECT organization_id FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return state
    org_id = row["organization_id"]
    state["_admin"] = {
        "hidden": admin_missions.hidden_for_user(conn, org_id, user_id),
        "custom": admin_missions.custom_for_user(conn, org_id, user_id),
    }
    return state


def _custom_mission(conn, user, mission_id: str) -> dict[str, Any] | None:
    from app import admin_missions

    return admin_missions.get_custom(conn, user.organization_id, user.id, mission_id)


def _initialize(conn, user_id: str, full_name: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT state_json FROM game_progress WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        state = _initial_progress(full_name)
        _save(conn, user_id, state)
        return _attach_admin(conn, user_id, _attach_sales(conn, user_id, state))
    state = json.loads(row["state_json"])
    state.pop("_accountName", None)
    return _attach_admin(conn, user_id, _attach_sales(conn, user_id, state))


def _save(conn, user_id: str, progress: dict[str, Any]) -> None:
    stored = dict(progress)
    stored.pop("_accountName", None)
    stored.pop("_sales", None)
    stored.pop("_admin", None)
    conn.execute(
        """INSERT INTO game_progress (user_id, state_json, updated_at) VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET state_json = excluded.state_json,
             updated_at = excluded.updated_at""",
        (user_id, json.dumps(stored, ensure_ascii=False, separators=(",", ":")), db.now_iso()),
    )


def _public_progress(progress: dict[str, Any]) -> dict[str, Any]:
    clean = dict(progress)
    clean.pop("_accountName", None)
    clean.pop("_sales", None)
    clean.pop("_admin", None)
    return clean


def bootstrap(conn, user, csrf_value: str) -> dict[str, Any]:
    progress = _initialize(conn, user.id, user.full_name)
    now = _now()
    day_key = _day_key(now)
    progress = _ensure_daily(progress, day_key)
    if progress.get("daily") != _load_daily_before(conn, user.id):
        _save(conn, user.id, progress)
    return {
        "api_version": "1",
        "content_version": catalog()["content_version"],
        "server_time": now.isoformat(),
        "date_key": day_key,
        "csrf_token": csrf_value,
        "player": {"id": user.id, "account_name": user.full_name, "role": user.role},
        "game_config": catalog()["game_config"],
        "categories": catalog()["categories"],
        "difficulty": catalog()["difficulty"],
        "missions": _mission_views(progress, day_key),
        "special_missions": _special_mission_views(progress, day_key),
        "store": {
            "version": store_catalog()["version"],
            "is_demo": True,
            "currency": "game_coins",
        },
        "achievements_catalog": catalog()["achievements"],
        "quests": _quests(conn, user.id, progress, day_key),
        "progress": _public_progress(progress),
    }


def _load_daily_before(conn, user_id: str):
    row = conn.execute(
        "SELECT state_json FROM game_progress WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    return json.loads(row["state_json"]).get("daily")


def get_progress(conn, user):
    progress = _initialize(conn, user.id, user.full_name)
    day_key = _day_key(_now())
    updated = _ensure_daily(progress, day_key)
    if updated.get("daily") != progress.get("daily"):
        progress = updated
        _save(conn, user.id, progress)
    return {
        "date_key": day_key,
        "missions": _mission_views(progress, day_key),
        "special_missions": _special_mission_views(progress, day_key),
        "quests": _quests(conn, user.id, progress, day_key),
        "progress": _public_progress(progress),
    }


def get_store(conn, user) -> dict[str, Any]:
    progress = _initialize(conn, user.id, user.full_name)
    purchased = {
        row["offer_id"]
        for row in conn.execute(
            "SELECT offer_id FROM game_store_purchases WHERE user_id = ?", (user.id,)
        ).fetchall()
    }
    offers = []
    for offer in store_catalog()["offers"]:
        mission = _mission_map()[offer["mission"]["id"]]
        offers.append(
            {
                "id": offer["id"],
                "title": offer["title"],
                "description": offer["description"],
                "price_coins": int(offer["price_coins"]),
                "mission_id": mission["id"],
                "mission_title": mission["title"],
                "purchased": offer["id"] in purchased,
            }
        )
    return {
        "store_version": store_catalog()["version"],
        "is_demo": True,
        "currency": "game_coins",
        "coin_balance": int(progress.get("coins", 0)),
        "offers": offers,
    }


def purchase_store_offer(conn, user, offer_id: str, idempotency_key: str) -> tuple[dict, bool]:
    if not idempotency_key or len(idempotency_key) > 128 or any(
        ord(char) < 33 or ord(char) > 126 for char in idempotency_key
    ):
        raise GameError(400, "INVALID_IDEMPOTENCY_KEY", "A valid Idempotency-Key is required.")
    offer = next((item for item in store_catalog()["offers"] if item["id"] == offer_id), None)
    if offer is None:
        raise GameError(404, "STORE_OFFER_NOT_FOUND", "Store offer was not found.")

    price = int(offer["price_coins"])
    canonical = json.dumps({"offer_id": offer_id}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = conn.execute(
            """SELECT request_sha256, response_json FROM game_store_purchases
               WHERE user_id = ? AND idempotency_key = ?""",
            (user.id, idempotency_key),
        ).fetchone()
        if existing:
            if existing["request_sha256"] != digest:
                raise GameError(
                    409,
                    "IDEMPOTENCY_KEY_REUSED",
                    "Idempotency-Key was already used with a different request.",
                )
            conn.commit()
            return json.loads(existing["response_json"]), True

        owned = conn.execute(
            "SELECT 1 FROM game_store_purchases WHERE user_id = ? AND offer_id = ?",
            (user.id, offer_id),
        ).fetchone()
        if owned:
            raise GameError(409, "OFFER_ALREADY_PURCHASED", "This offer was already purchased.")

        progress = _initialize(conn, user.id, user.full_name)
        balance = int(progress.get("coins", 0))
        if balance < price:
            raise GameError(409, "INSUFFICIENT_GAME_COINS", "Not enough game coins for this offer.")
        purchase_id = str(uuid.uuid4())
        purchased_at = _now().isoformat()
        progress["coins"] = balance - price
        unlocked = set(progress.get("storeUnlocks", []))
        unlocked.add(offer_id)
        progress["storeUnlocks"] = sorted(unlocked)
        response = {
            "purchase_id": purchase_id,
            "offer_id": offer_id,
            "mission_id": offer["mission"]["id"],
            "price_coins": price,
            "coin_balance": progress["coins"],
            "purchased_at": purchased_at,
            "replayed": False,
        }
        conn.execute(
            """INSERT INTO game_store_purchases
               (id, user_id, offer_id, price_coins, idempotency_key, request_sha256,
                response_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                purchase_id,
                user.id,
                offer_id,
                price,
                idempotency_key,
                digest,
                json.dumps(response, separators=(",", ":")),
                purchased_at,
            ),
        )
        conn.execute(
            """INSERT INTO game_coin_transactions
               (id, user_id, amount, transaction_type, source_id, created_at)
               VALUES (?, ?, ?, 'store_purchase', ?, ?)""",
            (str(uuid.uuid4()), user.id, -price, purchase_id, purchased_at),
        )
        _save(conn, user.id, progress)
        conn.commit()
        return response, False
    except Exception:
        conn.rollback()
        raise


def update_profile(conn, user, patch: dict[str, Any]) -> dict[str, Any]:
    allowed = {"name", "avatar"}
    if not patch or set(patch) - allowed:
        raise GameError(422, "INVALID_PROFILE", "Only name and avatar may be updated.")
    name = patch.get("name")
    avatar = patch.get("avatar")
    if name is not None and (not isinstance(name, str) or len(name.strip()) > 24):
        raise GameError(422, "INVALID_NAME", "Name must be a string of at most 24 characters.")
    if avatar is not None and avatar not in AVATARS:
        raise GameError(422, "INVALID_AVATAR", "Avatar is not supported.")
    progress = _initialize(conn, user.id, user.full_name)
    player = dict(progress["player"])
    if name is not None:
        player["name"] = name.strip()[:24] or player.get("name") or "Rookie"
    if avatar is not None:
        player["avatar"] = avatar
    player["onboarded"] = True
    progress["player"] = player
    _save(conn, user.id, progress)
    return {"progress": _public_progress(progress)}


def _clean_answers(mission: dict[str, Any], raw: Any, *, allow_incomplete: bool) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise GameError(422, "INVALID_ANSWERS", "Answers must be a JSON object.")
    steps = {step["id"]: step for step in mission["steps"]}
    if set(raw) - set(steps):
        raise GameError(
            422, "UNKNOWN_ANSWER", "One or more answer fields are not part of this mission."
        )
    clean: dict[str, Any] = {}
    for key, value in raw.items():
        step = steps[key]
        if step["type"] == "choice":
            valid = isinstance(value, str) and any(
                option["id"] == value for option in step["options"]
            )
            if not valid:
                raise GameError(422, "INVALID_ANSWER", f"Invalid choice for {key}.")
            clean[key] = value
        elif step["type"] == "rating":
            if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 5:
                raise GameError(
                    422, "INVALID_ANSWER", f"Rating for {key} must be an integer from 1 to 5."
                )
            clean[key] = value
        elif step["type"] == "note":
            if not isinstance(value, str):
                raise GameError(422, "INVALID_ANSWER", f"Note for {key} must be text.")
            note = value.strip()
            if len(note) > int(step["maxLength"]):
                raise GameError(422, "INVALID_ANSWER", f"Note for {key} is too long.")
            if note:
                clean[key] = note
    if not allow_incomplete:
        missing = set(mission["completion"]["requiredSteps"]) - set(clean)
        if missing:
            raise GameError(422, "MISSION_INCOMPLETE", "Required mission steps are unanswered.")
    return clean


def _collect_flags(mission: dict[str, Any], answers: dict[str, Any]) -> list[str]:
    flags: set[str] = set()
    for step in mission["steps"]:
        value = answers.get(step["id"])
        if step["type"] == "choice" and value is not None:
            option = next((o for o in step["options"] if o["id"] == value), None)
            flags.update((option or {}).get("flags", []))
        elif step["type"] == "rating" and value == 5:
            flags.add("five_star")
        elif step["type"] == "note" and value:
            flags.add("note_added")
    return sorted(flags)


def _history(conn, user_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT response_json FROM game_completions WHERE user_id = ?
           ORDER BY completed_at DESC, id DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return [json.loads(row["response_json"])["entry"] for row in rows]


def _new_achievements(progress: dict[str, Any], history: list[dict[str, Any]]) -> list[str]:
    base_mission_ids = {mission["id"] for mission in catalog()["missions"]}
    done = {
        mission_id
        for mission_id, record in progress.get("missions", {}).items()
        if mission_id in base_mission_ids and record.get("completions", 0)
    }
    flags = [flag for entry in history for flag in entry.get("flags", [])]
    unlocked: list[str] = []
    level = _level(progress["xp"])
    for achievement in catalog()["achievements"]:
        aid = achievement["id"]
        if aid in progress.get("achievements", {}):
            continue
        condition = {
            "first_steps": len(history) >= 1,
            "deal_maker": "order_received" in flags,
            "five_star": "five_star" in flags,
            "daily_hero": any(entry.get("wasDaily") for entry in history),
            "storyteller": flags.count("note_added") >= 3,
            "high_five": len(history) >= 5,
            "on_fire": progress["streak"]["best"] >= 3,
            "explorer": level >= 2,
            "trailblazer": len(done) >= len(catalog()["missions"]),
            "champion": level >= 5,
        }.get(aid, False)
        if condition:
            unlocked.append(aid)
    return unlocked


def complete_mission(
    conn, user, mission_id: str, answers: Any, idempotency_key: str
) -> tuple[dict[str, Any], bool]:
    if not idempotency_key or len(idempotency_key) > 128:
        raise GameError(
            400, "IDEMPOTENCY_KEY_REQUIRED", "A valid Idempotency-Key header is required."
        )
    if any(ord(char) < 33 or ord(char) > 126 for char in idempotency_key):
        raise GameError(
            400,
            "INVALID_IDEMPOTENCY_KEY",
            "Idempotency-Key must contain printable ASCII characters.",
        )
    definitions = _mission_map()
    mission = definitions.get(mission_id) or _custom_mission(conn, user, mission_id)
    if mission is None:
        raise GameError(404, "MISSION_NOT_FOUND", "Mission was not found.")
    clean = _clean_answers(mission, answers, allow_incomplete=False)
    canonical = json.dumps(
        {"mission_id": mission_id, "answers": clean},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    now = _now()
    completed_at = now.isoformat()
    day_key = _day_key(now)

    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = conn.execute(
            """SELECT request_sha256, response_json FROM game_completions
               WHERE user_id = ? AND idempotency_key = ?""",
            (user.id, idempotency_key),
        ).fetchone()
        if existing:
            if existing["request_sha256"] != digest:
                raise GameError(
                    409,
                    "IDEMPOTENCY_KEY_REUSED",
                    "Idempotency-Key was already used with a different request.",
                )
            conn.commit()
            return json.loads(existing["response_json"]), True

        progress = _initialize(conn, user.id, user.full_name)
        progress = _ensure_daily(progress, day_key)
        reason = _lock_reason(mission, progress)
        if reason:
            raise GameError(409, "MISSION_LOCKED", reason)

        flags = _collect_flags(mission, clean)
        is_daily = progress.get("daily", {}).get("missionId") == mission_id and not progress.get(
            "daily", {}
        ).get("completed")
        config = catalog()["game_config"]["rewards"]
        reward_lines = [
            {
                "ruleId": "mission_complete",
                "label": "Mission complete",
                "xp": mission["xpReward"],
                "coins": mission["coinReward"],
            }
        ]
        bonus_xp = 0
        if is_daily:
            bonus_xp += int(config["dailyBonusXp"])
            reward_lines.append(
                {
                    "ruleId": "daily_bonus",
                    "label": "Daily challenge bonus",
                    "xp": int(config["dailyBonusXp"]),
                    "coins": 0,
                }
            )
        if "order_received" in flags:
            bonus_xp += int(config["orderBonusXp"])
            reward_lines.append(
                {
                    "ruleId": "order_bonus",
                    "label": "Order received bonus",
                    "xp": int(config["orderBonusXp"]),
                    "coins": 0,
                }
            )
        xp_before = int(progress["xp"])
        xp_after = xp_before + int(mission["xpReward"]) + bonus_xp
        coins_after = int(progress["coins"]) + int(mission["coinReward"])
        xp_earned = xp_after - xp_before

        last_active = progress["streak"].get("lastActiveDate")
        gap = _date_diff(last_active, day_key) if last_active else None
        streak_count = (
            int(progress["streak"]["count"])
            if gap == 0
            else int(progress["streak"]["count"]) + 1
            if gap == 1
            else 1
        )
        previous = progress["missions"].get(mission_id, {})
        rating_step = next((step for step in mission["steps"] if step["type"] == "rating"), None)
        rating = clean.get(rating_step["id"]) if rating_step else None
        best_rating = max(int(previous.get("bestRating") or 0), int(rating or 0)) or None
        entry = {
            "id": f"{int(now.timestamp() * 1000):x}-{uuid.uuid4().hex[:6]}",
            "missionId": mission_id,
            "completedAt": completed_at,
            "answers": clean,
            "flags": flags,
            "wasDaily": is_daily,
            "rewards": {
                "lines": reward_lines,
                "xp": xp_earned,
                "coins": int(mission["coinReward"]),
            },
            "xpBefore": xp_before,
            "xpAfter": xp_after,
            "coinsAfter": coins_after,
            "levelBefore": _level(xp_before),
            "levelAfter": _level(xp_after),
            "streakAfter": streak_count,
            "achievementsUnlocked": [],
        }
        record = {
            "completions": int(previous.get("completions", 0)) + 1,
            "firstCompletedAt": previous.get("firstCompletedAt") or completed_at,
            "lastCompletedAt": completed_at,
            "bestRating": best_rating,
        }
        progress["xp"] = xp_after
        progress["coins"] = coins_after
        progress["streak"] = {
            "count": streak_count,
            "best": max(int(progress["streak"]["best"]), streak_count),
            "lastActiveDate": day_key,
        }
        progress.setdefault("missions", {})[mission_id] = record
        progress.setdefault("drafts", {}).pop(mission_id, None)
        if is_daily:
            progress["daily"]["completed"] = True
        history = [entry, *_history(conn, user.id, limit=199)]
        progress["history"] = history[: int(catalog()["game_config"]["history"]["maxEntries"])]
        unlocked = _new_achievements(progress, progress["history"])
        entry["achievementsUnlocked"] = unlocked
        for achievement_id in unlocked:
            progress.setdefault("achievements", {})[achievement_id] = completed_at

        if mission.get("orgAward"):
            gate = progress["_sales"][mission_id]["info"]
            entry["orgPoints"] = _award_org_points(conn, user, mission, gate, completed_at, entry)

        response = {
            "entry": entry,
            "progress": _public_progress(progress),
            "missions": _mission_views(progress, day_key),
            "special_missions": _special_mission_views(progress, day_key),
            "quests": _quests(conn, user.id, progress, day_key, pending_completions=1),
            "date_key": day_key,
        }
        completion_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO game_completions
               (id, user_id, mission_id, idempotency_key, request_sha256,
                response_json, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                completion_id,
                user.id,
                mission_id,
                idempotency_key,
                digest,
                json.dumps(response, ensure_ascii=False, separators=(",", ":")),
                completed_at,
            ),
        )
        _save(conn, user.id, progress)
        conn.commit()
        return response, False
    except Exception:
        conn.rollback()
        raise


def _category_of(mission_id: str) -> str | None:
    mission = _mission_map().get(mission_id)
    return mission.get("category") if mission else None


def _team_completions(conn, user_id: str, day_key: str) -> int | None:
    """Missions completed this ISO week by everyone under the same supervisor (the team challenge)."""
    row = conn.execute(
        "SELECT supervisor_id FROM employee_positions WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None or not row["supervisor_id"]:
        return None  # no team
    start, end = game_quests.week_bounds(day_key)
    return int(
        conn.execute(
            """SELECT COUNT(*) FROM game_completions gc
               JOIN employee_positions p ON p.user_id = gc.user_id
               WHERE p.supervisor_id = ? AND substr(gc.completed_at, 1, 10) BETWEEN ? AND ?""",
            (row["supervisor_id"], start, end),
        ).fetchone()[0]
    )


def _quests(
    conn, user_id: str, progress: dict[str, Any], day_key: str, *, pending_completions: int = 0
) -> dict[str, Any]:
    # pending_completions: a completion inside the open transaction that is not stored yet.
    base = _team_completions(conn, user_id, day_key)
    team = 0 if base is None else base + pending_completions
    return game_quests.weekly_quests(progress, day_key, _category_of, team)


def claim_quest(conn, user, quest_id: str, idempotency_key: str) -> tuple[dict[str, Any], bool]:
    """Claim a completed weekly quest (DEMO). Rewards are GAME XP only, never organizational points.

    Progress is recomputed here from the server history; the client only names the quest. A quest
    pays once per user, quest and ISO week, and an Idempotency-Key replay returns the stored result.
    """
    if not idempotency_key or len(idempotency_key) > 128 or any(
        ord(char) < 33 or ord(char) > 126 for char in idempotency_key
    ):
        raise GameError(400, "INVALID_IDEMPOTENCY_KEY", "A valid Idempotency-Key is required.")
    if game_quests.quest_definition(quest_id) is None:
        raise GameError(404, "QUEST_NOT_FOUND", "Weekly quest was not found.")

    canonical = json.dumps({"quest_id": quest_id}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    now = _now()
    claimed_at = now.isoformat()
    day_key = _day_key(now)

    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = conn.execute(
            """SELECT request_sha256, response_json FROM game_quest_claims
               WHERE user_id = ? AND idempotency_key = ?""",
            (user.id, idempotency_key),
        ).fetchone()
        if existing:
            if existing["request_sha256"] != digest:
                raise GameError(
                    409,
                    "IDEMPOTENCY_KEY_REUSED",
                    "Idempotency-Key was already used with a different request.",
                )
            conn.commit()
            return json.loads(existing["response_json"]), True

        progress = _initialize(conn, user.id, user.full_name)
        view = _quests(conn, user.id, progress, day_key)
        quest = next(item for item in view["quests"] if item["id"] == quest_id)
        if quest["claimed"]:
            raise GameError(
                409, "QUEST_ALREADY_CLAIMED", "This quest was already claimed this week."
            )
        if not quest["complete"]:
            raise GameError(
                409,
                "QUEST_NOT_COMPLETE",
                f"Progress {quest['progress']} of {quest['target']}. "
                "Finish the objective before claiming.",
            )

        reward = int(quest["rewardXp"])
        xp_before = int(progress["xp"])
        xp_after = xp_before + reward
        progress["xp"] = xp_after
        progress["quests"] = game_quests.with_claim(progress, day_key, quest_id, claimed_at, reward)
        unlocked = _new_achievements(progress, progress.get("history", []))
        for achievement_id in unlocked:
            progress.setdefault("achievements", {})[achievement_id] = claimed_at
        view = _quests(conn, user.id, progress, day_key)
        response = {
            "claim": {
                "quest_id": quest_id,
                "week_key": view["weekKey"],
                "xp": reward,
                "xp_before": xp_before,
                "xp_after": xp_after,
                "level_before": _level(xp_before),
                "level_after": _level(xp_after),
                "achievements_unlocked": unlocked,
                "claimed_at": claimed_at,
            },
            "progress": _public_progress(progress),
            "quests": view,
            "missions": _mission_views(progress, day_key),
            "special_missions": _special_mission_views(progress, day_key),
            "date_key": day_key,
        }
        conn.execute(
            """INSERT INTO game_quest_claims
               (id, user_id, week_key, quest_id, xp_awarded, idempotency_key, request_sha256,
                response_json, claimed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                user.id,
                view["weekKey"],
                quest_id,
                reward,
                idempotency_key,
                digest,
                json.dumps(response, ensure_ascii=False, separators=(",", ":")),
                claimed_at,
            ),
        )
        _save(conn, user.id, progress)
        conn.commit()
        return response, False
    except Exception:
        conn.rollback()
        raise


def _award_org_points(
    conn, user, mission: dict[str, Any], gate: dict[str, Any], completed_at: str, entry: dict
) -> dict[str, Any]:
    """Append an organizational score event for a verified sales-gated mission.

    Kept separate from game XP/coins: it goes through the append-only score ledger with an
    idempotency key (once per user/mission/period). Rule status is PROPOSED, not approved.
    """
    award = mission["orgAward"]
    period = gate["period"]
    rule = scoring.find_rule_version(conn, award["ruleCode"])
    if rule is None:
        raise GameError(409, "NO_ACTIVE_RULE_VERSION", "Organizational rule is not published.")
    key = f"game.sales_mission:{user.id}:{mission['id']}:{period}"
    existing = conn.execute(
        "SELECT id, points FROM score_events WHERE idempotency_key = ?", (key,)
    ).fetchone()
    base = {
        "ruleCode": award["ruleCode"],
        "ruleVersion": rule["version"],
        "approvalStatus": award["approvalStatus"],
        "period": period,
        "isDemo": True,
    }
    if existing is not None:
        return {
            **base,
            "points": int(existing["points"]),
            "eventId": existing["id"],
            "created": False,
        }
    points = int(rule["points"])
    event_id = str(uuid.uuid4())
    explain = {
        "rule_code": award["ruleCode"],
        "rule_version": rule["version"],
        "calculation_type": rule["calculation_type"],
        "approval_status": award["approvalStatus"],
        "conditions": {
            "event": "game.sales_mission.completed",
            "min_attainment_pct": gate["minPct"],
        },
        "input": {
            "mission_id": mission["id"],
            "period": period,
            "achieved": gate["achieved"],
            "target": gate["target"],
            "attainment_pct": gate["attainmentPct"],
            "game_entry_id": entry["id"],
        },
        "output": {"points": points},
        "is_sample": bool(rule["is_sample"]),
    }
    scoring._persist_award(
        conn,
        event_id=event_id,
        user_id=user.id,
        source_type="game_sales_mission",
        source_id=f"{user.id}:{mission['id']}:{period}",
        rule_code=award["ruleCode"],
        rule_version_id=rule["id"],
        points=points,
        occurred_at=completed_at,
        key=key,
        explain=explain,
    )
    return {**base, "points": points, "eventId": event_id, "created": True}


def save_draft(conn, user, mission_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    mission = _mission_map().get(mission_id) or _custom_mission(conn, user, mission_id)
    if mission is None:
        raise GameError(404, "MISSION_NOT_FOUND", "Mission was not found.")
    if not isinstance(payload, dict) or set(payload) - {"step_index", "answers"}:
        raise GameError(422, "INVALID_DRAFT", "Draft accepts only step_index and answers.")
    step_index = payload.get("step_index")
    if (
        isinstance(step_index, bool)
        or not isinstance(step_index, int)
        or not 0 <= step_index < len(mission["steps"])
    ):
        raise GameError(422, "INVALID_DRAFT", "step_index is outside the mission.")
    progress = _initialize(conn, user.id, user.full_name)
    reason = _lock_reason(mission, progress)
    if reason:
        raise GameError(409, "MISSION_LOCKED", reason)
    answers = _clean_answers(mission, payload.get("answers", {}), allow_incomplete=True)
    draft = progress.setdefault("drafts", {}).get(mission_id)
    progress["drafts"][mission_id] = {
        "missionId": mission_id,
        "stepIndex": step_index,
        "answers": answers,
        "startedAt": draft.get("startedAt") if draft else _now().isoformat(),
    }
    _save(conn, user.id, progress)
    return {
        "progress": _public_progress(progress),
        "missions": _mission_views(progress, _day_key(_now())),
        "special_missions": _special_mission_views(progress, _day_key(_now())),
    }


def discard_draft(conn, user, mission_id: str) -> dict[str, Any]:
    if mission_id not in _mission_map() and _custom_mission(conn, user, mission_id) is None:
        raise GameError(404, "MISSION_NOT_FOUND", "Mission was not found.")
    progress = _initialize(conn, user.id, user.full_name)
    progress.setdefault("drafts", {}).pop(mission_id, None)
    _save(conn, user.id, progress)
    return {
        "progress": _public_progress(progress),
        "missions": _mission_views(progress, _day_key(_now())),
        "special_missions": _special_mission_views(progress, _day_key(_now())),
    }


def list_history(conn, user, limit: int, cursor: str | None) -> dict[str, Any]:
    if not 1 <= limit <= 100:
        raise GameError(422, "INVALID_LIMIT", "limit must be between 1 and 100.")
    if cursor:
        row = conn.execute(
            "SELECT completed_at, id FROM game_completions WHERE user_id = ? AND id = ?",
            (user.id, cursor),
        ).fetchone()
        if row is None:
            raise GameError(404, "CURSOR_NOT_FOUND", "History cursor was not found.")
        rows = conn.execute(
            """SELECT response_json, id FROM game_completions WHERE user_id = ?
               AND (completed_at < ? OR (completed_at = ? AND id < ?))
               ORDER BY completed_at DESC, id DESC LIMIT ?""",
            (user.id, row["completed_at"], row["completed_at"], row["id"], limit + 1),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT response_json, id FROM game_completions WHERE user_id = ?
               ORDER BY completed_at DESC, id DESC LIMIT ?""",
            (user.id, limit + 1),
        ).fetchall()
    has_more = len(rows) > limit
    page = rows[:limit]
    return {
        "items": [json.loads(row["response_json"])["entry"] for row in page],
        "next_cursor": page[-1]["id"] if has_more and page else None,
    }

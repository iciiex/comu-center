"""Authorized business operations used by the Kilos Play web layer."""

from __future__ import annotations

import secrets
from datetime import timedelta

from app import play_data as p


def visit(conn, code, *, active=False) -> dict:
    result = p.need(
        p.one(conn, "SELECT * FROM play_accounts WHERE role='visitor' AND id=?", code),
        "ویزیتور پیدا نشد.",
    )
    if active and not result["active"]:
        raise p.PlayError("ویزیتور غیرفعال است.", 409)
    return result


def require(actor: dict, *roles: str) -> None:
    if actor["role"] not in roles:
        raise p.PlayError("این عملیات برای نقش شما مجاز نیست.", 403)


def save_visitor(conn, actor, form):
    name = p.text(form.get("name"), "نام ویزیتور", 70)
    region = p.choice(form.get("region"), p.REGIONS, "منطقه")
    target = p.integer(form.get("target"), "هدف ماهانه", 1, 999_999_999_999)
    active = 1 if form.get("active") else 0
    code = form.get("id")
    if code:
        record = visit(conn, code)
        conn.execute(
            """UPDATE play_accounts SET name=?,region=?,monthly_target=?,active=?
            WHERE id=?""",
            (name, region, target, active, record["id"]),
        )
    else:
        family = p.text(form.get("family"), "نام خانواده", 70)
        code, family_id = p.uid(), p.uid()
        conn.execute("INSERT INTO play_families VALUES (?,?,?)", (family_id, family, p.now()))
        conn.execute(
            """INSERT INTO play_accounts
            (id,family_id,role,name,avatar,region,monthly_target,active,created_at)
            VALUES (?,?,'visitor',?,'lion',?,?,?,?)""",
            (code, family_id, name, region, target, active, p.now()),
        )
    p.audit(conn, actor["id"], "visitor", f"پروندهٔ ویزیتور «{name}» ذخیره شد.")
    return code


def family_for(conn, actor, family_id, *, admin_only=False):
    if actor["role"] != "admin" and (
        admin_only or actor["age"] == "child" or actor["family_id"] != family_id
    ):
        raise p.PlayError("دسترسی مدیریت این خانواده را ندارید.", 403)
    return p.need(p.one(conn, "SELECT * FROM play_families WHERE id=?", family_id))


def add_member(conn, family_id, name, age, avatar):
    code = p.uid()
    conn.execute(
        """INSERT INTO play_accounts (id,family_id,role,name,age,avatar,created_at)
        VALUES (?,?,'member',?,?,?,?)""",
        (code, family_id, name, age, avatar, p.now()),
    )
    return code


def manage_member(conn, actor, form):
    family = family_for(conn, actor, form.get("family"))
    member_id = form.get("id")
    if member_id:
        require(actor, "admin")
        member = p.need(
            p.one(
                conn,
                """SELECT * FROM play_accounts
            WHERE id=? AND family_id=? AND role='member'""",
                member_id,
                family["id"],
            )
        )
        if form.get("set_active") in {"0", "1"}:
            active = int(form.get("set_active"))
            conn.execute("UPDATE play_accounts SET active=? WHERE id=?", (active, member_id))
            if member["active"] and not active:
                conn.execute("DELETE FROM play_sessions WHERE account_id=?", (member_id,))
            p.audit(conn, actor["id"], "member", f"وضعیت عضویت «{member['name']}» تغییر کرد.")
            return
    name = p.text(form.get("name"), "نام عضو", 55)
    age = p.choice(form.get("age"), ("adult", "child"), "گروه سنی")
    avatar = p.choice(form.get("avatar"), p.AVATARS, "آواتار")
    if member_id:
        conn.execute(
            "UPDATE play_accounts SET name=?,age=?,avatar=? WHERE id=?",
            (name, age, avatar, member_id),
        )
    else:
        require(actor, "admin")
        add_member(conn, family["id"], name, age, avatar)
    p.audit(conn, actor["id"], "member", f"حساب خانوادگی «{name}» ذخیره شد.")


def invite(conn, actor, form, *, revoke=False):
    family = family_for(conn, actor, form.get("family"))
    if revoke:
        result = conn.execute(
            """UPDATE play_invites SET revoked=1 WHERE code=? AND family_id=?
            AND used_by IS NULL""",
            (form.get("id"), family["id"]),
        )
        if not result.rowcount:
            raise p.PlayError("این دعوت پیدا نشد یا استفاده شده است.", 409)
    else:
        age = p.choice(form.get("age"), ("adult", "child"), "گروه سنی")
        conn.execute(
            "INSERT INTO play_invites VALUES (?,?,?,?,?,NULL,0)",
            (secrets.token_urlsafe(16), family["id"], actor["id"], age, p.now() + 86400 * 3),
        )
    p.audit(conn, actor["id"], "invite", f"دعوت‌نامهٔ {family['name']} به‌روزرسانی شد.")


def available_invite(conn, code):
    return p.need(
        p.one(
            conn,
            """SELECT code,family_id,age FROM play_invites
            WHERE code=? AND expires_at>? AND revoked=0 AND used_by IS NULL""",
            code,
            p.now(),
        ),
        "این دعوت معتبر نیست یا استفاده شده است.",
    )


def accept_invite(conn, code, name, avatar):
    item = available_invite(conn, code)
    name = p.text(name, "نام نمایشی", 55)
    avatar = p.choice(avatar, p.AVATARS, "آواتار")
    account = add_member(conn, item["family_id"], name, item["age"], avatar)
    conn.execute("UPDATE play_invites SET used_by=? WHERE code=?", (account, item["code"]))
    p.audit(conn, account, "invite", f"«{name}» دعوت را پذیرفت.")
    return account


def register_sale(conn, actor, form) -> str:
    visitor = visit(conn, form.get("visitor"), active=True)
    amount = p.integer(form.get("amount"), "مبلغ فروش", 1, 999_999_999_999)
    note = p.text(form.get("note"), "شرح فروش", 160)
    day = p.iso_date(form.get("sold_on"), "تاریخ فروش")
    if day > p.day().isoformat():
        raise p.PlayError("تاریخ فروش نمی‌تواند در آینده باشد.")
    campaign_id = form.get("campaign") or None
    key = p.request_id(form.get("request_id"))
    old = p.one(conn, "SELECT * FROM play_sales WHERE request_id=?", key)
    if old:
        if tuple(
            old[field] for field in ("visitor_id", "amount", "note", "sold_on", "campaign_id")
        ) != (visitor["id"], amount, note, day, campaign_id):
            raise p.PlayError("این درخواست قبلاً با مشخصات دیگری ثبت شده است.", 409)
        return old["id"]
    bonus = 0
    if campaign_id:
        campaign = p.one(
            conn,
            """SELECT c.bonus FROM play_campaigns c
            JOIN play_campaign_members m ON m.campaign_id=c.id
            WHERE c.id=? AND c.active=1 AND ? BETWEEN c.starts_on AND c.ends_on
                AND m.account_id=?""",
            campaign_id,
            day,
            visitor["id"],
        )
        if not campaign:
            raise p.PlayError("کمپین در تاریخ فروش فعال نیست یا ویزیتور عضو آن نیست.")
        bonus = campaign["bonus"]
    code = p.uid()
    conn.execute(
        """INSERT INTO play_sales
        (id,request_id,visitor_id,amount,note,sold_on,campaign_id,created_at,campaign_bonus)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (code, key, visitor["id"], amount, note, day, campaign_id, p.now(), bonus),
    )
    p.audit(conn, actor["id"], "sales", f"یک فروش برای «{visitor['name']}» ثبت شد.")
    return code


def approve_sale(conn, actor, code) -> tuple[int, bool]:
    item = p.need(p.one(conn, "SELECT * FROM play_sales WHERE id=?", code), "فروش پیدا نشد.")
    if item["approved_at"] is not None:
        return item["token_amount"], False
    who = visit(conn, item["visitor_id"], active=True)
    rule = p.one(conn, "SELECT * FROM play_token_rules ORDER BY version DESC LIMIT 1")
    tokens = item["amount"] // rule["unit"] * rule["per_unit"] + item["campaign_bonus"]
    at = p.now()
    conn.execute(
        """UPDATE play_sales SET approved_at=?,approved_by=?,rule_version=?,token_amount=?
        WHERE id=?""",
        (at, actor["id"], rule["version"], tokens, code),
    )
    p.wallet_event(
        conn, who["family_id"], "sale", code, tokens, f"تأیید فروش: {item['note']}", actor["id"], at
    )
    message = f"فروش «{item['note']}» تأیید شد؛ {p.fmt(tokens)} توکن به کیف خانواده رسید."
    recipients = p.rows(
        conn, "SELECT id FROM play_accounts WHERE family_id=? AND active=1", who["family_id"]
    )
    for recipient in recipients:
        p.notify(conn, recipient["id"], "فروش تأیید شد", message)
    p.audit(conn, actor["id"], "sales", f"فروش «{who['name']}» تأیید شد؛ {p.fmt(tokens)} توکن.", at)
    return tokens, True


def adjust(conn, actor, form) -> None:
    family = family_for(conn, actor, form.get("family"), admin_only=True)
    kind = p.choice(form.get("kind"), ("issue", "deduct", "correct"), "نوع تراکنش")
    amount = p.integer(
        form.get("amount"), "مقدار توکن", -100_000 if kind == "correct" else 1, 100_000
    )
    if not amount:
        raise p.PlayError("مقدار اصلاح نباید صفر باشد.")
    if kind == "deduct":
        amount *= -1
    key = p.request_id(form.get("request_id"))
    old = p.one(
        conn,
        """SELECT kind FROM play_wallet_events WHERE source_id=?
                         AND kind IN ('issue','deduct','correct')""",
        key,
    )
    if old and old["kind"] != kind:
        raise p.PlayError("این درخواست قبلاً برای نوع دیگری از تراکنش ثبت شده است.", 409)
    reason = p.text(form.get("reason"), "دلیل", 180)
    p.wallet_event(conn, family["id"], kind, key, amount, reason, actor["id"])
    if not old:
        p.audit(
            conn, actor["id"], "wallet", f"{p.EVENTS[kind]} برای {family['name']}: {p.fmt(amount)}"
        )


def period(form) -> tuple[str, str]:
    start = p.iso_date(form.get("starts_on"), "شروع")
    end = p.iso_date(form.get("ends_on"), "پایان")
    if start > end:
        raise p.PlayError("پایان نباید پیش از شروع باشد.")
    return start, end


def save_campaign(conn, actor, form):
    code = form.get("id") or p.uid()
    if form.get("id"):
        p.need(p.one(conn, "SELECT id FROM play_campaigns WHERE id=?", code))
    start, end = period(form)
    title = p.text(form.get("title"), "نام کمپین", 85)
    desc = p.text(form.get("description"), "توضیح", 360)
    bonus = p.integer(form.get("bonus"), "توکن اضافه", 0, 10000)
    members = list(dict.fromkeys(form.getlist("visitors")))
    for member in members:
        visit(conn, member)
    conn.execute(
        """INSERT INTO play_campaigns VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
        title=excluded.title,description=excluded.description,starts_on=excluded.starts_on,
        ends_on=excluded.ends_on,active=excluded.active,bonus=excluded.bonus""",
        (code, title, desc, start, end, int(bool(form.get("active"))), bonus),
    )
    conn.execute("DELETE FROM play_campaign_members WHERE campaign_id=?", (code,))
    conn.executemany("INSERT INTO play_campaign_members VALUES (?,?)", ((code, i) for i in members))
    p.audit(conn, actor["id"], "campaign", f"کمپین «{title}» ذخیره شد.")
    return code


def save_game(conn, actor, form):
    key = p.choice(form.get("id"), p.ART, "بازی")
    title = p.text(form.get("title"), "نام بازی", 85)
    desc = p.text(form.get("description"), "توضیح", 240)
    minimum = p.integer(form.get("min_players"), "حداقل بازیکن", 3 if key == "shir" else 2, 8)
    maximum = p.integer(form.get("max_players"), "حداکثر بازیکن", minimum, 8)
    cost = p.integer(form.get("cost"), "هزینهٔ هر بازیکن", 0, 1000)
    reward = p.integer(form.get("reward"), "امتیاز بازی", 0, 1000)
    duration = p.integer(form.get("duration"), "زمان هر مرحله", 10, 300)
    rounds = 1 if key == "shir" else p.integer(form.get("rounds"), "تعداد نوبت", 1, 8)
    conn.execute(
        """UPDATE play_games SET title=?,description=?,enabled=?,cost=?,reward=?,
        min_players=?,max_players=?,duration=?,rounds=? WHERE key=?""",
        (
            title,
            desc,
            int(bool(form.get("active"))),
            cost,
            reward,
            minimum,
            maximum,
            duration,
            rounds,
            key,
        ),
    )
    p.audit(conn, actor["id"], "game", f"تنظیمات «{title}» تغییر کرد.")


def save_content(conn, actor, form):
    collection = p.choice(form.get("collection"), ("cards", "questions", "words"), "مجموعه")
    code = form.get("id") or p.uid()
    archived = int(bool(form.get("archived")))
    if collection == "cards":
        if form.get("id"):
            p.need(p.one(conn, "SELECT id FROM play_cards WHERE id=?", code))
        title = p.text(form.get("label"), "عنوان کارت", 75)
        conn.execute(
            """INSERT INTO play_cards VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
            kind=excluded.kind,label=excluded.label,detail=excluded.detail,archived=excluded.archived""",
            (
                code,
                p.choice(form.get("kind"), p.CARDS, "نوع کارت"),
                title,
                p.text(form.get("detail"), "توضیح کارت", 200),
                archived,
            ),
        )
    elif collection == "questions":
        if form.get("id"):
            p.need(p.one(conn, "SELECT id FROM play_questions WHERE id=?", code))
        title = p.text(form.get("prompt"), "پرسش", 200)
        opts = [p.text(form.get(f"option{i}"), f"گزینهٔ {p.fmt(i + 1)}", 90) for i in range(4)]
        if len(set(opts)) != 4:
            raise p.PlayError("چهار گزینه باید متفاوت باشند.")
        conn.execute(
            """INSERT INTO play_questions VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
            prompt=excluded.prompt,category=excluded.category,difficulty=excluded.difficulty,
            options_json=excluded.options_json,answer=excluded.answer,archived=excluded.archived""",
            (
                code,
                title,
                p.text(form.get("category"), "دسته", 60),
                p.choice(form.get("difficulty"), p.DIFFICULTIES, "سختی"),
                p.dump(opts),
                p.integer(form.get("answer"), "شمارهٔ پاسخ", 1, 4) - 1,
                archived,
            ),
        )
    else:
        if form.get("id"):
            p.need(p.one(conn, "SELECT id FROM play_words WHERE id=?", code))
        title = p.text(form.get("word"), "واژه", 45)
        banned = [
            i.strip()
            for i in p.text(form.get("forbidden"), "واژه‌های ممنوعه", 160)
            .replace(",", "،")
            .split("،")
            if i.strip()
        ]
        if not 1 <= len(banned) <= 6:
            raise p.PlayError("یک تا شش واژهٔ ممنوعه را با ویرگول جدا کنید.")
        conn.execute(
            """INSERT INTO play_words VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
            word=excluded.word,hint=excluded.hint,category=excluded.category,
            forbidden_json=excluded.forbidden_json,archived=excluded.archived""",
            (
                code,
                title,
                p.text(form.get("hint"), "راهنما", 180),
                p.text(form.get("category"), "دسته", 60),
                p.dump(banned),
                archived,
            ),
        )
    p.audit(conn, actor["id"], "content", f"محتوای «{title}» ذخیره شد.")


def save_mission(conn, actor, form):
    code = form.get("id") or p.uid()
    if form.get("id"):
        p.need(p.one(conn, "SELECT id FROM play_missions WHERE id=?", code))
    start, end = period(form)
    audience = p.choice(form.get("audience"), ("member", "visitor"), "مخاطب")
    metric = p.choice(
        form.get("metric"),
        ("games",) if audience == "member" else ("sales", "amount"),
        "معیار مأموریت",
    )
    title = p.text(form.get("title"), "عنوان مأموریت", 85)
    campaign = form.get("campaign") or None
    if campaign:
        p.need(p.one(conn, "SELECT id FROM play_campaigns WHERE id=?", campaign))
    goal = p.integer(form.get("goal"), "هدف", 1, 999_999_999_999)
    points = p.integer(form.get("points"), "امتیاز", 0, 10000)
    conn.execute(
        """INSERT INTO play_missions VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET title=excluded.title,description=excluded.description,
        audience=excluded.audience,metric=excluded.metric,goal=excluded.goal,points=excluded.points,
        campaign_id=excluded.campaign_id,starts_on=excluded.starts_on,ends_on=excluded.ends_on,
        active=excluded.active""",
        (
            code,
            title,
            p.text(form.get("description"), "توضیح", 220),
            audience,
            metric,
            goal,
            points,
            campaign,
            start,
            end,
            int(bool(form.get("active"))),
        ),
    )
    p.audit(conn, actor["id"], "mission", f"مأموریت «{title}» ذخیره شد.")


def claim(conn, actor, code):
    require(actor, "member", "visitor")
    mission = next((item for item in p.missions(conn, actor) if item["id"] == code), None)
    if not mission or (not mission["ready"] and not mission["claimed"]):
        raise p.PlayError("مأموریت هنوز برای دریافت امتیاز آماده نیست.", 409)
    if mission["claimed"]:
        return
    conn.execute("INSERT INTO play_claims VALUES (?,?,?)", (code, actor["id"], p.now()))
    score_type = "mission" if actor["role"] == "member" else "sales_mission"
    p.add_score(conn, actor["id"], actor["family_id"], score_type, code, mission["points"])
    if actor["role"] == "member":
        p.grant_badge(conn, actor["id"], "mission")
    p.audit(conn, actor["id"], "mission", f"مأموریت «{mission['title']}» تکمیل شد.")


def save_competition(conn, actor, form):
    code = form.get("id") or p.uid()
    if form.get("id"):
        p.need(p.one(conn, "SELECT id FROM play_competitions WHERE id=?", code))
    start, end = period(form)
    kind = p.choice(form.get("kind"), ("community", "rank"), "نوع رقابت")
    title = p.text(form.get("title"), "نام رقابت", 95)
    reward = (form.get("reward") or None) if kind == "community" else None
    if reward:
        p.need(p.one(conn, "SELECT code FROM play_rewards WHERE code=?", reward))
    target = p.integer(form.get("target"), "هدف جمعی", 1, 100_000) if kind == "community" else 1
    conn.execute(
        """INSERT INTO play_competitions VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET title=excluded.title,description=excluded.description,
        kind=excluded.kind,target=excluded.target,reward_code=excluded.reward_code,
        starts_on=excluded.starts_on,ends_on=excluded.ends_on,active=excluded.active""",
        (
            code,
            title,
            p.text(form.get("description"), "توضیح", 220),
            kind,
            target,
            reward,
            start,
            end,
            int(bool(form.get("active"))),
        ),
    )
    grant_community(conn)
    p.audit(conn, actor["id"], "competition", f"رقابت «{title}» ذخیره شد.")


def grant_community(conn):
    granted = []
    for item in p.competitions(conn, public=True):
        if item["kind"] != "community" or not item["reward_code"] or item["remaining"]:
            continue
        start, end = p.epoch(item["starts_on"]), p.epoch(item["ends_on"]) + 86400
        for player in p.rows(
            conn,
            """SELECT DISTINCT s.account_id FROM play_scores s
            JOIN play_results r ON r.id=s.source_id WHERE s.source_type='game'
            AND r.created_at>=? AND r.created_at<?""",
            start,
            end,
        ):
            if p.grant_badge(conn, player["account_id"], item["reward_code"], item["id"]):
                granted.append((player["account_id"], item["reward_code"]))
    return granted


def save_reward(conn, actor, form):
    code = form.get("id") or p.uid()
    if form.get("id"):
        p.need(p.one(conn, "SELECT code FROM play_rewards WHERE code=?", code))
    title = p.text(form.get("title"), "عنوان نشان", 75)
    icon = p.choice(
        form.get("icon"), ("flag", "trophy", "target", "building", "star", "medal"), "نماد"
    )
    conn.execute(
        """INSERT INTO play_rewards VALUES (?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET
        title=excluded.title,description=excluded.description,icon=excluded.icon,active=excluded.active""",
        (
            code,
            title,
            p.text(form.get("description"), "توضیح", 180),
            icon,
            int(bool(form.get("active"))),
        ),
    )
    p.audit(conn, actor["id"], "reward", f"نشان «{title}» ذخیره شد.")


def save_rule(conn, actor, form):
    unit = p.integer(form.get("unit"), "واحد فروش", 1, 999_999_999_999)
    per_unit = p.integer(form.get("per_unit"), "توکن هر واحد", 1, 10000)
    version = p.scalar(conn, "SELECT MAX(version)+1 FROM play_token_rules")
    conn.execute(
        "INSERT INTO play_token_rules VALUES (?,?,?,?,?)",
        (version, unit, per_unit, p.now(), actor["id"]),
    )
    p.audit(conn, actor["id"], "settings", f"نسخهٔ {p.fmt(version)} قانون توکن منتشر شد.")


def profile(conn, actor, form):
    name = actor["name"]
    if actor["age"] != "child" and form.get("name") is not None:
        name = p.text(form.get("name"), "نام نمایشی", 55)
    avatar = p.choice(form.get("avatar"), p.AVATARS, "آواتار")
    conn.execute("UPDATE play_accounts SET name=?,avatar=? WHERE id=?", (name, avatar, actor["id"]))


def set_scenario(conn, actor, form):
    scenario = p.choice(form.get("scenario"), ("campaign", "community"), "سناریو")
    if scenario == "campaign":
        today = p.day()
        end = today + timedelta(days=20)
        conn.execute(
            "UPDATE play_campaigns SET active=1,starts_on=?,ends_on=? WHERE id='spring'",
            (today.isoformat(), end.isoformat()),
        )
        p.audit(conn, actor["id"], "scenario", "کمپین سناریوی هم‌قدم با فروش فعال شد.")
    else:
        town = next(c for c in p.competitions(conn) if c["id"] == "town")
        today = p.day()
        if not town["starts_on"] <= today.isoformat() <= town["ends_on"]:
            conn.execute(
                "UPDATE play_competitions SET starts_on=?,ends_on=? WHERE id='town'",
                (
                    (today - timedelta(days=10)).isoformat(),
                    (today + timedelta(days=18)).isoformat(),
                ),
            )
            town = next(c for c in p.competitions(conn) if c["id"] == "town")
        conn.execute(
            "UPDATE play_competitions SET active=1,target=? WHERE id='town'",
            (town["progress"] + 1,),
        )
        p.audit(conn, actor["id"], "scenario", "هدف شهر کیلوس یک بازی تا تکمیل فاصله دارد.")

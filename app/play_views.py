"""Read-side projections for the server-rendered Kilos Play screens."""

from __future__ import annotations

import json
from datetime import timedelta

from app import play_data as p
from app import play_rooms as rooms

FAMILY_NAV = {
    "home": ("خانه", "home"),
    "games": ("بازی‌ها", "game"),
    "rooms": ("اتاق‌های بازی", "doors"),
    "competitions": ("رقابت‌ها", "trophy"),
    "missions": ("مأموریت‌ها", "target"),
    "wallet": ("کیف پول خانواده", "wallet"),
    "avatars": ("آواتارها", "sparkles"),
    "achievements": ("دستاوردها", "medal"),
    "members": ("اعضای خانواده", "users"),
    "profile": ("حساب من", "profile"),
    "notices": ("اعلان‌ها", "bell"),
}
VISITOR_NAV = {
    "home": ("داشبورد فروش", "home"),
    "sales": ("عملکرد فروش", "chart"),
    "wallet": ("کیف توکن", "wallet"),
    "missions": ("مأموریت‌ها", "target"),
    "leaderboard": ("رتبه‌بندی", "trophy"),
    "family": ("خانوادهٔ من", "users"),
    "campaigns": ("کمپین‌ها", "flag"),
    "profile": ("حساب من", "profile"),
    "notices": ("اعلان‌ها", "bell"),
}
ADMIN_NAV = {
    "dashboard": ("داشبورد", "dashboard"),
    "visitors": ("ویزیتورها", "profile"),
    "families": ("خانواده‌ها", "users"),
    "sales": ("فروش نمایشی", "chart"),
    "campaigns": ("کمپین‌ها", "flag"),
    "games": ("بازی‌ها", "game"),
    "content": ("محتوای بازی", "cards"),
    "missions": ("مأموریت‌ها", "target"),
    "competitions": ("رقابت‌ها", "trophy"),
    "wallets": ("کیف‌های توکن", "wallet"),
    "transactions": ("تراکنش‌ها", "arrows"),
    "rewards": ("پاداش‌ها", "medal"),
    "reports": ("گزارش‌ها", "reports"),
    "control": ("مرکز کنترل دمو", "flask"),
    "settings": ("تنظیمات", "settings"),
}
NAV = {"family": FAMILY_NAV, "visitor": VISITOR_NAV, "admin": ADMIN_NAV}
AREAS = {"member": "family", "visitor": "visitor", "admin": "admin"}
AREA_LABEL = {"family": "باشگاه خانواده", "visitor": "پنل ویزیتور", "admin": "پنل مدیریت"}
ROOM_LABELS = {
    "lobby": "در انتظار بازیکن",
    "build": "ساخت پیشنهاد",
    "pitch": "معرفی پیشنهادها",
    "vote": "رأی‌گیری",
    "question": "پرسش",
    "feedback": "پاسخ نوبت",
    "clue": "ساخت سرنخ",
    "guess": "حدس واژه",
    "finished": "تمام‌شده",
    "closed": "بسته‌شده",
}
GROUPS = {
    "family": (
        ("بازی و رقابت", ("home", "games", "rooms", "competitions", "missions")),
        ("خانوادهٔ من", ("wallet", "avatars", "achievements", "members", "profile")),
    ),
    "visitor": (
        ("میز کار", ("home", "sales", "wallet", "missions", "leaderboard")),
        ("مدیریت حساب", ("family", "campaigns", "profile")),
    ),
    "admin": (
        ("نمای کلی", ("dashboard", "reports", "control")),
        ("فروش و خانواده", ("visitors", "families", "sales", "campaigns")),
        ("باشگاه بازی", ("games", "content", "missions", "competitions", "rewards")),
        ("امور مالی و سیستم", ("wallets", "transactions", "settings")),
    ),
}
PHONE = {
    "family": ("home", "games", "rooms", "wallet"),
    "visitor": ("home", "sales", "wallet", "family"),
    "admin": (),
}


def landing(actor):
    area = AREAS[actor["role"]]
    return f"/play/{area}/{'dashboard' if area == 'admin' else 'home'}"


def get_game(conn, game):
    return p.need(p.one(conn, "SELECT * FROM play_games WHERE key=?", game), "این بازی پیدا نشد.")


def games(conn, public=False):
    return p.rows(conn, "SELECT * FROM play_games WHERE enabled=1 OR ?=0 ORDER BY rowid", public)


def game_boards(conn, key, family):
    """Publish family totals, but only show individual ranks within the viewer's family."""
    per_family = p.rows(
        conn,
        """SELECT f.id,f.name,SUM(s.amount) AS score,COUNT(s.id) AS played
        FROM play_scores s JOIN play_results r ON r.id=s.source_id
        JOIN play_families f ON f.id=s.family_id
        WHERE s.source_type='game' AND r.game_key=? GROUP BY f.id
        ORDER BY score DESC,played DESC,f.name LIMIT 30""",
        key,
    )
    per_member = p.rows(
        conn,
        """SELECT a.id,a.name,a.avatar,SUM(s.amount) AS score,COUNT(s.id) AS played
        FROM play_scores s JOIN play_results r ON r.id=s.source_id
        JOIN play_accounts a ON a.id=s.account_id
        WHERE s.source_type='game' AND r.game_key=? AND a.family_id=? AND a.active=1
        GROUP BY a.id ORDER BY score DESC,played DESC,a.name""",
        key,
        family,
    )
    return {"families": per_family, "players": per_member}


def categories(conn):
    return [
        i["category"]
        for i in p.rows(
            conn,
            """SELECT DISTINCT category FROM play_questions
        WHERE archived=0 ORDER BY category""",
        )
    ]


def notices(conn, who):
    return p.rows(
        conn,
        """SELECT * FROM play_notices WHERE account_id=?
        ORDER BY created_at DESC,rowid DESC LIMIT 40""",
        who,
    )


def unread(conn, who):
    return p.scalar(
        conn, "SELECT COUNT(*) FROM play_notices WHERE account_id=? AND read_at IS NULL", who
    )


def invites(conn, family):
    items = p.rows(
        conn,
        """SELECT i.*,a.name AS used_name FROM play_invites i
        LEFT JOIN play_accounts a ON i.used_by=a.id WHERE i.family_id=?
        ORDER BY i.expires_at DESC,i.rowid DESC LIMIT 30""",
        family,
    )
    for item in items:
        item["usable"] = (
            not item["revoked"] and not item["used_by"] and item["expires_at"] > p.now()
        )
    return items


def paginate(items, raw_page, size=24):
    try:
        page = max(1, int(raw_page or 1))
    except ValueError:
        page = 1
    pages = max(1, (len(items) + size - 1) // size)
    page = min(page, pages)
    return {
        "items": items[(page - 1) * size : page * size],
        "current": page,
        "pages": pages,
        "total": len(items),
    }


def actor_context(conn, actor, area, page):
    info = {
        "actor": actor,
        "area": area,
        "current": page,
        "nav": NAV[area],
        "groups": GROUPS[area],
        "phone": PHONE[area],
        "area_label": AREA_LABEL[area],
        "today": p.day().isoformat(),
        "request_id": p.uid(),
        "request_id_extra": p.uid(),
    }
    if actor:
        info["unread"] = unread(conn, actor["id"])
        if actor["family_id"]:
            info["family"] = p.one(
                conn, "SELECT * FROM play_families WHERE id=?", actor["family_id"]
            )
            info["wallet_balance"] = p.balance(conn, actor["family_id"])
    return info


def family_context(conn, actor, page, query):
    family = actor["family_id"]
    info: dict = {}
    if page in {"home", "games"}:
        info.update(games=games(conn, True))
    if page in {"home", "competitions"}:
        events = p.competitions(conn, family, public=True)
        period = "month" if query.get("period") == "month" else "week"
        ranking = p.ranking(conn, period)
        info.update(
            events=events,
            community=next((i for i in events if i["kind"] == "community"), None),
            ranking=ranking,
            period=period,
            rank=next(i["rank"] for i in ranking if i["id"] == family),
        )
    if page in {"home", "missions"}:
        info["missions"] = p.missions(conn, actor)
    if page in {"home", "achievements"}:
        info["badges"] = p.achievements(conn, family, actor["id"] if query.get("mine") else None)
    if page == "home":
        info["stats"] = p.family_stats(conn, family)
        info["signature"] = next((g for g in info["games"] if g["key"] == "shir"), None)
    if page in {"games", "rooms", "profile"}:
        info["history"] = p.history(conn, family)
        if page == "profile":
            info["history"] = [
                r
                for r in info["history"]
                if any(a["id"] == actor["id"] for a in r["result"]["scores"])
            ]
    if page == "rooms":
        info["rooms"] = rooms.list_rooms(conn, family, viewer=actor["id"])
    if page == "members":
        info.update(
            members=p.family_members(conn, family),
            invites=invites(conn, family) if actor["age"] == "adult" else [],
        )
    if page == "wallet":
        info.update(transactions=p.ledger(conn, family, query.get("tx")), tx=query.get("tx"))
    if page == "notices":
        info["notices"] = notices(conn, actor["id"])
    return info


def visitor_context(conn, actor, page, query):
    visitor, family = actor["id"], actor["family_id"]
    info: dict = {}
    if page in {"home", "sales", "wallet"}:
        info["stats"] = p.visitor_stats(conn, actor)
    if page in {"home", "family"}:
        info.update(
            members=p.family_members(conn, family),
            history=p.history(conn, family),
            invites=invites(conn, family),
        )
    if page in {"home", "missions"}:
        info["missions"] = p.missions(conn, actor)
        info["mission_score"] = p.scalar(
            conn,
            """SELECT COALESCE(SUM(amount),0) FROM play_scores
            WHERE source_type='sales_mission' AND account_id=?""",
            visitor,
        )
    if page in {"home", "sales"}:
        info["sales"] = p.sales_list(conn, visitor)
    if page == "wallet":
        info.update(transactions=p.ledger(conn, family, query.get("tx")), tx=query.get("tx"))
    if page == "campaigns":
        info["campaigns"] = p.campaigns(conn, visitor)
    if page == "leaderboard":
        info["ranking"] = p.visitor_ranks(conn)
    if page == "notices":
        info["notices"] = notices(conn, visitor)
    return info


def analytics(conn, span=7):
    today = p.day()
    first = today - timedelta(days=span - 1)
    aggregate = p.one(
        conn,
        """SELECT COALESCE(SUM(CASE WHEN amount>0 THEN amount ELSE 0 END),0) AS issued,
        COALESCE(SUM(CASE WHEN kind='entry' THEN -amount ELSE 0 END),0) AS spent
        FROM play_wallet_events""",
    )
    counts = p.one(
        conn,
        """SELECT
        (SELECT COUNT(*) FROM play_accounts WHERE role='visitor') AS visitors,
        (SELECT COUNT(*) FROM play_families) AS families,
        (SELECT COUNT(*) FROM play_accounts WHERE role='member' AND active=1) AS members,
        (SELECT COUNT(*) FROM play_campaigns
            WHERE active=1 AND ? BETWEEN starts_on AND ends_on) AS campaigns,
        (SELECT COUNT(*) FROM play_results) AS played,
        (SELECT COUNT(*) FROM play_sales WHERE approved_at IS NULL) AS pending""",
        today.isoformat(),
    )
    counts.update(aggregate)
    daily = p.rows(
        conn,
        """SELECT date(created_at+12600,'unixepoch') AS date,
        SUM(CASE WHEN amount>0 THEN amount ELSE 0 END) AS issued,
        SUM(CASE WHEN kind='entry' THEN -amount ELSE 0 END) AS spent
        FROM play_wallet_events WHERE created_at>=? GROUP BY date""",
        p.epoch(first),
    )
    mapped = {item["date"]: item for item in daily}
    chart = []
    for i in range(span):
        date = (first + timedelta(days=i)).isoformat()
        chart.append(mapped.get(date, dict(date=date, issued=0, spent=0)))
    ceiling = max(1, *(max(i["issued"], i["spent"]) for i in chart))
    for item in chart:
        item.update(a=p.percent(item["issued"], ceiling), b=p.percent(item["spent"], ceiling))
    popular = p.rows(
        conn,
        """SELECT g.key,g.title,COUNT(r.id) AS played FROM play_games g
        LEFT JOIN play_results r ON r.game_key=g.key GROUP BY g.key ORDER BY played DESC,g.key""",
    )
    return dict(
        kpis=counts,
        chart=chart,
        popular=popular,
        ranking=p.ranking(conn, "week"),
        history=p.history(conn),
        activity=p.rows(
            conn,
            """SELECT t.*,a.name AS actor FROM play_audit t
                    LEFT JOIN play_accounts a ON t.actor_id=a.id
                    ORDER BY t.created_at DESC,t.rowid DESC LIMIT 30""",
        ),
    )


def visitors(conn, query=""):
    return p.rows(
        conn,
        """SELECT a.*,f.name AS family,
        (SELECT COALESCE(SUM(amount),0) FROM play_wallet_events e
            WHERE e.family_id=f.id) AS balance,
        (SELECT COUNT(*) FROM play_accounts m
            WHERE m.family_id=f.id AND m.role='member' AND m.active=1) AS members
        FROM play_accounts a JOIN play_families f ON a.family_id=f.id WHERE a.role='visitor'
        AND (?='' OR instr(a.name,?)>0 OR instr(a.region,?)>0)
        ORDER BY a.created_at DESC,a.rowid""",
        query,
        query,
        query,
    )


def families(conn):
    return p.rows(
        conn,
        """SELECT f.*,a.name AS visitor,
        (SELECT COALESCE(SUM(amount),0) FROM play_wallet_events e
            WHERE e.family_id=f.id) AS balance,
        (SELECT COUNT(*) FROM play_accounts m
            WHERE m.family_id=f.id AND m.role='member' AND m.active=1) AS members,
        (SELECT COUNT(*) FROM play_results r WHERE r.family_id=f.id) AS played FROM play_families f
        LEFT JOIN play_accounts a ON f.id=a.family_id AND a.role='visitor' ORDER BY f.rowid""",
    )


def content(conn, collection, filtering):
    if collection == "questions":
        items = p.rows(conn, "SELECT * FROM play_questions ORDER BY archived,rowid")
        for item in items:
            item["options"] = json.loads(item["options_json"])
            item["answer_text"] = item["options"][item["answer"]]
    elif collection == "words":
        items = p.rows(conn, "SELECT * FROM play_words ORDER BY archived,rowid")
        for item in items:
            item["forbidden"] = "، ".join(json.loads(item["forbidden_json"]))
    else:
        items = p.rows(conn, "SELECT * FROM play_cards ORDER BY archived,rowid")
    return (
        items
        if not filtering
        else [i for i in items if i.get("kind", i.get("category")) == filtering]
    )


def admin_context(conn, page, query):
    info: dict = {"create": query.get("new") == "1"}
    selected = query.get("edit")
    if page in {"dashboard", "reports", "control"}:
        info.update(analytics(conn, 30 if query.get("span") == "30" else 7))
    if page == "dashboard":
        info["pending"] = [s for s in p.sales_list(conn) if s["approved_at"] is None]
    if page in {"sales", "control"}:
        info.update(sales=p.sales_list(conn), visitors=visitors(conn), campaigns=p.campaigns(conn))
        if page == "control":
            info.update(
                pending=[s for s in info["sales"] if s["approved_at"] is None],
                rooms=rooms.list_rooms(conn, p.PRIMARY_FAMILY),
                member=p.one(
                    conn, "SELECT * FROM play_accounts WHERE id=? AND active=1", p.PRIMARY
                ),
                primary=p.one(
                    conn, "SELECT * FROM play_accounts WHERE id=? AND active=1", p.VISITOR
                ),
                games=games(conn, True),
                primary_balance=p.balance(conn, p.PRIMARY_FAMILY),
                family_list=families(conn),
            )
    if page == "visitors":
        search = str(query.get("q") or "").strip()[:70]
        info.update(visitors=visitors(conn, search), search=search)
        if selected:
            from app.play_ops import visit

            entry = visit(conn, selected)
            edit_family = entry["family_id"]
            info.update(
                edit=entry,
                stats=p.visitor_stats(conn, entry),
                sales=p.sales_list(conn, selected, 12),
                members=p.family_members(conn, edit_family),
                txs=p.ledger(conn, edit_family, limit=10),
                balance=p.balance(conn, edit_family),
                history=p.history(conn, edit_family),
            )
    if page in {"families", "wallets"}:
        all_families = families(conn)
        info["family_list"] = all_families
        if selected:
            fam = p.need(next((i for i in all_families if i["id"] == selected), None))
            info.update(
                edit=fam,
                members=p.family_members(conn, selected, False),
                invites=invites(conn, selected),
                txs=p.ledger(conn, selected),
                history=p.history(conn, selected),
            )
            if query.get("member"):
                info["edit_member"] = p.need(
                    next((i for i in info["members"] if i["id"] == query.get("member")), None)
                )
    if page == "transactions":
        family = query.get("family") or None
        new = query.get("tx") or None
        pages = paginate(p.ledger(conn, family, new, -1), query.get("p"), size=30)
        info.update(
            transactions=pages["items"],
            tx_pages=pages,
            family_list=families(conn),
            family_sel=family,
            tx=new,
        )
    if page == "campaigns":
        items = p.campaigns(conn)
        info.update(campaigns=items, visitors=visitors(conn))
        if selected:
            info["edit"] = p.need(next((i for i in items if i["id"] == selected), None))
            info["selected_visitors"] = [
                i["account_id"]
                for i in p.rows(
                    conn,
                    "SELECT account_id FROM play_campaign_members WHERE campaign_id=?",
                    selected,
                )
            ]
    if page == "games":
        info["games"] = games(conn)
        if selected:
            info["edit"] = get_game(conn, selected)
    if page == "content":
        collection = query.get("tab") if query.get("tab") in ("questions", "words") else "cards"
        all_items = content(conn, collection, None)
        filtering = query.get("category") or ""
        visible = (
            all_items
            if not filtering
            else [i for i in all_items if i.get("kind", i.get("category")) == filtering]
        )
        info.update(
            collection=collection,
            grouped=paginate(visible, query.get("p")),
            filter=filtering,
            content_categories=(
                p.CARDS
                if collection == "cards"
                else {i["category"]: i["category"] for i in all_items}
            ),
        )
        if selected:
            info["edit"] = p.need(next((i for i in all_items if i["id"] == selected), None))
    if page == "missions":
        items = p.rows(
            conn,
            """SELECT m.*,c.title AS campaign,
            (SELECT COUNT(*) FROM play_claims r WHERE r.mission_id=m.id) AS claims
            FROM play_missions m LEFT JOIN play_campaigns c ON m.campaign_id=c.id
            ORDER BY m.rowid""",
        )
        info.update(missions=items, campaigns=p.campaigns(conn))
        if selected:
            info["edit"] = p.need(next((i for i in items if i["id"] == selected), None))
    if page == "competitions":
        items = p.competitions(conn)
        info.update(events=items, rewards=p.rows(conn, "SELECT * FROM play_rewards ORDER BY rowid"))
        if selected:
            info["edit"] = p.need(next((i for i in items if i["id"] == selected), None))
    if page == "rewards":
        items = p.rows(
            conn,
            """SELECT r.*,(SELECT COUNT(*) FROM play_badges b WHERE b.code=r.code) AS count
            FROM play_rewards r ORDER BY r.rowid""",
        )
        info["rewards"] = items
        if selected:
            info["edit"] = p.need(next((i for i in items if i["code"] == selected), None))
    if page == "settings":
        info["rules"] = p.rows(conn, "SELECT * FROM play_token_rules ORDER BY version DESC")
    return info

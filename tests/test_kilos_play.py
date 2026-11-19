"""Kilos Play vertical slices: independent sessions, immutable ledger and online turns."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import db
from app import play_data as p
from app.main import create_app
from app.play import COOKIE

JSON = {"Accept": "application/json"}
RETURN = "/play/admin/control"
BASE_URL = "https://play.test"


def new_client(app):
    return TestClient(app, base_url=BASE_URL)


def csrf_from(response):
    return re.search(r'<meta name="csrf-token" content="([a-f0-9]+)"', response.text)[1]


def admin_sign_in(client, settings):
    response = client.post("/play/admin/login", data={"operator_key": settings.demo_operator_key})
    assert response.status_code == 200, response.text
    return csrf_from(response)


def entry_code(issuer, account):
    response = issuer.client.post(
        "/play/entry-code", data={"csrf": issuer.csrf, "account": account}
    )
    assert response.status_code == 200, response.text
    return re.search(r'value="([a-zA-Z0-9_-]{43})" data-issued-code', response.text)[1]


class Persona:
    def __init__(self, app, account, *, settings, issuer=None):
        self.client = new_client(app)
        if account == p.ADMIN:
            self.csrf = admin_sign_in(self.client, settings)
        else:
            response = self.client.post(
                "/play/enter", data={"entry_code": entry_code(issuer, account)}
            )
            assert response.status_code == 200, response.text
            self.csrf = csrf_from(response)
        self.account = account

    def get(self, path):
        return self.client.get(path)

    def act(self, verb, *, status=303, **fields):
        response = self.client.post(
            "/play/action",
            data={
                "csrf": self.csrf,
                "action": verb,
                "return": RETURN,
                **fields,
            },
            follow_redirects=False,
        )
        assert response.status_code == status, response.text
        return response

    def state(self, room):
        response = self.client.get(f"/play/state/{room}", headers=JSON)
        assert response.status_code == 200, response.text
        return response.json()

    def move(self, room, verb, *, status=200, key=None, **fields):
        state = self.state(room)
        response = self.client.post(
            "/play/action",
            headers=JSON,
            data={
                "csrf": self.csrf,
                "action": "room_move",
                "move": verb,
                "code": room,
                "phase_key": key or state["phase_key"],
                "move_seq": state["move_seq"],
                **fields,
            },
        )
        assert response.status_code == status, response.text
        return response.json()


@pytest.fixture
def demos(play_client, play_settings):
    issuer = Persona(play_client.app, p.ADMIN, settings=play_settings)
    return lambda account: Persona(play_client.app, account, settings=play_settings, issuer=issuer)


@pytest.fixture
def play_conn(play_client):
    path = next(
        route for route in play_client.app.routes if route.path == "/play"
    ).app.state.db_path
    with closing(db.connect(path)) as conn:
        yield conn


def launch(host, game, others=(), **options):
    response = host.act("create_room", game=game, request_id=p.uid(), **options)
    room = response.headers["location"].split("/")[-1]
    assert len(room) == 6
    for player in others:
        assert player.act("join_room", code=room).headers["location"].endswith(room)
    for player in (host, *others):
        player.move(room, "ready", value="1")
    return room


def engine_room(conn, room):
    return json.loads(p.scalar(conn, "SELECT state_json FROM play_rooms WHERE code=?", room))


def test_fa_routes_and_role_guards(play_client, demos):
    html = play_client.get("/")
    assert 'lang="fa" dir="rtl"' in html.text
    assert "محیط نمایشی – اطلاعات این محیط واقعی نیست." in html.text
    assert html.url.path == "/play/entrance"
    assert not play_client.cookies.get(COOKIE)
    profiles = {
        "family": (
            p.PRIMARY,
            "home games rooms competitions missions wallet avatars achievements "
            "members profile notices",
        ),
        "visitor": (
            p.VISITOR,
            "home sales wallet missions leaderboard family campaigns profile notices",
        ),
        "admin": (
            p.ADMIN,
            "dashboard visitors families sales campaigns games content missions "
            "competitions wallets transactions rewards reports settings control",
        ),
    }
    for area, (account, paths) in profiles.items():
        persona = demos(account)
        for page in paths.split():
            response = persona.get(f"/play/{area}/{page}")
            assert response.status_code == 200, page
            assert 'lang="fa" dir="rtl"' in response.text
    member = demos(p.PRIMARY)
    assert "خانوادهٔ رضایی" in member.get("/play/family/home").text
    assert member.get("/play/admin/dashboard").status_code == 403
    member.act("approve", id="pending-ali", status=403)
    blocked = play_client.post(
        "/play/enter", headers={"origin": "https://example.test"}, data={"account": p.ADMIN}
    )
    assert blocked.status_code == 403
    assert play_client.get("/login", follow_redirects=False).headers["location"] == "/play/entrance"


def test_sales_ledger_connected_and_versioned(demos, play_conn):
    admin, visitor, family = (demos(key) for key in (p.ADMIN, p.VISITOR, p.PRIMARY))
    assert p.balance(play_conn, p.PRIMARY_FAMILY) == 128
    visitor.act("approve", id="pending-ali", status=403)
    assert "۷۸٪" in visitor.get("/play/visitor/home").text
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(admin.act, "approve", id="pending-ali") for _ in range(2)]
        paths = {future.result().headers["location"].split("done=")[-1] for future in futures}
        assert paths == {"approve", "approved"}
    assert p.balance(play_conn, p.PRIMARY_FAMILY) == 172
    assert "۱۰۰٪" in visitor.get("/play/visitor/home").text
    assert "فروش تأیید شد" in visitor.get("/play/visitor/notices").text
    assert family.get("/play/pulse").json()["balance"] == 172
    assert (
        p.scalar(play_conn, "SELECT COUNT(*) FROM play_wallet_events WHERE source_id='pending-ali'")
        == 1
    )
    assert (
        p.scalar(play_conn, "SELECT COUNT(*) FROM play_notices WHERE account_id=?", p.VISITOR) == 1
    )

    admin.act("rule", unit="۱٬۰۰۰٬۰۰۰", per_unit="۳")
    sale = dict(
        visitor=p.VISITOR,
        amount="4500000",
        note="فروش با پاداش کمپین",
        sold_on=p.day().isoformat(),
        campaign="spring",
        request_id=p.uid(),
    )
    admin.act("sale", **sale)
    admin.act("sale", **sale)
    admin.act("sale", **{**sale, "amount": "5000000"}, status=409)
    saved = p.one(play_conn, "SELECT * FROM play_sales WHERE request_id=?", sale["request_id"])
    admin.act("approve", id=saved["id"])
    assert p.balance(play_conn, p.PRIMARY_FAMILY) == 189  # 4 complete units × 3 + 5 campaign.
    assert p.scalar(play_conn, "SELECT rule_version FROM play_sales WHERE id=?", saved["id"]) == 2
    assert p.scalar(play_conn, "SELECT token_amount FROM play_sales WHERE id='pending-ali'") == 44
    assert "فروش با پاداش کمپین" in admin.get("/play/admin/transactions?family=family-rezaei").text
    assert admin.get("/play/admin/export").headers["content-type"].startswith("text/csv")


def test_admin_manages_resources_and_configuration(demos, play_conn):
    admin = demos(p.ADMIN)
    form = dict(
        name="مهسا کیانی", family="خانوادهٔ کیانی", region="گیلان", target="90000000", active="1"
    )
    admin.act("visitor", **form)
    account = p.one(play_conn, "SELECT * FROM play_accounts WHERE name=?", form["name"])
    admin.act("visitor", id=account["id"], name="مهسا کیان", region="البرز", target="110000000")
    assert p.scalar(play_conn, "SELECT active FROM play_accounts WHERE id=?", account["id"]) == 0
    admin.act("family", family=account["family_id"], name="خانوادهٔ تازه")
    admin.act("member", family=account["family_id"], name="رستا", age="child", avatar="panda")
    child = p.one(play_conn, "SELECT * FROM play_accounts WHERE name='رستا'")
    admin.act("member", id=child["id"], family=account["family_id"], set_active="0")
    admin.act("member", id=child["id"], family=account["family_id"], set_active="0")
    assert p.scalar(play_conn, "SELECT active FROM play_accounts WHERE id=?", child["id"]) == 0

    dates = dict(starts_on=p.day().isoformat(), ends_on=p.day().isoformat())
    form = dict(
        title="کمپین آزمون", description="همراه فروشگاه‌ها", bonus="7", visitors=p.VISITOR, **dates
    )
    response = admin.act("campaign", **form)
    code = response.headers["location"].split("edit=")[1].split("&")[0]
    admin.act("campaign", id=code, active="1", **form)
    assert "کمپین آزمون" in demos(p.VISITOR).get("/play/visitor/campaigns").text
    admin.act(
        "mission",
        title="گام آزمون",
        description="خرید تأییدشده",
        audience="visitor",
        metric="sales",
        goal="1",
        points="20",
        campaign=code,
        active="1",
        **dates,
    )
    assert "گام آزمون" in demos(p.VISITOR).get("/play/visitor/missions").text
    admin.act("content", collection="cards", label="کارت آزمون", kind="event", detail="بازی تازه")
    card = p.one(play_conn, "SELECT * FROM play_cards WHERE label='کارت آزمون'")
    preview = admin.get(f"/play/admin/content?tab=cards&edit={card['id']}")
    assert "کارت آزمون" in preview.text and "پیش‌نمایش" in preview.text
    admin.act(
        "content",
        collection="cards",
        label="کارت ویرایش‌شده",
        kind="event",
        detail="آزمایش بایگانی",
        archived="1",
        id=card["id"],
    )
    assert p.scalar(play_conn, "SELECT archived FROM play_cards WHERE id=?", card["id"]) == 1
    admin.act(
        "content",
        collection="questions",
        prompt="پرسش تازه؟",
        category="آزمون",
        difficulty="hard",
        option0="یک",
        option1="دو",
        option2="سه",
        option3="چهار",
        answer="2",
    )
    admin.act(
        "content",
        collection="words",
        word="قلم",
        category="آزمون",
        hint="با آن می‌نویسیم",
        forbidden="نوشتن، مرکب",
    )
    admin.act(
        "game",
        id="shir",
        title="شیر و مرغ کیلوس",
        description="کارت‌ها",
        cost="9",
        reward="60",
        min_players="3",
        max_players="8",
        duration="60",
    )
    assert p.scalar(play_conn, "SELECT enabled FROM play_games WHERE key='shir'") == 0
    assert "/play/family/game/shir" not in demos(p.PRIMARY).get("/play/family/games").text


def test_adjustment_is_idempotent_and_reset_is_isolated(demos, play_conn, settings):
    admin, member = demos(p.ADMIN), demos(p.PRIMARY)
    base = dict(family=p.PRIMARY_FAMILY, reason="تست گردش", request_id=p.uid())
    admin.act("adjust", kind="issue", amount="18", **base)
    admin.act("adjust", kind="issue", amount="18", **base)
    admin.act("adjust", kind="deduct", amount="18", **base, status=409)
    admin.act(
        "adjust", kind="correct", amount="-9000", **{**base, "request_id": p.uid()}, status=409
    )
    assert p.balance(play_conn, p.PRIMARY_FAMILY) == 146
    db.init_db(settings.db_path, settings.evidence_dir)
    with closing(db.connect(settings.db_path)) as legacy:
        with legacy:
            legacy.execute("UPDATE users SET full_name='کاربر قدیمی دست‌نخورده' WHERE role='admin'")
        member.act("reset", confirm="بازنشانی", status=403)
        admin.act("reset", confirm="نامعتبر", status=409)
        assert admin.act("reset", confirm="بازنشانی").headers["location"].endswith("done=reset")
        assert member.get("/play/pulse").status_code == 401  # Previous sessions revoked.
        assert admin.get("/play/admin/control").status_code == 200
        assert p.balance(play_conn, p.PRIMARY_FAMILY) == 128
        assert p.scalar(play_conn, "SELECT COUNT(*) FROM play_families") == 10
        assert (
            p.scalar(legacy, "SELECT full_name FROM users WHERE role='admin'")
            == "کاربر قدیمی دست‌نخورده"
        )


def test_private_family_invitation_and_child_scope(demos, play_client, play_conn):
    adult, child = demos(p.PRIMARY), demos("member-arin")
    child.act("invite", family=p.PRIMARY_FAMILY, age="adult", status=403)
    adult.act("invite", family="family-mina", age="adult", status=403)
    adult.act("invite", family=p.PRIMARY_FAMILY, age="child")
    invite = p.scalar(
        play_conn, "SELECT code FROM play_invites WHERE family_id=?", p.PRIMARY_FAMILY
    )
    assert "حساب نمایشی مستقل" in play_client.get(f"/play/invitation/{invite}").text
    response = play_client.post(
        f"/play/invitation/{invite}", data={"name": "درسا", "avatar": "owl"}
    )
    assert response.status_code == 200
    assert play_client.get(f"/play/invitation/{invite}").status_code == 404
    assert p.scalar(play_conn, "SELECT age FROM play_accounts WHERE name='درسا'") == "child"
    child.act("profile", name="تغییر نام ممنوع", avatar="frog")
    assert p.scalar(play_conn, "SELECT name FROM play_accounts WHERE id='member-arin'") == "آرین"
    child.act("create_room", game="shir", request_id=p.uid(), status=403)


def test_shir_three_independent_accounts_to_result_and_replay(demos, play_conn):
    admin = demos(p.ADMIN)
    admin.act("approve", id="pending-ali")
    admin.act("scenario", scenario="community")
    host, ali, child, outsider = (
        demos(i) for i in (p.PRIMARY, "member-ali", "member-arin", "member-mina-adult")
    )
    assert len({a.client.cookies.get(COOKIE) for a in (admin, host, ali, child, outsider)}) == 5
    room = launch(host, "shir", (ali, child))
    assert outsider.get(f"/play/state/{room}").status_code == 404
    outsider.act("join_room", code=room, status=404)
    ali.move(room, "start", status=409)
    host.move(room, "start")
    assert p.balance(play_conn, p.PRIMARY_FAMILY) == 148  # 128 + 44 - 3 × 8.
    players = {a.account: a for a in (host, ali, child)}
    hands = {a.account: a.state(room)["hand"] for a in players.values()}
    assert all(len(x) == 6 for x in hands.values())
    assert len({c["id"] for hand in hands.values() for c in hand}) == 18
    assert "hands" not in host.state(room)
    host.move(
        room,
        "offer",
        product="forged",
        feature=hands[p.PRIMARY][2]["id"],
        pitch="معرفی آزمون",
        status=422,
    )
    for label, player in players.items():
        hand = hands[label]
        player.move(
            room,
            "offer",
            product=hand[0]["id"],
            feature=hand[2]["id"],
            pitch=f"پیشنهاد خصوصی از {label}",
        )
        if label == p.PRIMARY:
            assert "پیشنهاد خصوصی" not in ali.get(f"/play/state/{room}").text
            player.move(
                room,
                "offer",
                product=hand[0]["id"],
                feature=hand[2]["id"],
                pitch="معرفی دوم",
                status=409,
            )
    for _ in players:
        state = host.state(room)
        assert state["phase"] == "pitch"
        assert "offers" not in state and state["offer"]["player"] == state["speaker"]
        players[state["speaker"]].move(room, "present")
    host.move(room, "vote", target=host.account, status=409)
    host.move(room, "vote", target=ali.account)
    host.move(room, "vote", target=child.account, status=409)
    ali.move(room, "vote", target=host.account)
    result = child.move(room, "vote", target=host.account)["result"]
    assert result["winners"] == [host.account]
    assert result["scores"][0]["votes"] == 2
    assert any(b["title"] == "سازندهٔ شهر" for b in result["badges"])
    assert all(a.state(room)["result"] == result for a in players.values())
    stored = p.one(
        play_conn,
        "SELECT id FROM play_results WHERE room_id=(SELECT id FROM play_rooms WHERE code=?)",
        room,
    )
    assert "نتیجهٔ شیر و مرغ کیلوس" in admin.get(f"/play/admin/result/{stored['id']}").text
    assert "هدف تکمیل شد" in host.get("/play/family/competitions").text
    host.act("claim", id="daily", status=303)
    assert p.balance(play_conn, p.PRIMARY_FAMILY) == 148  # Game score and badges don't mint tokens.
    state = host.move(room, "replay")
    assert state["phase"] == "lobby" and state["round"] == 2
    assert not any(a["ready"] for a in state["players"])
    assert stored["id"] in host.get("/play/family/rooms").text


def test_quiz_answer_privacy_progress_and_score(demos, play_conn):
    a, b = demos(p.PRIMARY), demos("member-arin")
    room = launch(a, "quiz", (b,), difficulty="easy", category="علوم و طبیعت")
    a.move(room, "start")
    total = len(engine_room(play_conn, room)["bank"])
    for idx in range(total):
        view = b.state(room)
        assert view["phase"] == "question" and view["index"] == idx
        assert "answer" not in view["question"] and "bank" not in view
        answer = engine_room(play_conn, room)["bank"][idx]["answer"]
        a.move(room, "answer", option=str(answer))
        a.move(room, "answer", option=str(answer), status=409)
        assert b.state(room)["my_answer"] is None
        feedback = b.move(room, "answer", option=str((answer + 1) % 4))
        assert feedback["feedback"]["correct"] == [a.account]
        assert feedback["feedback"]["answer"] == view["question"]["options"][answer]
        final = a.move(room, "next")
    assert final["result"]["winners"] == [a.account]
    assert final["result"]["scores"][0]["score"] == 24
    assert p.balance(play_conn, p.PRIMARY_FAMILY) == 116


@pytest.mark.parametrize("mode", ("guess", "forbidden", "speed"))
def test_word_modes_turn_restrictions_and_results(demos, play_conn, mode):
    host, remote = demos(p.PRIMARY), demos("member-arin")
    room = launch(host, "words", (remote,), mode=mode)
    state = host.move(room, "start")
    for _ in range(state["count"]):
        engine = engine_room(play_conn, room)
        word = engine["bank"][engine["index"]]["word"]
        player, other = (host, remote) if engine["turn"] == host.account else (remote, host)
        if mode == "forbidden":
            assert player.state(room)["secret_word"] == word
            assert "secret_word" not in other.state(room)
            player.move(room, "clue", clue=f"واژهٔ {word} ممنوع است", status=422)
            player.move(room, "clue", clue="یک نشانهٔ تازه برای شما دارم")
            player.move(room, "guess", guess=word, status=409)
            solver = other
        elif mode == "guess":
            other.move(room, "guess", guess=word, status=409)
            solver = player
        else:
            solver = remote
        assert solver.move(room, "guess", guess=word)["feedback"]["answer"] == word
        final = host.move(room, "next")
    assert final["result"]["mode"] == mode
    assert len(final["result"]["log"]) == state["count"]
    assert p.balance(play_conn, p.PRIMARY_FAMILY) == 120


def test_no_funds_rolls_back_and_timeout_is_projected_by_admin(demos, play_conn, monkeypatch):
    a, b, admin = demos(p.PRIMARY), demos("member-arin"), demos(p.ADMIN)
    room = launch(a, "quiz", (b,))
    admin.act(
        "adjust",
        family=p.PRIMARY_FAMILY,
        kind="deduct",
        amount="128",
        reason="تست کمبود",
        request_id=p.uid(),
    )
    a.move(room, "start", status=409)
    assert a.state(room)["phase"] == "lobby"
    assert p.balance(play_conn, p.PRIMARY_FAMILY) == 0
    admin.act(
        "adjust",
        family=p.PRIMARY_FAMILY,
        kind="issue",
        amount="20",
        reason="ورود به بازی",
        request_id=p.uid(),
    )
    a.move(room, "start")
    timestamp = p.now()
    monkeypatch.setattr(p, "now", lambda: timestamp + 400)
    assert admin.get("/play/admin/reports").status_code == 200
    assert a.state(room)["phase"] == "finished"
    assert not b.state(room)["result"]["winners"]
    assert p.balance(play_conn, p.PRIMARY_FAMILY) == 8


def test_play_is_not_mounted_outside_demo(settings):
    production = replace(settings, env="prod", demo_mode="play")
    with TestClient(create_app(production)) as client:
        assert client.get("/play/").status_code == 404
        assert client.get("/", follow_redirects=False).headers["location"] == "/login"
        assert not production.db_path.with_name(
            production.db_path.name + ".kilos-play-demo.sqlite3"
        ).exists()


def test_https_preview_uses_http_only_partitioned_session(play_client, demos):
    admin = demos(p.ADMIN)
    code = entry_code(admin, p.PRIMARY)
    with TestClient(play_client.app, base_url="https://sample.e2b.app") as embedded:
        response = embedded.post("/play/enter", data={"entry_code": code}, follow_redirects=False)
        cookie = response.headers["set-cookie"].lower()
        assert all(
            flag in cookie for flag in ("httponly", "secure", "samesite=none", "partitioned")
        )
        assert "no-store" in response.headers["cache-control"]
        assert embedded.get("/play/pulse").json()["balance"] == 128


def test_uat01_admin_requires_credential_and_old_passwordless_sessions_are_invalid(
    play_client, play_settings, play_conn, demos
):
    import hashlib
    import secrets

    assert play_client.get("/play/admin/dashboard", headers=JSON).status_code == 401
    assert play_client.get("/play/admin/export", headers=JSON).status_code == 401
    response = play_client.get("/play/admin/dashboard", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/play/admin/login"
    assert 'type="password"' in play_client.get(response.headers["location"]).text
    for form in ({}, {"operator_key": "incorrect"}):
        denied = play_client.post("/play/admin/login", data=form, headers=JSON)
        assert denied.status_code == 401 and COOKIE not in denied.cookies
    assert play_client.post("/play/enter", data={"account": p.ADMIN}).status_code == 403
    assert play_client.post("/play/entry-code", data={"account": p.VISITOR}).status_code == 401
    assert play_client.post("/play/action", data={"action": "reset"}).status_code == 401
    assert (
        play_client.post(
            "/play/admin/login",
            data={"operator_key": play_settings.demo_operator_key},
            headers={"Origin": "https://unrelated.test"},
        ).status_code
        == 403
    )

    assert (
        play_client.post(
            "/play/admin/login",
            data={"operator_key": play_settings.demo_operator_key},
            headers={"Origin": "null", "Sec-Fetch-Site": "same-site"},
        ).status_code
        == 403
    )

    # The existing database can contain a historical demo session; do not delete the DB.
    raw = secrets.token_urlsafe(32)
    with play_conn:
        play_conn.execute(
            "INSERT INTO play_sessions VALUES (?,?,?)",
            (hashlib.sha256(raw.encode()).hexdigest(), p.ADMIN, p.now() + 600),
        )
    play_client.cookies.set(COOKIE, raw, domain="play.test", path="/play")
    assert play_client.get("/play/admin/dashboard", headers=JSON).status_code == 401

    visitor = demos(p.VISITOR)
    assert visitor.get("/play/admin/dashboard").status_code == 403
    assert (
        visitor.client.post(
            "/play/entry-code",
            data={
                "csrf": visitor.csrf,
                "account": p.PRIMARY,
            },
        ).status_code
        == 403
    )
    assert (
        visitor.client.post(
            "/play/admin/login",
            data={
                "operator_key": play_settings.demo_operator_key,
            },
        ).status_code
        == 403
    )  # A role change also requires the current session's CSRF.
    admin = visitor.client.post(
        "/play/admin/login",
        data={
            "operator_key": play_settings.demo_operator_key,
            "csrf": visitor.csrf,
        },
    )
    assert admin.url.path == "/play/admin/dashboard" and admin.status_code == 200
    assert play_settings.demo_operator_key not in admin.text


def test_uat01_entry_codes_are_admin_issued_single_use_and_not_cookies(demos, play_conn):
    admin = demos(p.ADMIN)
    for form, code in [
        ({"account": p.VISITOR}, 403),
        ({"account": p.ADMIN, "csrf": admin.csrf}, 404),
    ]:
        assert admin.client.post("/play/entry-code", data=form).status_code == code
    code = entry_code(admin, p.VISITOR)

    def claim():
        with new_client(admin.client.app) as c:
            return c.post("/play/enter", data={"entry_code": code}, follow_redirects=False)

    assert admin.client.get(f"/play/visitor/home?entry_code={code}").status_code == 403
    with new_client(admin.client.app) as forged:
        forged.cookies.set(COOKIE, code, domain="play.test", path="/play")
        assert forged.get("/play/pulse").status_code == 401
    with ThreadPoolExecutor(2) as pool:
        left, right = list(pool.map(lambda _: claim(), range(2)))
    assert sorted((left.status_code, right.status_code)) == [303, 401]
    winner = next(r for r in (left, right) if r.status_code == 303)
    assert winner.headers["location"] == "/play/visitor/home"
    assert code not in winner.headers["set-cookie"]

    old = entry_code(admin, p.PRIMARY)
    admin.act("reset", confirm="بازنشانی")
    with new_client(admin.client.app) as fresh:
        assert fresh.post("/play/enter", data={"entry_code": old}).status_code == 401
    assert p.scalar(play_conn, "SELECT COUNT(*) FROM play_sessions") == 1


def test_uat04_room_links_hide_account_catalogue_and_entry_checks_family(play_client, demos):
    admin, host, outsider = (demos(i) for i in (p.ADMIN, p.PRIMARY, "member-mina-adult"))
    room = launch(host, "shir")
    path = f"/play/entrance?room={room}"
    unknown = "ZZZZZZ" if room != "ZZZZZZ" else "XXXXXX"
    for accept in ({}, JSON):
        page = play_client.get(path, headers=accept)
        absent = play_client.get(f"/play/entrance?room={unknown}", headers=accept)
        assert page.status_code == absent.status_code == 200
        assert page.text.replace(room, unknown) == absent.text
        assert "no-store" in page.headers["cache-control"]
        assert all(word not in page.text for word in ("مریم", "آرین", "member-", "خانوادهٔ رضایی"))
        assert 'name="account"' not in page.text
        for url in (path, f"/play/entrance?room={unknown}"):
            denied = outsider.client.get(url, headers=accept)
            assert denied.status_code == 404
            assert "مریم" not in denied.text and "آرین" not in denied.text
    assert (
        play_client.post("/play/enter", data={"room": room, "account": p.PRIMARY}).status_code
        == 401
    )
    outsider_code = entry_code(admin, "member-mina-adult")
    result = play_client.post("/play/enter", data={"room": room, "entry_code": outsider_code})
    assert result.status_code == 404 and not play_client.cookies.get(COOKIE)
    # Wrong-room attempt rolled back; sign-in to this person's own family still works.
    assert (
        play_client.post("/play/enter", data={"entry_code": outsider_code}).url.path
        == "/play/family/home"
    )
    assert play_client.get(f"/play/state/{room}").status_code == 404
    with new_client(host.client.app) as new_player:
        member_code = entry_code(admin, "member-ali")
        assert (
            new_player.post(
                "/play/enter",
                data={
                    "entry_code": member_code,
                    "room": room,
                },
            ).url.path
            == f"/play/family/room/{room}"
        )
        assert new_player.get(f"/play/state/{room}").json()["joined"] is False


def test_uat04_private_invite_never_advertises_family_and_ignores_scope_fields(
    play_client, demos, play_conn, monkeypatch
):
    adult = demos(p.PRIMARY)
    adult.act("invite", family=p.PRIMARY_FAMILY, age="child")
    code = p.scalar(play_conn, "SELECT code FROM play_invites")
    path = f"/play/invitation/{code}"
    page = play_client.get(path, headers=JSON)
    assert page.status_code == 200 and "پذیرش دعوت خانوادگی" in page.text
    assert all(value not in page.text for value in [p.PRIMARY, p.PRIMARY_FAMILY, "مریم", "آرین"])
    assert 'name="account"' not in page.text and 'name="family"' not in page.text
    out = play_client.post(
        path,
        data={
            "name": "عضو جدید آزمون",
            "avatar": "owl",
            "family": "family-mina",
            "role": "admin",
            "age": "adult",
            "account": p.ADMIN,
        },
    )
    assert out.status_code == 200 and out.url.path == "/play/family/home"
    user = p.one(play_conn, "SELECT * FROM play_accounts WHERE name='عضو جدید آزمون'")
    assert (user["family_id"], user["role"], user["age"]) == (p.PRIMARY_FAMILY, "member", "child")
    assert play_client.get("/play/admin/dashboard").status_code == 403
    assert play_client.get(path).status_code == 404
    with new_client(adult.client.app) as guest:
        assert guest.post(path, data={"name": "تکراری", "avatar": "owl"}).status_code == 404
        adult.act("invite", family=p.PRIMARY_FAMILY, age="adult")
        revoked = p.scalar(play_conn, "SELECT code FROM play_invites WHERE used_by IS NULL")
        adult.act("revoke", family=p.PRIMARY_FAMILY, id=revoked)
        adult.act("invite", family=p.PRIMARY_FAMILY, age="adult")
        expired = p.scalar(
            play_conn, "SELECT code FROM play_invites WHERE revoked=0 AND used_by IS NULL"
        )
        at = p.now()
        monkeypatch.setattr(p, "now", lambda: at + 86400 * 4)
        for invalid in (revoked, expired, "not-a-code"):
            route = f"/play/invitation/{invalid}"
            assert guest.get(route).status_code == 404
            assert guest.post(route, data={"name": "تکراری", "avatar": "owl"}).status_code == 404


def test_uat02_pulse_tracks_one_approved_sale_and_game_debits(demos, play_conn):
    admin, visitor, host, ali, arin, outsider = (
        demos(i)
        for i in (p.ADMIN, p.VISITOR, p.PRIMARY, "member-ali", "member-arin", "member-mina-adult")
    )

    def poll(person, view, **params):
        result = person.client.get("/play/pulse", params={"view": view, **params})
        assert result.status_code == 200 and result.headers["cache-control"] == "no-store"
        return result.json()

    dashboard = poll(visitor, "home")
    assert dashboard["balance"] == 128 and dashboard["sales"]["target_pct"] == 78
    new_sale = dict(
        amount="22000000",
        visitor=p.VISITOR,
        sold_on=p.day().isoformat(),
        note="فروش زندهٔ آزمون",
        request_id=p.uid(),
    )
    admin.act("sale", **new_sale)
    sale = p.one(play_conn, "SELECT id FROM play_sales WHERE request_id=?", new_sale["request_id"])
    pending = poll(visitor, "home")
    assert pending["sales"] == dashboard["sales"] and pending["balance"] == 128
    assert new_sale["note"] in pending["table_html"]
    host.act("approve", id=sale["id"], status=403)
    admin.act("approve", id=sale["id"])
    admin.act("approve", id=sale["id"])
    approved = poll(visitor, "home", table_revision=pending["table_revision"])
    assert approved["sales"]["target_pct"] == 100 and approved["balance"] == 172
    assert approved["sales"]["amount"] - pending["sales"]["amount"] == 22_000_000
    assert (
        approved["sales"]["tokens"] - pending["sales"]["tokens"] == 44 and approved["unread"] == 1
    )
    assert approved["table_revision"] != pending["table_revision"]
    assert approved["table_html"] != pending["table_html"]
    shadow = poll(visitor, "home", table_revision=approved["table_revision"])
    assert shadow == {k: v for k, v in approved.items() if k != "table_html"}
    event = p.one(
        play_conn, "SELECT id,amount FROM play_wallet_events WHERE source_id=?", sale["id"]
    )
    assert event["amount"] == 44
    assert (
        p.scalar(play_conn, "SELECT COUNT(*) FROM play_wallet_events WHERE source_id=?", sale["id"])
        == 1
    )
    for person in (visitor, host):
        wallet = poll(person, "wallet", tx=event["id"])
        assert wallet["balance"] == 172 and new_sale["note"] in wallet["table_html"]
    foreign = poll(outsider, "wallet", tx=event["id"], family=p.PRIMARY_FAMILY)
    assert "sales" not in foreign and new_sale["note"] not in foreign["table_html"]

    room = launch(host, "shir", (ali, arin))
    host.move(room, "start")
    for person in (host, visitor, ali, arin):
        wallet = poll(person, "wallet")
        assert wallet["balance"] == 148 and wallet["table_html"].count(room) == 3
        if person == visitor:
            assert (
                wallet["sales"]["target_pct"] == 100
                and wallet["sales"]["tokens"] == approved["sales"]["tokens"]
            )
    assert (
        p.scalar(
            play_conn,
            """SELECT COUNT(*) FROM play_wallet_events WHERE kind='entry'
           AND source_id LIKE (SELECT id||':%' FROM play_rooms WHERE code=?)""",
            room,
        )
        == 3
    )


def test_uat03_uncommitted_move_can_retry_but_committed_guess_cannot_duplicate(demos, play_conn):
    host, ali = (demos(i) for i in (p.PRIMARY, "member-ali"))
    room = launch(host, "words", (ali,), mode="speed")
    host.move(room, "start")
    before = host.state(room)
    assert before["phase"] == "guess" and before["attempts_left"] == 3
    args = dict(key=before["phase_key"], move_seq=before["move_seq"])
    host.move(room, "guess", guess="", status=422, **args)
    after_error = host.state(room)
    assert after_error["move_seq"] == before["move_seq"] and after_error["attempts_left"] == 3
    payload = "حدس نادرست آزمون یک‌بار"

    def same_move(_):
        return host.client.post(
            "/play/action",
            headers=JSON,
            data={
                "action": "room_move",
                "move": "guess",
                "csrf": host.csrf,
                "code": room,
                "move_seq": before["move_seq"],
                "phase_key": before["phase_key"],
                "guess": payload,
            },
        ).status_code

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(same_move, range(2))) == [200, 409]
    after = host.state(room)
    assert after["phase_key"] == before["phase_key"] and after["deadline"] == before["deadline"]
    assert after["attempts_left"] == 2 and after["move_seq"] == before["move_seq"] + 1
    assert ali.state(room)["attempts_left"] == 3
    assert engine_room(play_conn, room)["attempts"][p.PRIMARY] == 1

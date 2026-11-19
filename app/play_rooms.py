"""Server-authoritative room state machine and player-specific projections."""

from __future__ import annotations

import json
import secrets
import unicodedata

from app import play_data as p
from app import play_ops as ops

RNG = secrets.SystemRandom()
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
LIVE = {"build", "pitch", "vote", "question", "clue", "guess", "feedback"}


def code_from(value) -> str:
    return str(value or "").strip().translate(p.DIGITS).upper()


def fetch(conn, code, actor):
    ops.require(actor, "member")
    room = p.one(
        conn,
        "SELECT * FROM play_rooms WHERE code=? AND family_id=?",
        code_from(code),
        actor["family_id"],
    )
    if not room:
        raise p.PlayError("اتاق پیدا نشد یا خصوصی است.", 404)
    return room, json.loads(room["state_json"])


def save(conn, room, state):
    state["rev"] += 1
    conn.execute(
        "UPDATE play_rooms SET state_json=?,updated_at=? WHERE id=?",
        (p.dump(state), p.now(), room["id"]),
    )


def roster(conn, room):
    return p.rows(
        conn,
        """SELECT a.id,a.name,a.avatar,a.age,m.ready
        FROM play_room_members m JOIN play_accounts a ON m.account_id=a.id
        WHERE m.room_id=? AND a.active=1 ORDER BY m.joined_at,m.rowid""",
        room["id"],
    )


def create(conn, actor, form, *, host=None) -> str:
    if host is None:
        ops.require(actor, "member")
        host = actor
    else:
        ops.require(actor, "admin")
    if host["role"] != "member" or host["age"] != "adult" or not host["active"]:
        raise p.PlayError("ساخت اتاق فقط برای حساب بزرگسالِ فعال خانواده ممکن است.", 403)
    game = p.need(p.one(conn, "SELECT * FROM play_games WHERE key=?", form.get("game")))
    if not game["enabled"]:
        raise p.PlayError("این بازی در حال حاضر فعال نیست.", 409)
    options: dict = {}
    if game["key"] == "quiz":
        category = p.text(form.get("category"), "دسته", 60, optional=True)
        difficulty = form.get("difficulty") or ""
        p.choice(difficulty, (*p.DIFFICULTIES, ""), "سختی")
        if category and not p.one(
            conn, "SELECT id FROM play_questions WHERE category=? AND archived=0", category
        ):
            raise p.PlayError("این دستهٔ پرسش در دسترس نیست.")
        options = {"category": category, "difficulty": difficulty}
    if game["key"] == "words":
        options = {"mode": p.choice(form.get("mode") or "guess", p.WORD_MODES, "حالت بازی")}
    key = p.request_id(form.get("request_id"))
    old = p.one(conn, "SELECT * FROM play_rooms WHERE request_id=?", key)
    if old:
        if (old["host_id"], old["game_key"], old["options_json"]) != (
            host["id"],
            game["key"],
            p.dump(options),
        ):
            raise p.PlayError("این درخواست قبلاً برای اتاق دیگری استفاده شده است.", 409)
        return old["code"]
    code = "".join(secrets.choice(ALPHABET) for _ in range(6))
    while p.one(conn, "SELECT id FROM play_rooms WHERE code=?", code):
        code = "".join(secrets.choice(ALPHABET) for _ in range(6))
    room_id, at = p.uid(), p.now()
    state = {"rev": 1, "phase": "lobby", "round": 1, "index": 0, "deadline": None}
    conn.execute(
        "INSERT INTO play_rooms VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            room_id,
            code,
            key,
            host["family_id"],
            host["id"],
            game["key"],
            p.dump(options),
            p.dump(state),
            at,
            at,
        ),
    )
    conn.execute("INSERT INTO play_room_members VALUES (?,?,0,?)", (room_id, host["id"], at))
    p.audit(conn, actor["id"], "room", f"اتاق بازی «{game['title']}» ساخته شد.")
    return code


def list_rooms(conn, family=None, limit=40, viewer=None):
    items = p.rows(
        conn,
        """SELECT r.*,g.title AS game,f.name AS family,a.name AS host,
        (SELECT COUNT(*) FROM play_room_members m JOIN play_accounts n ON n.id=m.account_id
            WHERE m.room_id=r.id AND n.active=1) AS total,
        EXISTS(SELECT 1 FROM play_room_members m WHERE m.room_id=r.id AND m.account_id=?) AS joined,
        (SELECT x.id FROM play_results x WHERE x.room_id=r.id
            ORDER BY x.round_no DESC LIMIT 1) AS result_id
        FROM play_rooms r JOIN play_games g ON r.game_key=g.key
        JOIN play_families f ON f.id=r.family_id
        JOIN play_accounts a ON a.id=r.host_id WHERE (? IS NULL OR r.family_id=?)
        ORDER BY r.updated_at DESC,r.rowid DESC LIMIT ?""",
        viewer,
        family,
        family,
        limit,
    )
    for item in items:
        state = json.loads(item.pop("state_json"))
        item["phase"] = state["phase"]
        item["round"] = state["round"]
    return items


def join(conn, actor, code):
    room, state = fetch(conn, code, actor)
    if p.one(
        conn,
        "SELECT account_id FROM play_room_members WHERE room_id=? AND account_id=?",
        room["id"],
        actor["id"],
    ):
        return room["code"]
    if state["phase"] != "lobby":
        raise p.PlayError("ورود جدید فقط پیش از آغاز بازی ممکن است.", 409)
    game = p.one(conn, "SELECT enabled,max_players FROM play_games WHERE key=?", room["game_key"])
    if not game["enabled"] or len(roster(conn, room)) >= game["max_players"]:
        raise p.PlayError("ظرفیت اتاق پر است یا بازی غیرفعال شده است.", 409)
    conn.execute(
        "INSERT INTO play_room_members VALUES (?,?,0,?)", (room["id"], actor["id"], p.now())
    )
    save(conn, room, state)
    return room["code"]


def phase_key(state) -> str:
    return f"{state['round']}:{state['phase']}:{state['index']}"


def phase(state, name, at, seconds=None):
    state["phase"] = name
    state["deadline"] = at + seconds if seconds else None


def deal(conn, players):
    deck = p.rows(conn, "SELECT id,kind,label,detail FROM play_cards WHERE archived=0 ORDER BY id")
    kinds = {kind: [c for c in deck if c["kind"] == kind] for kind in p.CARDS}
    hands: dict = {person["id"]: [] for person in players}
    if not kinds["customer"]:
        raise p.PlayError("برای بازی دست‌کم یک کارت مشتری لازم است.", 409)
    for kind, count in (("product", 2), ("feature", 2), ("limitation", 1), ("event", 1)):
        pool = kinds[kind]
        if len(pool) < count:
            raise p.PlayError(f"کارت‌های دستهٔ «{p.CARDS[kind]}» برای بازی کافی نیستند.", 409)
        # Deal disjoint hands where possible. A managed, small bank may repeat across players.
        RNG.shuffle(pool)
        for i, person in enumerate(players):
            start = i * count
            selected = (
                pool[start : start + count]
                if start + count <= len(pool)
                else RNG.sample(pool, count)
            )
            hands[person["id"]].extend(selected)
    return RNG.choice(kinds["customer"]), hands


def start(conn, room, state, at):
    game = p.one(conn, "SELECT * FROM play_games WHERE key=?", room["game_key"])
    people = roster(conn, room)
    if not game["enabled"] or not game["min_players"] <= len(people) <= game["max_players"]:
        raise p.PlayError("بازی غیرفعال است یا تعداد بازیکنان با ظرفیت فعلی هم‌خوان نیست.", 409)
    if not all(a["ready"] for a in people):
        raise p.PlayError("برای شروع، همهٔ بازیکنان باید آماده باشند.", 409)
    options = json.loads(room["options_json"])
    state.update(
        settings=game,
        players=people,
        index=0,
        options=options,
        scores={a["id"]: 0 for a in people},
        log=[],
    )
    if game["key"] == "shir":
        state["customer"], state["hands"] = deal(conn, people)
        state.update(offers={}, votes={}, pitch_order=[])
        phase(state, "build", at, game["duration"])
    elif game["key"] == "quiz":
        category, difficulty = options.get("category", ""), options.get("difficulty", "")
        pool = p.rows(
            conn,
            """SELECT id,prompt,category,difficulty,options_json,answer
            FROM play_questions WHERE archived=0 AND (?='' OR category=?) AND (?='' OR difficulty=?)
            ORDER BY id""",
            category,
            category,
            difficulty,
            difficulty,
        )
        if not pool:
            raise p.PlayError("برای این ترکیب دسته و سختی، پرسشی وجود ندارد.", 409)
        state["bank"] = RNG.sample(pool, min(game["rounds"], len(pool)))
        next_puzzle(state, at)
    else:
        pool = p.rows(
            conn, "SELECT id,word,hint,category,forbidden_json FROM play_words WHERE archived=0"
        )
        if not pool:
            raise p.PlayError("بانک واژه‌ها خالی است.", 409)
        state["bank"] = RNG.sample(pool, min(game["rounds"], len(pool)))
        next_puzzle(state, at)
    if p.balance(conn, room["family_id"]) < game["cost"] * len(people):
        raise p.PlayError("توکن کیف خانواده برای ورود همهٔ بازیکنان کافی نیست.", 409)
    for player in people:
        source = f"{room['id']}:{state['round']}:{player['id']}"
        p.wallet_event(
            conn,
            room["family_id"],
            "entry",
            source,
            -game["cost"],
            f"ورود {player['name']} به {game['title']} · {room['code']}",
            player["id"],
            at,
        )
    p.audit(conn, room["host_id"], "room", f"بازی «{game['title']}» آغاز شد.", at)


def next_puzzle(state, at):
    state.update(answers={}, attempts={}, clue=None, solver=None, feedback=None)
    duration = state["settings"]["duration"]
    if state["settings"]["key"] == "quiz":
        phase(state, "question", at, duration)
    else:
        mode = state["options"]["mode"]
        state["turn"] = state["players"][state["index"] % len(state["players"])]["id"]
        phase(
            state,
            "clue" if mode == "forbidden" else "guess",
            at,
            max(10, duration // 2) if mode == "speed" else duration,
        )


def finish(conn, room, state, at):
    people, scores = state["players"], state["scores"]
    game = state["settings"]
    tally = None
    if game["key"] == "shir":
        tally = {a["id"]: 0 for a in people}
        for vote in state["votes"].values():
            tally[vote] += 1
        best = max(tally.values())
        winners = [code for code, score in tally.items() if best > 0 and score == best]
        for code in scores:
            scores[code] = (
                (game["reward"] // 4 if code in state["offers"] else 0)
                + tally[code] * ((game["reward"] + 4) // 5)
                + (game["reward"] if code in winners else 0)
            )
    else:
        high = max(scores.values())
        winners = [code for code, score in scores.items() if high > 0 and score == high]
    ranked = [
        {
            "id": a["id"],
            "name": a["name"],
            "avatar": a["avatar"],
            "score": scores[a["id"]],
            **({"votes": tally[a["id"]]} if tally is not None else {}),
        }
        for a in people
    ]
    ranked.sort(key=lambda a: (-a["score"], a["name"], a["id"]))
    code = p.uid()
    result = {
        "scores": ranked,
        "winners": winners,
        "mode": state["options"].get("mode"),
        "log": state["log"],
        "round": state["round"],
    }
    conn.execute(
        "INSERT INTO play_results VALUES (?,?,?,?,?,?,?)",
        (code, room["id"], room["family_id"], room["game_key"], state["round"], p.dump(result), at),
    )
    new_badges = []
    for account, score in scores.items():
        p.add_score(conn, account, room["family_id"], "game", code, score, at)
        if p.grant_badge(conn, account, "first", at=at):
            new_badges.append((account, "first"))
        if account in winners and p.grant_badge(conn, account, "champion", at=at):
            new_badges.append((account, "champion"))
    new_badges.extend(pair for pair in ops.grant_community(conn) if pair[0] in scores)
    labels = {a["id"]: a["name"] for a in people}
    result["badges"] = [
        dict(
            p.need(p.one(conn, "SELECT title,icon FROM play_rewards WHERE code=?", badge)),
            name=labels[account],
            account=account,
        )
        for account, badge in new_badges
    ]
    conn.execute("UPDATE play_results SET details_json=? WHERE id=?", (p.dump(result), code))
    state["result"] = result
    phase(state, "finished", at)
    p.audit(conn, room["host_id"], "result", f"نتیجهٔ {game['title']} در تاریخچه ذخیره شد.", at)


def feedback(state, at):
    item = state["bank"][state["index"]]
    game = state["settings"]
    unit = (game["reward"] + len(state["bank"]) - 1) // len(state["bank"])
    if game["key"] == "quiz":
        correct = [a for a, answer in state["answers"].items() if answer == item["answer"]]
        for code in correct:
            state["scores"][code] += unit
        note = {
            "prompt": item["prompt"],
            "answer": json.loads(item["options_json"])[item["answer"]],
            "correct": correct,
            "points": unit,
            "index": item["answer"],
        }
    else:
        solver = state["solver"]
        correct = [solver] if solver else []
        if solver:
            state["scores"][solver] += unit
            if state["options"]["mode"] == "forbidden":
                state["scores"][state["turn"]] += unit // 2
        note = {
            "prompt": item["category"],
            "answer": item["word"],
            "correct": correct,
            "points": unit,
        }
    state["feedback"] = note
    state["log"].append(note)
    phase(state, "feedback", at, 8)


def advance(conn, room, state, at):
    stage = state["phase"]
    if stage == "build":
        state["pitch_order"] = list(state["offers"])
        RNG.shuffle(state["pitch_order"])
        if state["pitch_order"]:
            phase(state, "pitch", at, min(18, state["settings"]["duration"]))
        else:
            finish(conn, room, state, at)
    elif stage == "pitch":
        state["index"] += 1
        if state["index"] >= len(state["pitch_order"]):
            if len(state["offers"]) > 1:
                phase(state, "vote", at, min(45, state["settings"]["duration"]))
            else:
                finish(conn, room, state, at)
        else:
            phase(state, "pitch", at, min(18, state["settings"]["duration"]))
    elif stage == "vote":
        finish(conn, room, state, at)
    elif stage in {"question", "clue", "guess"}:
        feedback(state, at)
    elif stage == "feedback":
        state["index"] += 1
        if state["index"] >= len(state["bank"]):
            finish(conn, room, state, at)
        else:
            next_puzzle(state, at)


def tick(conn, room, state, at):
    changed = False
    while state["deadline"] is not None and state["deadline"] <= at:
        advance(conn, room, state, state["deadline"])
        changed = True
    if changed:
        save(conn, room, state)


def normalize(value: str) -> str:
    value = value.translate(str.maketrans("يكۀةىأإ", "یکههیاا"))
    return "".join(s.lower() for s in unicodedata.normalize("NFKC", value) if s.isalnum())


def play_action(conn, actor, code, form):
    room, state = fetch(conn, code, actor)
    who = actor["id"]
    if not p.one(
        conn,
        "SELECT account_id FROM play_room_members WHERE room_id=? AND account_id=?",
        room["id"],
        who,
    ):
        raise p.PlayError("ابتدا به اتاق بپیوندید.", 403)
    at = p.now()
    tick(conn, room, state, at)
    stage = state["phase"]
    if form.get("phase_key") != phase_key(state):
        raise p.PlayError("مرحلهٔ بازی تغییر کرده است؛ صفحه همگام می‌شود.", 409)
    sequence = state.get("move_sequences", {}).get(who, 0)
    supplied = p.integer(form.get("move_seq"), "ترتیب حرکت", 0, 10**12)
    if supplied != sequence:
        raise p.PlayError("وضعیت حرکت شما تغییر کرده است؛ اتاق را همگام کنید.", 409)
    action = form.get("move")
    host = who == room["host_id"] and actor["age"] == "adult"
    if action == "ready" and stage == "lobby":
        ready = p.choice(form.get("value"), ("0", "1"), "آمادگی")
        conn.execute(
            "UPDATE play_room_members SET ready=? WHERE room_id=? AND account_id=?",
            (int(ready), room["id"], who),
        )
    elif action == "leave" and stage == "lobby":
        if who == room["host_id"]:
            phase(state, "closed", at)
        else:
            conn.execute(
                "DELETE FROM play_room_members WHERE room_id=? AND account_id=?", (room["id"], who)
            )
    elif action == "start" and stage == "lobby" and host:
        start(conn, room, state, at)
    elif action == "offer" and stage == "build" and who in state["hands"]:
        if who in state["offers"]:
            raise p.PlayError("پیشنهاد شما پیش‌تر ثبت شده است.", 409)
        cards = {card["id"]: card for card in state["hands"][who]}
        product = p.choice(form.get("product"), cards, "کارت محصول")
        feature = p.choice(form.get("feature"), cards, "کارت ویژگی")
        if cards[product]["kind"] != "product" or cards[feature]["kind"] != "feature":
            raise p.PlayError("یک کارت محصول و یک کارت ویژگی از دست خود انتخاب کنید.")
        pitch = p.text(form.get("pitch"), "معرفی پیشنهاد", 240)
        if len(pitch) < 6:
            raise p.PlayError("معرفی باید دست‌کم ۶ نویسه باشد.")
        picked = [cards[product], cards[feature]]
        picked.extend(c for c in cards.values() if c["kind"] in {"limitation", "event"})
        state["offers"][who] = {"player": who, "pitch": pitch, "cards": picked}
        if len(state["offers"]) == len(state["players"]):
            advance(conn, room, state, at)
    elif action == "present" and stage == "pitch" and state["pitch_order"][state["index"]] == who:
        advance(conn, room, state, at)
    elif action == "vote" and stage == "vote" and who in state["scores"]:
        target = p.choice(form.get("target"), state["offers"], "پیشنهاد")
        if who == target:
            raise p.PlayError("نمی‌توانید به پیشنهاد خودتان رأی بدهید.", 409)
        if who in state["votes"]:
            raise p.PlayError("برای این دور قبلاً رأی داده‌اید.", 409)
        state["votes"][who] = target
        if len(state["votes"]) == len(state["players"]):
            advance(conn, room, state, at)
    elif action == "answer" and stage == "question" and who in state["scores"]:
        if who in state["answers"]:
            raise p.PlayError("پاسخ شما پیش‌تر ثبت شده است.", 409)
        state["answers"][who] = p.integer(form.get("option"), "پاسخ", 0, 3)
        if len(state["answers"]) == len(state["players"]):
            advance(conn, room, state, at)
    elif action == "clue" and stage == "clue" and state["turn"] == who:
        target = state["bank"][state["index"]]
        clue = p.text(form.get("clue"), "سرنخ", 120)
        simplified = normalize(clue)
        prohibited = [target["word"], *json.loads(target["forbidden_json"])]
        if len(simplified) < 4 or any(normalize(word) in simplified for word in prohibited):
            raise p.PlayError("سرنخ باید تازه باشد و واژهٔ اصلی یا واژه‌های ممنوعه را نداشته باشد.")
        state["clue"] = clue
        phase(state, "guess", at, state["settings"]["duration"])
    elif action == "guess" and stage == "guess" and who in eligible_guessers(state):
        word = p.text(form.get("guess"), "حدس", 45)
        if state["attempts"].get(who, 0) >= 3:
            raise p.PlayError("سه فرصت حدس این نوبت را استفاده کرده‌اید.", 409)
        state["attempts"][who] = state["attempts"].get(who, 0) + 1
        target = state["bank"][state["index"]]["word"]
        if normalize(word) == normalize(target):
            state["solver"] = who
            advance(conn, room, state, at)
        elif all(state["attempts"].get(a, 0) >= 3 for a in eligible_guessers(state)):
            advance(conn, room, state, at)
    elif action == "next" and stage == "feedback" and host:
        advance(conn, room, state, at)
    elif action == "replay" and stage == "finished" and host:
        rev, round_no = state["rev"], state["round"]
        state.clear()
        state.update(rev=rev, round=round_no + 1, phase="lobby", index=0, deadline=None)
        conn.execute("UPDATE play_room_members SET ready=0 WHERE room_id=?", (room["id"],))
    else:
        raise p.PlayError("این حرکت در مرحله یا نوبت فعلی مجاز نیست.", 409)
    # Compare and advance the player's sequence inside the same write transaction.
    # A lost response must not consume a second guess or apply a stale lobby move.
    state.setdefault("move_sequences", {})[who] = sequence + 1
    save(conn, room, state)
    return view(conn, room, state, actor)


def eligible_guessers(state) -> list[str]:
    mode = state["options"]["mode"]
    if mode == "guess":
        return [state["turn"]]
    return [who for who in state["scores"] if mode == "speed" or state["turn"] != who]


def view(conn, room, state, actor) -> dict:
    who = actor["id"]
    stage = state["phase"]
    live = stage in LIVE or stage == "finished"
    settings = (
        state["settings"]
        if live
        else p.one(conn, "SELECT * FROM play_games WHERE key=?", room["game_key"])
    )
    people = state["players"] if live else roster(conn, room)
    joined = any(a["id"] == who for a in people)
    if live and not joined:
        raise p.PlayError("این بازی خصوصی آغاز شده است؛ فقط بازیکنان آن می‌توانند وارد شوند.", 403)
    host = room["host_id"] == who and actor["age"] == "adult"
    options = json.loads(room["options_json"])
    view_data = {
        "you": who,
        "role_is_child": actor["age"] == "child",
        "game": room["game_key"],
        "title": settings["title"],
        "code": room["code"],
        "phase": stage,
        "rev": state["rev"],
        "phase_key": phase_key(state),
        "move_seq": state.get("move_sequences", {}).get(who, 0),
        "deadline": state["deadline"],
        "now": p.now(),
        "host": host,
        "host_id": room["host_id"],
        "joined": joined,
        "round": state["round"],
        "index": state["index"],
        "min": settings["min_players"],
        "max": settings["max_players"],
        "cost": settings["cost"],
        "options": options,
        "enabled": bool(settings["enabled"]),
        "players": [dict(a, score=state.get("scores", {}).get(a["id"], 0)) for a in people],
    }
    if stage == "lobby":
        view_data["can_start"] = bool(
            host
            and settings["enabled"]
            and settings["min_players"] <= len(people) <= settings["max_players"]
            and all(a["ready"] for a in people)
        )
    if room["game_key"] == "shir" and live:
        view_data["customer"] = state["customer"]
        view_data["submitted"] = list(state["offers"])
        if stage == "build":
            view_data["hand"] = state["hands"][who]
        if stage == "pitch":
            speaker = state["pitch_order"][state["index"]]
            view_data.update(
                speaker=speaker, offer=state["offers"][speaker], count=len(state["pitch_order"])
            )
        if stage == "vote":
            view_data.update(
                offers=list(state["offers"].values()),
                voted=who in state["votes"],
                votes_cast=list(state["votes"]),
            )
    if room["game_key"] != "shir" and stage in {"question", "clue", "guess", "feedback"}:
        item = state["bank"][state["index"]]
        view_data["count"] = len(state["bank"])
        if stage == "feedback":
            view_data["feedback"] = state["feedback"]
        elif stage == "question":
            view_data.update(
                question={
                    "prompt": item["prompt"],
                    "category": item["category"],
                    "difficulty": p.DIFFICULTIES[item["difficulty"]],
                    "options": json.loads(item["options_json"]),
                },
                answered=list(state["answers"]),
                my_answer=state["answers"].get(who),
            )
        else:
            view_data.update(
                turn=None if options["mode"] == "speed" else state["turn"],
                category=item["category"],
            )
            if stage == "clue" and who == state["turn"]:
                view_data.update(
                    secret_word=item["word"], forbidden=json.loads(item["forbidden_json"])
                )
            if stage == "guess":
                view_data.update(
                    hint=state["clue"] if options["mode"] == "forbidden" else item["hint"],
                    attempts_left=3 - state["attempts"].get(who, 0),
                    may_guess=who in eligible_guessers(state),
                )
    if stage == "finished":
        view_data["result"] = state["result"]
    return view_data


def room_state(conn, actor, code):
    room, state = fetch(conn, code, actor)
    if state["deadline"] is not None and state["deadline"] <= p.now():
        # Authorize the projection before a spectator would trigger a timed state transition.
        if not any(a["id"] == actor["id"] for a in state["players"]):
            raise p.PlayError("این بازی خصوصی آغاز شده است.", 403)
        with p.writing(conn):
            room, state = fetch(conn, code, actor)
            tick(conn, room, state, p.now())
    return view(conn, room, state, actor)


def settle_due(conn):
    """Project overdue turns even when everyone disconnected before a deadline."""
    sql = """SELECT * FROM play_rooms WHERE json_extract(state_json,'$.deadline')<=?
        ORDER BY updated_at LIMIT 60"""
    if conn.execute(sql, (p.now(),)).fetchone() is None:
        return
    with p.writing(conn):
        now = p.now()
        for room in p.rows(conn, sql, now):
            state = json.loads(room["state_json"])
            tick(conn, room, state, now)

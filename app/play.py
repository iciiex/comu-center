"""Mounted Kilos Play demo. It never reads or writes the legacy app database."""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import re
import secrets
import threading
from collections.abc import Iterator
from urllib.parse import urlencode, urlsplit

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.datastructures import FormData
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import db
from app import play_data as p
from app import play_ops as ops
from app import play_rooms as rooms
from app import play_views as v
from app.config import Settings
from app.jalali import format_jalali, to_persian_digits
from app.security import credential_transport, cross_origin, csrf_for

COOKIE = "kilos_play_session"
TOKEN = re.compile(r"[a-zA-Z0-9_-]{43}")
ROOM_CODE = re.compile(r"[A-Z2-9]{6}")
ENTRY_TTL = 600
ADMIN_LOGIN = "/play/admin/login"
ENTRANCE = "/play/entrance"
FORM_PATH = re.compile(
    r"/play/(?:admin|visitor|family)/(?:[a-z]+|(?:game|room|result)/[a-zA-Z0-9-]+)"
)
SAVED = {
    "visitor": "مشخصات ویزیتور ذخیره شد.",
    "family": "مشخصات خانواده ذخیره شد.",
    "member": "عضویت خانواده به‌روزرسانی شد.",
    "invite": "دعوت‌نامه ساخته شد.",
    "revoke": "دعوت‌نامه لغو شد.",
    "sale": "فروش ثبت شد و در انتظار تأیید است.",
    "approve": "فروش تأیید شد؛ پاداش محاسبه و کیف خانواده به‌روزرسانی شد.",
    "approved": "این فروش قبلاً تأیید شده است؛ توکن دوباره صادر نشد.",
    "adjust": "عملیات در دفتر تراکنش‌ها ثبت شد.",
    "campaign": "کمپین ذخیره شد.",
    "game": "تنظیمات بازی ذخیره شد.",
    "content": "محتوای بازی ذخیره شد.",
    "mission": "مأموریت ذخیره شد.",
    "claim": "امتیاز مأموریت در حساب شما ثبت شد.",
    "competition": "رقابت ذخیره شد.",
    "reward": "نشان ذخیره شد.",
    "rule": "نسخهٔ جدید قانون توکن منتشر شد.",
    "profile": "حساب شما به‌روز شد.",
    "notices": "اعلان‌ها به‌عنوان خوانده‌شده علامت خوردند.",
    "scenario": "سناریوی نمایشی آماده شد.",
    "reset": "داده‌های اولیهٔ دمو با موفقیت بازگشتند.",
}
ADMIN_ACTIONS = {
    "visitor": ops.save_visitor,
    "member": ops.manage_member,
    "campaign": ops.save_campaign,
    "game": ops.save_game,
    "content": ops.save_content,
    "mission": ops.save_mission,
    "competition": ops.save_competition,
    "reward": ops.save_reward,
    "rule": ops.save_rule,
    "sale": ops.register_sale,
    "adjust": ops.adjust,
    "scenario": ops.set_scenario,
}


def make_play(settings: Settings, templates: Jinja2Templates) -> FastAPI:
    path = settings.db_path.with_name(f"{settings.db_path.name}.kilos-play-demo.sqlite3")
    if path.resolve() == settings.db_path.resolve() or (
        path.exists() and settings.db_path.exists() and path.samefile(settings.db_path)
    ):
        raise RuntimeError("Kilos Play requires a separate database file")
    p.initialize(path)
    app = FastAPI(title="کیلوس پلی", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.db_path = path
    limiter: dict[tuple[str, str], list[int]] = {}
    operator_key = settings.demo_operator_key.encode()
    lock = threading.Lock()
    templates.env.filters.update(
        num=p.fmt, playtime=p.when, playdate=format_jalali, digits=to_persian_digits
    )
    templates.env.globals.update(
        art=p.ART,
        avatars=p.AVATARS,
        regions=p.REGIONS,
        card_kinds=p.CARDS,
        levels=p.DIFFICULTIES,
        word_modes=p.WORD_MODES,
        tx_kinds=p.EVENTS,
        metric_kinds=p.METRICS,
        phase_labels=v.ROOM_LABELS,
    )

    def connection() -> Iterator:
        conn = db.connect(path)
        try:
            yield conn
        finally:
            conn.close()

    def digest(raw: str, purpose: str = "session") -> str:
        # Invalidate pre-UAT passwordless sessions without changing the schema. Entry codes
        # cannot verify as cookies, and rotating the operator key invalidates both kinds.
        data = f"kilos-play-v2:{purpose}:{raw}".encode()
        return hmac.new(operator_key, data, hashlib.sha256).hexdigest()

    def who(request: Request, conn):
        raw = request.cookies.get(COOKIE, "")
        if not TOKEN.fullmatch(raw):
            return None
        return p.one(
            conn,
            """SELECT a.* FROM play_sessions s JOIN play_accounts a ON a.id=s.account_id
            WHERE s.token_hash=? AND s.expires_at>? AND a.active=1""",
            digest(raw),
            p.now(),
        )

    def rate(request: Request, purpose: str):
        address = request.client.host if request.client else "unknown"
        key = purpose, address
        at = p.now()
        window = settings.login_rate_window
        limit = (
            settings.login_rate_limit if purpose == "staff" else max(30, settings.login_rate_limit)
        )
        with lock:
            for entry in tuple(limiter):
                if limiter[entry][-1] < at - window:
                    del limiter[entry]
            hits = [moment for moment in limiter.get(key, []) if moment >= at - window]
            if len(hits) >= limit:
                raise p.PlayError("تلاش‌های ورود زیاد است؛ کمی بعد دوباره امتحان کنید.", 429)
            limiter[key] = [*hits, at]

    def new_session(conn, account, request):
        raw = secrets.token_urlsafe(32)
        conn.execute(
            "DELETE FROM play_sessions WHERE expires_at<=? OR token_hash=?",
            (p.now(), digest(request.cookies.get(COOKIE, ""))),
        )
        conn.execute(
            "INSERT INTO play_sessions VALUES (?,?,?)",
            (digest(raw), account, p.now() + settings.session_ttl_seconds),
        )
        return raw

    def cookie(response, request, raw, *, remove=False):
        host = request.headers.get("host", "").split(":", 1)[0]
        secure = request.url.scheme == "https" or host.endswith(".e2b.app")
        response.set_cookie(
            COOKIE,
            raw,
            path="/play",
            httponly=True,
            secure=secure,
            samesite="none" if secure else "lax",
            max_age=0 if remove else settings.session_ttl_seconds,
        )
        if secure:
            # CHIPS allows separate sandbox accounts in embedded Chromium previews.
            response.headers["Set-Cookie"] += "; Partitioned"
        return response

    def csrf(request, form):
        expected = csrf_for(request.cookies.get(COOKIE, ""), settings.secret)
        value = str(form.get("csrf") or "")
        if not hmac.compare_digest(expected.encode(), value.encode()):
            raise p.PlayError("اعتبار فرم منقضی شده است؛ صفحه را دوباره باز کنید.", 403)

    async def read_form(request: Request) -> FormData:
        if cross_origin(request):
            raise p.PlayError("این درخواست از نشانی مجاز ارسال نشده است.", 403)
        length = request.headers.get("content-length", "0")
        if not length.isascii() or not length.isdigit() or len(length) > 5 or int(length) > 65536:
            raise p.PlayError("حجم این فرم بیش از حد مجاز است.", 413)
        return await request.form(max_fields=200, max_files=0, max_part_size=16_384)

    def render(request, name, data, status=200):
        raw = request.cookies.get(COOKIE, "")
        data.update(
            csrf=csrf_for(raw, settings.secret) if raw else "",
            here=request.url.path + (f"?{request.url.query}" if request.url.query else ""),
            flash=SAVED.get(request.query_params.get("done")),
        )
        return templates.TemplateResponse(
            request=request, name=name, context=data, status_code=status
        )

    def table_revision(items):
        return hashlib.sha256(p.dump(items).encode()).hexdigest()

    def screen(request, conn, actor, area, page):
        if v.AREAS[actor["role"]] != area:
            raise p.PlayError("برای این محیط، حساب متناسب با نقش را انتخاب کنید.", 403)
        if page not in v.NAV[area]:
            raise p.PlayError("این بخش پیدا نشد.", 404)
        if page in {"home", "rooms", "competitions", "dashboard", "reports", "control"}:
            rooms.settle_due(conn)
        conn.execute("BEGIN")  # One read snapshot for the header and the server-rendered body.
        context = v.actor_context(conn, actor, area, page)
        builders = {"family": v.family_context, "visitor": v.visitor_context}
        if area == "admin":
            context.update(v.admin_context(conn, page, request.query_params))
        else:
            context.update(builders[area](conn, actor, page, request.query_params))
            if page == "wallet":
                context["table_revision"] = table_revision(context["transactions"])
            elif area == "visitor" and page in {"home", "sales"}:
                items = context["sales"]
                context["table_revision"] = table_revision(items[:3] if page == "home" else items)
        return render(request, f"play_{area}.html", context)

    def go(path):
        return RedirectResponse(path, status_code=303)

    def back(form, actor):
        candidate = str(form.get("return") or "")
        if any(c in candidate for c in ("\r", "\n", "\\", "#")) or len(candidate) > 500:
            return v.landing(actor)
        url = urlsplit(candidate)
        if not url.netloc and not url.scheme and FORM_PATH.fullmatch(url.path):
            # Drop prior success messages on a second write.
            parts = [part for part in url.query.split("&") if part and not part.startswith("done=")]
            return url.path + ("?" + "&".join(parts) if parts else "")
        return v.landing(actor)

    def want_json(request):
        return (
            request.url.path.startswith("/play/state/")
            or request.url.path == "/play/pulse"
            or "application/json" in request.headers.get("accept", "")
        )

    @app.middleware("http")
    async def uncached(request, call_next):
        result = await call_next(request)
        result.headers["Cache-Control"] = "no-store"
        return result

    @app.exception_handler(p.PlayError)
    async def play_error(request: Request, exc: p.PlayError):
        if want_json(request):
            return JSONResponse({"error": exc.message}, status_code=exc.status)
        return render(
            request, "play_error.html", {"message": exc.message, "status": exc.status}, exc.status
        )

    @app.exception_handler(StarletteHTTPException)
    async def route_error(request: Request, exc: StarletteHTTPException):
        label = (
            "این نشانی در باشگاه پیدا نشد."
            if exc.status_code == 404
            else "درخواست قابل پردازش نیست."
        )
        return await play_error(request, p.PlayError(label, exc.status_code))

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, conn=Depends(connection)):
        actor = who(request, conn)
        return go(v.landing(actor) if actor else ENTRANCE)

    def room_destination(conn, supplied, actor):
        code = rooms.code_from(supplied)
        if not ROOM_CODE.fullmatch(code) or actor["role"] != "member":
            raise p.PlayError("اتاق پیدا نشد یا خصوصی است.", 404)
        room, _ = rooms.fetch(conn, code, actor)
        return f"/play/family/room/{room['code']}"

    @app.get("/entrance", response_class=HTMLResponse)
    def entrance(request: Request, conn=Depends(connection)):
        if not credential_transport(request):
            raise p.PlayError("برای ورود به دمو از نشانی امن استفاده کنید.", 403)
        current = who(request, conn)
        room = rooms.code_from(request.query_params.get("room"))
        if room and not ROOM_CODE.fullmatch(room):
            raise p.PlayError("اتاق پیدا نشد یا خصوصی است.", 404)
        if room and current and current["role"] == "member":
            return go(room_destination(conn, room, current))
        people = []
        if not room and current:
            if current["role"] == "admin":
                people = p.rows(
                    conn,
                    """SELECT a.id,a.name,a.role,a.age,f.name AS family FROM play_accounts a
                    JOIN play_families f ON f.id=a.family_id WHERE a.active=1
                    AND a.role<>'admin' ORDER BY f.rowid,a.rowid""",
                )
            elif current["role"] == "visitor":
                people = p.rows(
                    conn,
                    """SELECT id,name,avatar,age FROM play_accounts WHERE family_id=?
                    AND active=1 AND role='member' ORDER BY rowid""",
                    current["family_id"],
                )
        return render(
            request,
            "play_login.html",
            {
                "people": people,
                "room": room,
                "actor": current,
                "landing": v.landing(current) if current else None,
            },
        )

    @app.get("/admin/login", response_class=HTMLResponse)
    def admin_login_page(request: Request, conn=Depends(connection)):
        if not credential_transport(request):
            raise p.PlayError("برای ورود مدیر از نشانی امن استفاده کنید.", 403)
        actor = who(request, conn)
        if actor and actor["role"] == "admin":
            return go(v.landing(actor))
        return render(request, "play_login.html", {"admin_login": True})

    @app.post("/admin/login")
    def admin_login(request: Request, form=Depends(read_form), conn=Depends(connection)):
        if not credential_transport(request):
            raise p.PlayError("برای ورود مدیر از نشانی امن استفاده کنید.", 403)
        rate(request, "staff")
        supplied = str(form.get("operator_key") or "").encode()
        if not hmac.compare_digest(supplied, operator_key):
            raise p.PlayError("کلید ورود مدیر معتبر نیست.", 401)
        with p.writing(conn):
            if who(request, conn):
                csrf(request, form)
            actor = p.need(
                p.one(
                    conn,
                    "SELECT * FROM play_accounts WHERE id=? AND role='admin' AND active=1",
                    p.ADMIN,
                )
            )
            raw = new_session(conn, actor["id"], request)
        return cookie(go(v.landing(actor)), request, raw)

    @app.post("/entry-code")
    def issue_entry_code(request: Request, form=Depends(read_form), conn=Depends(connection)):
        if not credential_transport(request):
            raise p.PlayError("برای جابه‌جایی حساب از نشانی امن استفاده کنید.", 403)
        with p.writing(conn):
            actor = who(request, conn)
            if not actor:
                raise p.PlayError("ابتدا با حساب مدیر وارد شوید.", 401)
            ops.require(actor, "admin")
            csrf(request, form)
            target = p.need(
                p.one(
                    conn,
                    "SELECT id,name FROM play_accounts WHERE id=? AND role<>'admin' AND active=1",
                    form.get("account"),
                )
            )
            raw = secrets.token_urlsafe(32)
            conn.execute("DELETE FROM play_sessions WHERE expires_at<=?", (p.now(),))
            conn.execute(
                "INSERT INTO play_sessions VALUES (?,?,?)",
                (digest(raw, "entry"), target["id"], p.now() + ENTRY_TTL),
            )
        return render(
            request,
            "play_login.html",
            {
                "issued_code": raw,
                "issued_name": target["name"],
                "landing": "/play/entrance",
            },
        )

    @app.post("/enter")
    def enter(request: Request, form=Depends(read_form), conn=Depends(connection)):
        if not credential_transport(request):
            raise p.PlayError("برای ورود به دمو از نشانی امن استفاده کنید.", 403)
        rate(request, "entry")
        code = str(form.get("entry_code") or "").strip()
        account = form.get("account")
        if account == p.ADMIN:
            raise p.PlayError("ورود مدیر از میز انتخاب حساب ممکن نیست.", 403)
        if code and account:
            raise p.PlayError("فقط یک روش ورود را انتخاب کنید.", 400)
        with p.writing(conn):
            current = who(request, conn)
            if current:
                csrf(request, form)
            if code:
                token_hash = digest(code, "entry") if TOKEN.fullmatch(code) else ""
                actor = p.one(
                    conn,
                    """SELECT a.* FROM play_sessions s JOIN play_accounts a ON a.id=s.account_id
                    WHERE s.token_hash=? AND s.expires_at>? AND a.active=1 AND a.role<>'admin'""",
                    token_hash,
                    p.now(),
                )
                if not actor:
                    raise p.PlayError("کد ورود معتبر نیست یا استفاده شده است.", 401)
                conn.execute("DELETE FROM play_sessions WHERE token_hash=?", (token_hash,))
            elif not current:
                raise p.PlayError("برای ورود، کد یک‌بارمصرف لازم است.", 401)
            elif current["role"] in {"admin", "visitor"}:
                actor = p.need(
                    p.one(
                        conn,
                        """SELECT * FROM play_accounts WHERE id=? AND active=1 AND role<>'admin'
                    AND (?='admin' OR (family_id=? AND role='member'))""",
                        account,
                        current["role"],
                        current["family_id"],
                    )
                )
            else:
                raise p.PlayError("برای تغییر حساب، کد یک‌بارمصرف لازم است.", 403)
            room = form.get("room")
            target = room_destination(conn, room, actor) if room else v.landing(actor)
            raw = new_session(conn, actor["id"], request)
        return cookie(go(target), request, raw)

    @app.get("/invitation/{code}")
    def invitation(request: Request, code: str, conn=Depends(connection)):
        if not credential_transport(request):
            raise p.PlayError("برای پذیرش دعوت از نشانی امن استفاده کنید.", 403)
        ops.available_invite(conn, code)
        return render(request, "play_login.html", {"invitation_code": code})

    @app.post("/invitation/{code}")
    def invite_accept(
        request: Request, code: str, form=Depends(read_form), conn=Depends(connection)
    ):
        if not credential_transport(request):
            raise p.PlayError("برای پذیرش دعوت از نشانی امن استفاده کنید.", 403)
        rate(request, "entry")
        with p.writing(conn):
            if who(request, conn):
                csrf(request, form)
            account = ops.accept_invite(conn, code, form.get("name"), form.get("avatar"))
            raw = new_session(conn, account, request)
        return cookie(go("/play/family/home"), request, raw)

    @app.get("/state/{code}")
    def state(request: Request, code: str, conn=Depends(connection)):
        actor = who(request, conn)
        if not actor:
            raise p.PlayError("نشست شما پایان یافته است؛ دوباره وارد شوید.", 401)
        return rooms.room_state(conn, actor, code)

    @app.get("/pulse")
    def pulse(request: Request, conn=Depends(connection)):
        conn.execute("BEGIN")  # Sales, balance and rows come from the same committed snapshot.
        actor = who(request, conn)
        if not actor:
            raise p.PlayError("نشست شما پایان یافته است.", 401)
        family = actor["family_id"]
        status = {
            "account": actor["id"],
            "unread": v.unread(conn, actor["id"]),
            "balance": p.balance(conn, family) if family else None,
        }
        view = request.query_params.get("view")
        area = v.AREAS[actor["role"]]
        if area == "visitor" and view in {"home", "sales", "wallet"}:
            status["sales"] = p.visitor_stats(conn, actor)
        tx = request.query_params.get("tx")
        if view == "wallet" and family:
            items = p.ledger(conn, family, tx)
        elif area == "visitor" and view in {"home", "sales"}:
            items = p.sales_list(conn, actor["id"], limit=3 if view == "home" else 100)
        else:
            return status
        rev = table_revision(items)
        status["table_revision"] = rev
        if request.query_params.get("table_revision") != rev:
            macros = templates.env.get_template("play_bits.html").module
            status["table_html"] = (
                str(macros.tx_table(items, area, tx))
                if view == "wallet"
                else str(macros.sales_table(items))
            )
        return status

    def sign_in_required(request, *, admin=False):
        if want_json(request):
            raise p.PlayError("ابتدا وارد حساب خود شوید.", 401)
        return go(ADMIN_LOGIN if admin else ENTRANCE)

    @app.get("/family/game/{key}")
    @app.get("/admin/game/{key}")
    def game_page(request: Request, key: str, conn=Depends(connection)):
        area = "admin" if request.url.path.startswith("/play/admin/") else "family"
        actor = who(request, conn)
        if not actor:
            return sign_in_required(request, admin=area == "admin")
        ops.require(actor, "admin" if area == "admin" else "member")
        game = v.get_game(conn, key)
        context = v.actor_context(conn, actor, area, "games")
        context.update(
            game=game,
            categories=v.categories(conn) if key == "quiz" else [],
            preview=area == "admin",
            boards=v.game_boards(conn, key, actor["family_id"]) if area == "family" else {},
        )
        return render(request, "play_game.html", context)

    @app.get("/family/room/{code}")
    def room_page(request: Request, code: str, conn=Depends(connection)):
        actor = who(request, conn)
        if not actor:
            return go("/play/entrance?" + urlencode({"room": rooms.code_from(code)}))
        context = v.actor_context(conn, actor, "family", "rooms")
        context["room"] = rooms.room_state(conn, actor, code)
        return render(request, "play_room.html", context)

    @app.get("/{area}/result/{result_id}")
    def result_page(request: Request, area: str, result_id: str, conn=Depends(connection)):
        actor = who(request, conn)
        if not actor:
            return sign_in_required(request, admin=area == "admin")
        if v.AREAS[actor["role"]] != area:
            raise p.PlayError("به این نتیجه دسترسی ندارید.", 403)
        item = p.need(
            p.one(
                conn,
                """SELECT p.*,g.title,f.name AS family FROM play_results p
            JOIN play_games g ON p.game_key=g.key JOIN play_families f ON p.family_id=f.id
            WHERE p.id=? AND (?='admin' OR p.family_id=?)""",
                result_id,
                actor["role"],
                actor["family_id"],
            )
        )
        item["result"] = json.loads(item.pop("details_json"))
        current = {"admin": "reports", "visitor": "family", "family": "rooms"}[area]
        context = v.actor_context(conn, actor, area, current)
        return render(request, "play_result.html", dict(context, item=item))

    @app.get("/admin/export")
    def export(request: Request, conn=Depends(connection)):
        actor = who(request, conn)
        if not actor:
            return sign_in_required(request, admin=True)
        ops.require(actor, "admin")
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["شناسه", "خانواده", "نوع", "مقدار", "زمان", "دلیل"])
        for e in p.ledger(conn, limit=-1):

            def neutralize(cell):
                return "'" + cell if cell.lstrip().startswith(("=", "+", "-", "@")) else cell

            writer.writerow(
                [
                    e["id"],
                    neutralize(e["family"]),
                    p.EVENTS[e["kind"]],
                    e["amount"],
                    p.when(e["created_at"]),
                    neutralize(e["reason"]),
                ]
            )
        return Response(
            "\ufeff" + output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="kilos-play-ledger.csv"'},
        )

    @app.get("/{area}/{page}", response_class=HTMLResponse)
    def generic(request: Request, area: str, page: str, conn=Depends(connection)):
        actor = who(request, conn)
        if not actor:
            return sign_in_required(request, admin=area == "admin")
        return screen(request, conn, actor, area, page)

    @app.post("/action")
    def action(request: Request, form=Depends(read_form), conn=Depends(connection)):
        verb = form.get("action")
        session = None
        with p.writing(conn):
            actor = who(request, conn)
            if not actor:
                raise p.PlayError("نشست شما پایان یافته است؛ دوباره وارد شوید.", 401)
            csrf(request, form)
            dest, notice = back(form, actor), verb
            if verb == "logout":
                conn.execute(
                    "DELETE FROM play_sessions WHERE token_hash=?",
                    (digest(request.cookies.get(COOKIE, "")),),
                )
                return cookie(go("/play/entrance"), request, "", remove=True)
            if verb in ADMIN_ACTIONS:
                ops.require(actor, "admin")
                code = ADMIN_ACTIONS[verb](conn, actor, form)
                if verb == "visitor" and not form.get("id"):
                    dest = "/play/admin/visitors?" + urlencode({"edit": code})
                if verb == "campaign" and not form.get("id"):
                    dest = "/play/admin/campaigns?" + urlencode({"edit": code})
            elif verb == "family":
                ops.require(actor, "admin")
                fam = ops.family_for(conn, actor, form.get("family"))
                name = p.text(form.get("name"), "نام خانواده", 70)
                conn.execute("UPDATE play_families SET name=? WHERE id=?", (name, fam["id"]))
                p.audit(conn, actor["id"], "family", f"«{name}» به‌روزرسانی شد.")
            elif verb in {"invite", "revoke"}:
                ops.invite(conn, actor, form, revoke=verb == "revoke")
            elif verb == "approve":
                ops.require(actor, "admin")
                _, created = ops.approve_sale(conn, actor, form.get("id"))
                notice = "approve" if created else "approved"
            elif verb == "claim":
                ops.claim(conn, actor, form.get("id"))
            elif verb == "profile":
                ops.profile(conn, actor, form)
            elif verb == "notices":
                conn.execute(
                    "UPDATE play_notices SET read_at=? WHERE account_id=? AND read_at IS NULL",
                    (p.now(), actor["id"]),
                )
            elif verb in {"create_room", "admin_room"}:
                host = None
                if verb == "admin_room":
                    ops.require(actor, "admin")
                    host = p.need(
                        p.one(
                            conn, "SELECT * FROM play_accounts WHERE id=? AND active=1", p.PRIMARY
                        )
                    )
                code = rooms.create(conn, actor, form, host=host)
                dest = (
                    f"/play/family/room/{code}"
                    if not host
                    else "/play/admin/control?" + urlencode({"room": code})
                )
            elif verb == "join_room":
                code = rooms.join(conn, actor, form.get("code"))
                dest = f"/play/family/room/{code}"
            elif verb == "room_move":
                result = rooms.play_action(conn, actor, form.get("code"), form)
                if want_json(request):
                    return JSONResponse(result)
                dest = f"/play/family/room/{result['code']}"
            elif verb == "reset":
                ops.require(actor, "admin")
                if str(form.get("confirm") or "").strip() != "بازنشانی":
                    raise p.PlayError("برای بازنشانی، واژهٔ «بازنشانی» را دقیق وارد کنید.", 409)
                p.reset(conn)
                session = new_session(conn, p.ADMIN, request)
                dest = "/play/admin/control"
            else:
                raise p.PlayError("عملیات پیدا نشد.", 404)
        if notice in SAVED:
            dest += ("&" if "?" in dest else "?") + urlencode({"done": notice})
        response = go(dest)
        return cookie(response, request, session) if session else response

    return app

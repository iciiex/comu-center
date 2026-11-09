"""Kiloos Club prototype — FastAPI app.

MODE: P. One tenant, demo login (OD-01), sample data clearly labelled in the UI.
Scope: the end-to-end demo path from `.agent/playbooks/prototype-9-days.md`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import threading
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import db, repo, sales
from app.config import Settings
from app.jalali import format_jalali, to_persian_digits
from app.repo import DomainError
from app.security import (
    CurrentUser,
    clear_session,
    csrf_for,
    csrf_token,
    current_user,
    make_token,
    read_token,
    session_token,
    set_session,
)

APP_DIR = Path(__file__).resolve().parent
MAX_EVIDENCE_BYTES = 4 * 1024 * 1024
ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class LoginRequired(Exception):
    """Raised when an anonymous user hits a protected page."""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()
    db.init_db(settings.db_path, settings.evidence_dir)

    app = FastAPI(title="Kiloos Club", docs_url="/api/docs", redoc_url=None)
    app.state.settings = settings
    app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

    templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
    templates.env.filters["fa"] = to_persian_digits
    templates.env.filters["jdate"] = format_jalali
    templates.env.filters["jdatetime"] = lambda v: format_jalali(v, with_time=True)
    app.state.templates = templates

    def url_session(request: Request) -> str | None:
        """The token to keep in internal links — only when it came from the URL."""
        candidate = request.query_params.get("s")
        if candidate and read_token(
            candidate, settings.secret, ttl_seconds=settings.session_ttl_seconds
        ):
            return candidate
        return None

    def with_token(path: str, token: str | None) -> str:
        if not token:
            return path
        separator = "&" if "?" in path else "?"
        return f"{path}{separator}s={token}"

    @pass_context
    def url(ctx, path: str) -> str:
        return with_token(path, ctx.get("s"))

    templates.env.globals["url"] = url

    def go(path: str, request: Request) -> RedirectResponse:
        return RedirectResponse(with_token(path, url_session(request)), status_code=303)

    def page(
        request: Request,
        name: str,
        context: dict,
        *,
        status_code: int = 200,
        user: CurrentUser | None = None,
    ) -> HTMLResponse:
        base = {
            "request": request,
            "user": user,
            "active": context.pop("active", ""),
            "demo": True,
            "s": url_session(request),
            "csrf": csrf_token(request),
        }
        base.update(context)
        return templates.TemplateResponse(
            request=request, name=name, context=base, status_code=status_code
        )

    def conn_dep() -> Iterator[sqlite3.Connection]:
        conn = db.connect(settings.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def require_user(
        request: Request, conn: sqlite3.Connection = Depends(conn_dep)
    ) -> CurrentUser:
        user = current_user(request, conn)
        if user is None:
            raise LoginRequired()
        return user

    def require_staff(
        request: Request, conn: sqlite3.Connection = Depends(conn_dep)
    ) -> CurrentUser:
        user = current_user(request, conn)
        if user is None:
            raise LoginRequired()
        if not user.is_staff:
            raise HTTPException(status_code=403, detail="دسترسی به این بخش مجاز نیست.")
        return user

    def require_admin(
        request: Request, conn: sqlite3.Connection = Depends(conn_dep)
    ) -> CurrentUser:
        user = current_user(request, conn)
        if user is None:
            raise LoginRequired()
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="این عملیات فقط برای مدیر سیستم است.")
        return user

    # ------------------------------------------------------------------ errors
    @app.exception_handler(LoginRequired)
    async def _login_required(request: Request, exc: LoginRequired) -> RedirectResponse:
        return RedirectResponse("/login", status_code=303)

    ERROR_MESSAGES = {
        400: "درخواست نامعتبر است.",
        403: "دسترسی به این بخش مجاز نیست.",
        404: "صفحه یا مورد درخواستی یافت نشد.",
        405: "این عملیات مجاز نیست.",
        422: "داده‌های ارسالی معتبر نیست.",
        429: "تعداد درخواست‌ها بیش از حد مجاز است.",
    }

    @app.exception_handler(HTTPException)
    async def _http_error(request: Request, exc: HTTPException) -> HTMLResponse:
        return page(
            request,
            "error.html",
            {"message": exc.detail or "خطای غیرمنتظره", "code": exc.status_code},
            status_code=exc.status_code,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _starlette_error(
        request: Request, exc: StarletteHTTPException
    ) -> HTMLResponse:
        detail = exc.detail if isinstance(exc.detail, str) else ""
        message = (
            detail
            if detail and detail not in {"Not Found", "Method Not Allowed"}
            else ERROR_MESSAGES.get(exc.status_code, "خطای غیرمنتظره")
        )
        return page(
            request,
            "error.html",
            {"message": message, "code": exc.status_code},
            status_code=exc.status_code,
        )

    # ---------------------------------------------------------- hardening
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    CSRF_EXEMPT = {"/demo-login"}  # no session exists yet; documented in api-spec

    app.state.login_attempts: dict[str, list[float]] = {}
    app.state.login_lock = threading.Lock()

    def login_rate_limited(key: str) -> bool:
        """In-memory token bucket. Single-process only (documented limitation)."""
        moment = time.monotonic()
        window = settings.login_rate_window
        with app.state.login_lock:
            hits = [t for t in app.state.login_attempts.get(key, []) if moment - t < window]
            limited = len(hits) >= settings.login_rate_limit
            if not limited:
                hits.append(moment)
            app.state.login_attempts[key] = hits
            return limited

    async def csrf_guard(request: Request) -> None:
        """Reject form posts whose CSRF value does not match the session token.

        Implemented as a route dependency (not middleware) so the parsed form is
        cached and multipart uploads stay intact for the handler.
        """
        if request.method in SAFE_METHODS or request.url.path in CSRF_EXEMPT:
            return
        token = session_token(request)
        if token is None:
            raise LoginRequired()
        form = await request.form()
        supplied = str(form.get("csrf") or "")
        if not hmac.compare_digest(supplied, csrf_for(token, settings.secret)):
            raise HTTPException(
                status_code=403,
                detail="اعتبار فرم منقضی شده است؛ صفحه را دوباره بارگذاری کنید.",
            )

    @app.middleware("http")
    async def hardening(request: Request, call_next):
        if request.method == "POST" and request.url.path == "/demo-login":
            client_ip = request.client.host if request.client else "unknown"
            if login_rate_limited(client_ip):
                return page(
                    request,
                    "error.html",
                    {
                        "code": 429,
                        "message": (
                            "تلاش‌های ورود بیش از حد مجاز است؛ "
                            "یک دقیقه بعد دوباره امتحان کنید."
                        ),
                    },
                    status_code=429,
                )

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        # frame-ancestors stays open on purpose: the shared preview embeds this app
        # in an iframe. Narrow it before real users (documented in api-spec).
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "form-action 'self'; base-uri 'self'; frame-ancestors *"
        )
        return response

    # ------------------------------------------------------------------ public
    @app.get("/health")
    def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "mode": "P",
                "env": settings.env,
                "demo_data": True,
                "message": "Prototype — sample data only",
            }
        )

    @app.get("/", response_class=HTMLResponse)
    def root(request: Request, conn: sqlite3.Connection = Depends(conn_dep)):
        user = current_user(request, conn)
        return go("/home" if user else "/login", request)

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, conn: sqlite3.Connection = Depends(conn_dep)):
        users = conn.execute(
            """SELECT id, full_name, role FROM users
               WHERE role IN ('visitor', 'operator', 'admin') AND is_active = 1
               ORDER BY CASE role WHEN 'visitor' THEN 0 WHEN 'operator' THEN 1 ELSE 2 END,
                        full_name"""
        ).fetchall()
        return page(request, "login.html", {"people": users})

    @app.post("/demo-login")
    def demo_login(
        user_id: str = Form(...),
        conn: sqlite3.Connection = Depends(conn_dep),
    ) -> RedirectResponse:
        row = conn.execute(
            "SELECT id, role FROM users WHERE id = ? AND is_active = 1", (user_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="کاربر نمایشی یافت نشد.")
        target = "/admin/submissions" if row["role"] in {"operator", "admin"} else "/home"
        token = make_token(row["id"], settings.secret)
        response = RedirectResponse(with_token(target, token), status_code=303)
        set_session(response, row["id"], settings.secret, token)
        return response

    @app.post("/logout", dependencies=[Depends(csrf_guard)])
    def logout() -> RedirectResponse:
        response = RedirectResponse("/login", status_code=303)
        clear_session(response)
        return response

    # ---------------------------------------------------------------- visitor
    @app.get("/home", response_class=HTMLResponse)
    def home(
        request: Request,
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        missions = repo.list_active_missions(conn, user)
        balance = repo.wallet_balance(conn, user.id)
        _, rank = repo.leaderboard(conn, user)
        recent = repo.list_user_submissions(conn, user.id)[:3]
        return page(
            request,
            "home.html",
            {
                "active": "home",
                "missions": missions,
                "balance": balance,
                "rank": rank,
                "recent": recent,
            },
            user=user,
        )

    @app.get("/missions", response_class=HTMLResponse)
    def missions_page(
        request: Request,
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        return page(
            request,
            "missions.html",
            {"active": "missions", "missions": repo.list_active_missions(conn, user)},
            user=user,
        )

    @app.get("/missions/{mission_id}", response_class=HTMLResponse)
    def mission_page(
        mission_id: str,
        request: Request,
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        mission = repo.get_mission_for_user(conn, mission_id, user)
        if mission is None:
            raise HTTPException(status_code=404, detail="مأموریت فعال نیست یا برای شما مجاز نیست.")
        submissions = repo.list_user_submissions(conn, user.id, mission_id)
        return page(
            request,
            "mission.html",
            {
                "active": "missions",
                "mission": mission,
                "submissions": submissions,
                "request_id": str(uuid.uuid4()),
                "remaining": max(0, mission["max_per_user"] - len(submissions)),
            },
            user=user,
        )

    @app.post(
        "/missions/{mission_id}/submissions",
        response_class=HTMLResponse,
        dependencies=[Depends(csrf_guard)],
    )
    async def submit_mission(
        mission_id: str,
        request: Request,
        note: str = Form(""),
        request_id: str = Form(...),
        evidence: UploadFile | None = File(None),
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        mission = repo.get_mission_for_user(conn, mission_id, user)
        if mission is None:
            raise HTTPException(status_code=404, detail="مأموریت فعال نیست یا برای شما مجاز نیست.")

        def render_error(message: str, status_code: int = 400):
            return page(
                request,
                "mission.html",
                {
                    "active": "missions",
                    "mission": mission,
                    "submissions": repo.list_user_submissions(conn, user.id, mission_id),
                    "request_id": request_id,
                    "remaining": max(0, mission["max_per_user"]
                                     - repo.count_user_submissions(conn, user.id, mission_id)),
                    "error": message,
                },
                status_code=status_code,
                user=user,
            )

        stored: dict | None = None
        if evidence is not None and evidence.filename:
            content_type = evidence.content_type or ""
            if content_type not in ALLOWED_TYPES:
                return render_error("فقط تصویر JPG، PNG یا WEBP مجاز است.", 422)
            raw = await evidence.read(MAX_EVIDENCE_BYTES + 1)
            if len(raw) > MAX_EVIDENCE_BYTES:
                return render_error("حجم تصویر باید کمتر از ۴ مگابایت باشد.", 422)
            if not raw:
                return render_error("فایل تصویر خالی است.", 422)
            file_id = str(uuid.uuid4())
            relative = f"{file_id}{ALLOWED_TYPES[content_type]}"
            (settings.evidence_dir / relative).write_bytes(raw)
            stored = {
                "file_name": evidence.filename[:120],
                "content_type": content_type,
                "storage_path": relative,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }

        try:
            submission, _ = repo.create_submission(
                conn, mission, user, request_id=request_id, note=note, evidence=stored
            )
        except DomainError as exc:
            return render_error(exc.message, 409 if exc.code == "MAX_ATTEMPTS_REACHED" else 422)

        return go(f"/submissions/{submission['id']}", request)

    @app.get("/submissions/{submission_id}", response_class=HTMLResponse)
    def submission_page(
        submission_id: str,
        request: Request,
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        submission = repo.submission_detail(conn, submission_id)
        if submission is None:
            raise HTTPException(status_code=404, detail="درخواست یافت نشد.")
        if submission["organization_id"] != user.organization_id:
            raise HTTPException(status_code=403, detail="دسترسی به این درخواست مجاز نیست.")
        if submission["user_id"] != user.id and not user.is_staff:
            raise HTTPException(status_code=403, detail="دسترسی به این درخواست مجاز نیست.")
        event = repo.score_event_for_source(conn, submission_id)
        reversal = repo.reversal_for(conn, event["id"]) if event else None
        return page(
            request,
            "submission.html",
            {
                "active": "missions",
                "submission": submission,
                "evidences": repo.submission_evidences(conn, submission_id),
                "event": event,
                "reversal": reversal,
                "can_correct": bool(
                    user.is_admin and event and not event["corrects_event_id"] and not reversal
                ),
                "explain": json.loads(event["explain_json"]) if event else None,
            },
            user=user,
        )

    @app.get("/score", response_class=HTMLResponse)
    def score_page(
        request: Request,
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        return page(
            request,
            "score.html",
            {
                "active": "score",
                "balance": repo.wallet_balance(conn, user.id),
                "history": repo.score_history(conn, user.id),
            },
            user=user,
        )

    @app.get("/leaderboard", response_class=HTMLResponse)
    def leaderboard_page(
        request: Request,
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        board, rank = repo.leaderboard(conn, user)
        return page(
            request,
            "leaderboard.html",
            {
                "active": "leaderboard",
                "board": board,
                "rank": rank,
                "competition": repo.active_competition(conn, user.organization_id),
            },
            user=user,
        )

    @app.get("/evidence/{evidence_id}")
    def evidence_file(
        evidence_id: str,
        user: CurrentUser = Depends(require_user),
        conn: sqlite3.Connection = Depends(conn_dep),
    ) -> FileResponse:
        row = repo.evidence(conn, evidence_id)
        if row is None:
            raise HTTPException(status_code=404, detail="شاهد یافت نشد.")
        if row["organization_id"] != user.organization_id:
            raise HTTPException(status_code=403, detail="دسترسی مجاز نیست.")
        if row["owner_id"] != user.id and not user.is_staff:
            raise HTTPException(status_code=403, detail="دسترسی مجاز نیست.")
        path = settings.evidence_dir / row["storage_path"]
        if not path.is_file():
            raise HTTPException(status_code=404, detail="فایل شاهد در دسترس نیست.")
        return FileResponse(path, media_type=row["content_type"])

    # ------------------------------------------------------------------ admin
    @app.get("/admin/submissions", response_class=HTMLResponse)
    def admin_queue(
        request: Request,
        status: str = "submitted",
        page_no: int = Query(1, alias="page", ge=1),
        user: CurrentUser = Depends(require_staff),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        if status not in {"submitted", "approved", "rejected"}:
            status = "submitted"
        size = settings.queue_page_size
        total = repo.count_queue(conn, user.organization_id, status)
        pages = max(1, -(-total // size))
        page_no = min(max(1, page_no), pages)
        return page(
            request,
            "admin_queue.html",
            {
                "active": "queue",
                "status": status,
                "total": total,
                "page": page_no,
                "pages": pages,
                "rows": repo.list_queue(
                    conn,
                    user.organization_id,
                    status,
                    limit=size,
                    offset=(page_no - 1) * size,
                ),
            },
            user=user,
        )

    @app.get("/admin/submissions/{submission_id}", response_class=HTMLResponse)
    def admin_review(
        submission_id: str,
        request: Request,
        user: CurrentUser = Depends(require_staff),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        submission = repo.submission_detail(conn, submission_id)
        if submission is None:
            raise HTTPException(status_code=404, detail="درخواست یافت نشد.")
        if submission["organization_id"] != user.organization_id:
            raise HTTPException(status_code=403, detail="خارج از محدوده سازمانی شما.")
        event = repo.score_event_for_source(conn, submission_id)
        return page(
            request,
            "admin_review.html",
            {
                "active": "queue",
                "submission": submission,
                "evidences": repo.submission_evidences(conn, submission_id),
                "event": event,
            },
            user=user,
        )

    @app.post(
        "/admin/submissions/{submission_id}/review",
        response_class=HTMLResponse,
        dependencies=[Depends(csrf_guard)],
    )
    def admin_decide(
        submission_id: str,
        request: Request,
        decision: str = Form(...),
        reason: str = Form(""),
        user: CurrentUser = Depends(require_staff),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        submission = repo.submission_detail(conn, submission_id)
        if submission is None:
            raise HTTPException(status_code=404, detail="درخواست یافت نشد.")
        if submission["organization_id"] != user.organization_id:
            raise HTTPException(status_code=403, detail="خارج از محدوده سازمانی شما.")
        try:
            _, created = repo.review_submission(conn, submission, user, decision, reason)
        except DomainError as exc:
            return page(
                request,
                "admin_review.html",
                {
                    "active": "queue",
                    "submission": repo.submission_detail(conn, submission_id),
                    "evidences": repo.submission_evidences(conn, submission_id),
                    "event": repo.score_event_for_source(conn, submission_id),
                    "error": exc.message,
                },
                status_code=409,
                user=user,
            )
        suffix = "&ok=1" if created else ""
        return go(f"/admin/submissions?status=submitted{suffix}", request)

    @app.post(
        "/admin/score-events/{event_id}/reverse",
        response_class=HTMLResponse,
        dependencies=[Depends(csrf_guard)],
    )
    def admin_reverse_score(
        event_id: str,
        request: Request,
        reason: str = Form(""),
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        """Correct a score event with a negative event — history is never edited."""
        event = repo.score_event_detail(conn, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="رخداد امتیاز یافت نشد.")
        if event["organization_id"] != user.organization_id:
            raise HTTPException(status_code=403, detail="خارج از محدوده سازمانی شما.")
        try:
            repo.reverse_score_event(conn, event, user, reason)
        except DomainError as exc:
            return page(
                request,
                "error.html",
                {"code": 409, "message": exc.message},
                status_code=409,
                user=user,
            )
        return go(f"/submissions/{event['source_id']}?reversed=1", request)

    # ------------------------------------------------------------------ sales
    def sales_page_context(conn: sqlite3.Connection, org_id: str) -> dict:
        mapping = conn.execute(
            """SELECT m.user_external_id, u.full_name
               FROM sales_user_map m JOIN users u ON u.id = m.user_id
               WHERE m.organization_id = ? ORDER BY m.user_external_id""",
            (org_id,),
        ).fetchall()
        rule = conn.execute(
            """SELECT * FROM scoring_rule_versions
               WHERE rule_code = 'SALES_AMOUNT_SAMPLE' AND status = 'published'
               ORDER BY version DESC LIMIT 1"""
        ).fetchone()
        return {"mapping": mapping, "rule": rule}

    @app.get("/admin/sales", response_class=HTMLResponse)
    def admin_sales(
        request: Request,
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        return page(
            request,
            "admin_sales.html",
            {"active": "sales", "imports": repo.list_sales_imports(conn, user.organization_id)},
            user=user,
        )

    @app.get("/admin/sales/new", response_class=HTMLResponse)
    def admin_sales_new(
        request: Request,
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        return page(
            request,
            "admin_sales_new.html",
            {"active": "sales", **sales_page_context(conn, user.organization_id)},
            user=user,
        )

    @app.post(
        "/admin/sales",
        response_class=HTMLResponse,
        dependencies=[Depends(csrf_guard)],
    )
    async def admin_sales_upload(
        request: Request,
        file: UploadFile | None = File(None),
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        def render_error(message: str, status_code: int):
            return page(
                request,
                "admin_sales_new.html",
                {
                    "active": "sales",
                    "error": message,
                    **sales_page_context(conn, user.organization_id),
                },
                status_code=status_code,
                user=user,
            )

        if file is None or not file.filename:
            return render_error("فایلی انتخاب نشده است.", 422)
        if not file.filename.lower().endswith(".xlsx"):
            return render_error("فقط فایل اکسل با پسوند xlsx پذیرفته می‌شود.", 422)

        raw = await file.read(settings.sales_max_bytes + 1)
        if not raw:
            return render_error("فایل خالی است.", 422)
        if len(raw) > settings.sales_max_bytes:
            limit_mb = settings.sales_max_bytes // (1024 * 1024)
            return render_error(f"حجم فایل باید کمتر از {limit_mb} مگابایت باشد.", 422)

        sha = hashlib.sha256(raw).hexdigest()
        duplicate = repo.sales_import_by_fingerprint(conn, user.organization_id, sha)
        if duplicate is not None:
            return render_error(
                "این فایل قبلاً آپلود شده است "
                f"(import {duplicate['id'][:8]}…، {duplicate['status']}).",
                409,
            )

        try:
            parsed = sales.parse_workbook(raw, settings.sales_max_rows)
        except sales.SalesFileError as exc:
            return render_error(str(exc), 422)

        validated = sales.validate_rows(
            parsed,
            repo.sales_user_map(conn, user.organization_id),
            existing_ids=repo.sales_external_ids(conn, user.organization_id),
        )
        import_row = repo.create_sales_import(
            conn,
            user.organization_id,
            user.id,
            file.filename[:160],
            sha,
            validated,
        )
        return go(f"/admin/sales/{import_row['id']}", request)

    @app.get("/admin/sales/{import_id}", response_class=HTMLResponse)
    def admin_sale_detail(
        import_id: str,
        request: Request,
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        import_row = repo.sales_import(conn, import_id, user.organization_id)
        if import_row is None:
            raise HTTPException(status_code=404, detail="import یافت نشد.")
        counts = repo.sales_record_counts(conn, import_id)
        scored_points = conn.execute(
            """SELECT COALESCE(SUM(points), 0) AS total FROM score_events
               WHERE source_type = 'sales_record'
                 AND source_id IN (SELECT id FROM sales_records WHERE import_id = ?)""",
            (import_id,),
        ).fetchone()["total"]
        accounted = counts["valid"] + counts["invalid"] + counts["duplicate"] + counts["scored"]
        return page(
            request,
            "admin_sale_detail.html",
            {
                "active": "sales",
                "import": import_row,
                "counts": counts,
                "records": repo.sales_records(conn, import_id, limit=200),
                "scored_points": scored_points,
                "rows_ok": accounted == import_row["row_count"],
                "points_ok": int(scored_points) == int(import_row["points_sum"]),
            },
            user=user,
        )

    @app.post(
        "/admin/sales/{import_id}/process",
        response_class=HTMLResponse,
        dependencies=[Depends(csrf_guard)],
    )
    def admin_sales_process(
        import_id: str,
        request: Request,
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        import_row = repo.sales_import(conn, import_id, user.organization_id)
        if import_row is None:
            raise HTTPException(status_code=404, detail="import یافت نشد.")
        try:
            result = repo.process_sales_import(conn, import_row, user)
        except DomainError as exc:
            return page(
                request,
                "error.html",
                {"code": 409, "message": exc.message},
                status_code=409,
                user=user,
            )
        return go(f"/admin/sales/{import_id}?processed={result['created']}", request)

    @app.get("/admin/missions", response_class=HTMLResponse)
    def admin_missions(
        request: Request,
        user: CurrentUser = Depends(require_staff),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        return page(
            request,
            "admin_missions.html",
            {
                "active": "missions",
                "missions": repo.list_missions_admin(conn, user.organization_id),
            },
            user=user,
        )

    @app.get("/admin/missions/new", response_class=HTMLResponse)
    def admin_mission_new(
        request: Request,
        user: CurrentUser = Depends(require_admin),
    ):
        return page(
            request,
            "admin_mission_form.html",
            {"active": "missions", "mission": None, "form": {}},
            user=user,
        )

    @app.post(
        "/admin/missions/new",
        response_class=HTMLResponse,
        dependencies=[Depends(csrf_guard)],
    )
    def admin_mission_create(
        request: Request,
        title: str = Form(""),
        description: str = Form(""),
        points: str = Form("0"),
        max_per_user: str = Form("1"),
        starts_on: str = Form(""),
        ends_on: str = Form(""),
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        form = {
            "title": title,
            "description": description,
            "points": points,
            "max_per_user": max_per_user,
            "starts_on": starts_on,
            "ends_on": ends_on,
        }
        try:
            repo.create_mission(conn, user.organization_id, form, user)
        except DomainError as exc:
            return page(
                request,
                "admin_mission_form.html",
                {"active": "missions", "mission": None, "form": form, "error": exc.message},
                status_code=422,
                user=user,
            )
        return go("/admin/missions?created=1", request)

    @app.get("/admin/missions/{mission_id}", response_class=HTMLResponse)
    def admin_mission_edit(
        mission_id: str,
        request: Request,
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        mission = repo.mission_by_id(conn, mission_id, user.organization_id)
        if mission is None:
            raise HTTPException(status_code=404, detail="مأموریت یافت نشد.")
        form = {
            "title": mission["title"],
            "description": mission["description"],
            "points": mission["points"],
            "max_per_user": mission["max_per_user"],
            "starts_on": mission["starts_at"][:10],
            "ends_on": mission["ends_at"][:10],
        }
        return page(
            request,
            "admin_mission_form.html",
            {"active": "missions", "mission": mission, "form": form},
            user=user,
        )

    @app.post(
        "/admin/missions/{mission_id}",
        response_class=HTMLResponse,
        dependencies=[Depends(csrf_guard)],
    )
    def admin_mission_update(
        mission_id: str,
        request: Request,
        title: str = Form(""),
        description: str = Form(""),
        points: str = Form("0"),
        max_per_user: str = Form("1"),
        starts_on: str = Form(""),
        ends_on: str = Form(""),
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        mission = repo.mission_by_id(conn, mission_id, user.organization_id)
        if mission is None:
            raise HTTPException(status_code=404, detail="مأموریت یافت نشد.")
        form = {
            "title": title,
            "description": description,
            "points": points,
            "max_per_user": max_per_user,
            "starts_on": starts_on,
            "ends_on": ends_on,
        }
        try:
            new_version = repo.update_mission(conn, mission, form, user)
        except DomainError as exc:
            return page(
                request,
                "admin_mission_form.html",
                {"active": "missions", "mission": mission, "form": form, "error": exc.message},
                status_code=422,
                user=user,
            )
        suffix = "?versioned=1" if new_version else "?saved=1"
        return go(f"/admin/missions/{mission_id}{suffix}", request)

    @app.post("/admin/missions/{mission_id}/publish", dependencies=[Depends(csrf_guard)])
    def admin_mission_publish(
        mission_id: str,
        request: Request,
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ) -> RedirectResponse:
        mission = repo.mission_by_id(conn, mission_id, user.organization_id)
        if mission is None:
            raise HTTPException(status_code=404, detail="مأموریت یافت نشد.")
        try:
            repo.publish_mission(conn, mission, user)
        except DomainError as exc:
            raise HTTPException(status_code=409, detail=exc.message) from exc
        return go(f"/admin/missions/{mission_id}?published=1", request)

    @app.post("/admin/missions/{mission_id}/archive", dependencies=[Depends(csrf_guard)])
    def admin_mission_archive(
        mission_id: str,
        request: Request,
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ) -> RedirectResponse:
        mission = repo.mission_by_id(conn, mission_id, user.organization_id)
        if mission is None:
            raise HTTPException(status_code=404, detail="مأموریت یافت نشد.")
        repo.archive_mission(conn, mission, user)
        return go(f"/admin/missions/{mission_id}?archived=1", request)

    return app

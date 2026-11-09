"""Kiloos Club prototype — FastAPI app.

MODE: P. One tenant, demo login (OD-01), sample data clearly labelled in the UI.
Scope: the end-to-end demo path from `.agent/playbooks/prototype-9-days.md`.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import db, repo
from app.config import Settings
from app.jalali import format_jalali, to_persian_digits
from app.repo import DomainError
from app.security import (
    CurrentUser,
    clear_session,
    current_user,
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

    @app.exception_handler(HTTPException)
    async def _http_error(request: Request, exc: HTTPException) -> HTMLResponse:
        return page(
            request,
            "error.html",
            {"message": exc.detail or "خطای غیرمنتظره", "code": exc.status_code},
            status_code=exc.status_code,
        )

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
        return RedirectResponse("/home" if user else "/login", status_code=303)

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
        response = RedirectResponse(target, status_code=303)
        set_session(response, row["id"], settings.secret)
        return response

    @app.post("/logout")
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

    @app.post("/missions/{mission_id}/submissions", response_class=HTMLResponse)
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

        return RedirectResponse(f"/submissions/{submission['id']}", status_code=303)

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
        return page(
            request,
            "submission.html",
            {
                "active": "missions",
                "submission": submission,
                "evidences": repo.submission_evidences(conn, submission_id),
                "event": event,
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
        user: CurrentUser = Depends(require_staff),
        conn: sqlite3.Connection = Depends(conn_dep),
    ):
        if status not in {"submitted", "approved", "rejected"}:
            status = "submitted"
        return page(
            request,
            "admin_queue.html",
            {
                "active": "queue",
                "status": status,
                "rows": repo.list_queue(conn, user.organization_id, status),
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

    @app.post("/admin/submissions/{submission_id}/review", response_class=HTMLResponse)
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
        return RedirectResponse(f"/admin/submissions?status=submitted{suffix}", status_code=303)

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

    @app.post("/admin/missions/new", response_class=HTMLResponse)
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
        return RedirectResponse("/admin/missions?created=1", status_code=303)

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

    @app.post("/admin/missions/{mission_id}", response_class=HTMLResponse)
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
        return RedirectResponse(f"/admin/missions/{mission_id}{suffix}", status_code=303)

    @app.post("/admin/missions/{mission_id}/publish")
    def admin_mission_publish(
        mission_id: str,
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
        return RedirectResponse(f"/admin/missions/{mission_id}?published=1", status_code=303)

    @app.post("/admin/missions/{mission_id}/archive")
    def admin_mission_archive(
        mission_id: str,
        user: CurrentUser = Depends(require_admin),
        conn: sqlite3.Connection = Depends(conn_dep),
    ) -> RedirectResponse:
        mission = repo.mission_by_id(conn, mission_id, user.organization_id)
        if mission is None:
            raise HTTPException(status_code=404, detail="مأموریت یافت نشد.")
        repo.archive_mission(conn, mission, user)
        return RedirectResponse(f"/admin/missions/{mission_id}?archived=1", status_code=303)

    return app

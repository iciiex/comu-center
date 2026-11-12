# Graph Report - kiloos-club  (2026-11-12)

## Corpus Check
- 76 files · ~64,125 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1090 nodes · 3226 edges · 63 communities (59 shown, 4 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 401 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- repo.py
- award_mission_approval
- test_sales.py
- game.py
- D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE
- MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18
- test_game_api.py
- score_events
- base.html
- OD-01 — روش ورود
- test_demo_stability.py
- Implementation status (engineering judgement, 2026-11-11)
- main.py
- create_app
- AGENTS.md — اپراتور مهندسی Kiloos Club
- test_hardening.py
- Settings
- login
- روزشمار
- current_user
- CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club
- test_docs.py
- سناریوی دمو — MS-01
- نقش ۰۳ — Backend
- A — پیش از MS-01 (به ترتیب اولویت)
- پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها
- db.py
- format_jalali
- نقش ۰۱ — Product / Business Analyst
- نقش ۰۲ — Solution Architect
- نقش ۰۵ — QA
- conftest.py
- پلی‌بوک — موتور امتیاز و قوانین
- نقش ۰۴ — Frontend / Mobile
- نقش ۰۶ — DevOps
- MVP-01 — احراز هویت
- maintenance.py
- Runbook (prototype)
- پلی‌بوک — ورود داده فروش (Sales Import)
- ۱۲. بلوک handoff همین نشست
- نقش ۰۷ — Integrator / Lead
- .from_env
- Current Project State
- 3. Recipes
- 03 — Deliver
- Knowledge Graph
- Database ERD & Schema (prototype)
- Agent Guide
- Solution Architecture (prototype)
- Admin Panel Specification (prototype)
- UX/UI Specification (prototype)
- QA & Test Strategy (prototype)
- Changelog
- 01 — Start
- Execution Plan (working)
- Product Strategy & Scope (پروژه Kiloos Club)
- مستندات پروژه Kiloos Club
- Kiloos Club — Prototype
- _audit
- 02 — Continue
- scoring-rule-matrix.md

## God Nodes (most connected - your core abstractions)
1. `Settings` - 99 edges
2. `create_app()` - 85 edges
3. `login()` - 66 edges
4. `score_events` - 47 edges
5. `post()` - 46 edges
6. `users` - 42 edges
7. `missions` - 35 edges
8. `submissions` - 35 edges
9. `row_id()` - 31 edges
10. `test_demo_script_main_path_and_optional_correction()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `2.6 A test` --references--> `Settings`  [INFERRED]
  docs/agent-guide/02-continue.md → app/config.py
- `CSRF` --references--> `csrf_guard()`  [INFERRED]
  docs/engineering/api-spec.md → app/main.py
- `R2 — Add an action` --references--> `DomainError`  [INFERRED]
  docs/agent-guide/02-continue.md → app/repo.py
- `روز ۱ — ۱۸ آبان: اسکلت و قرارداد` --references--> `submission_evidences()`  [INFERRED]
  .agent/playbooks/prototype-9-days.md → app/repo.py
- `Tables` --references--> `submission_evidences()`  [INFERRED]
  docs/architecture/database-erd.md → app/repo.py

## Import Cycles
- None detected.

## Communities (63 total, 4 thin omitted)

### Community 0 - "repo.py"
Cohesion: 0.07
Nodes (61): admin_decide(), admin_mission_archive(), admin_mission_publish(), admin_mission_update(), admin_missions(), admin_review(), admin_sale_detail(), admin_sales_upload() (+53 more)

### Community 1 - "award_mission_approval"
Cohesion: 0.06
Nodes (41): پلی‌بوک — برش عمودی (Vertical Slice), ۱. برش را تعریف کن, ۲. قرارداد اول (Contract-first), ۳. ترتیب ساخت, ۴. معیار «تمام» برش, ۵. ضدالگوها, ۶. الگوی پیام commit / PR, award_mission_approval() (+33 more)

### Community 2 - "test_sales.py"
Cohesion: 0.10
Nodes (33): _decimal(), _duplicate(), _invalid(), money_points(), parse_workbook(), _raw(), _row_status(), _sale_date() (+25 more)

### Community 3 - "game.py"
Cohesion: 0.15
Nodes (36): bootstrap(), catalog(), _clean_answers(), _collect_flags(), complete_mission(), _daily_mission(), _date_diff(), _day_key() (+28 more)

### Community 4 - "D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE"
Cohesion: 0.13
Nodes (41): ۱۴. تصمیم‌های باز (خلاصه — جزئیات در `context/open-decisions.seed.json`), تصمیم‌های پیش‌فرض قابل بازگشت (ASSUMPTION), 4. Commit and pull request, 3. Queries, D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه), D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه), D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE, OD-02 — ساختار سازمانی (+33 more)

### Community 5 - "MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18"
Cohesion: 0.10
Nodes (35): ۱۰. تحویل و فازها, MASTER_PROMPT — پرامپت آماده برای شروع هر ایجنت, نسخه انگلیسی (برای ابزارهای انگلیسی‌زبان), نسخه فارسی (کپی کن), چطور این را به ابزارهای مختلف بدهیم, 2026-11-09 — Kiloos Club prototype — [PR #4](https://github.com/iciiex/comu-center/pull/4), 5. Invariants you must not break, ADR-0001: FastAPI + SQLite for the prototype (+27 more)

### Community 6 - "test_game_api.py"
Cohesion: 0.10
Nodes (34): game_complete_mission(), game_demo_users(), game_history(), game_progress(), Sales Quest Arena BFF (prototype, separate game economy), Agreement for this integration, API contract (same-origin BFF), Completion request / response sketch (+26 more)

### Community 7 - "score_events"
Cohesion: 0.14
Nodes (27): sales_page_context(), purge_evidence(), count_queue(), list_queue(), score_event_detail(), seed_demo(), audit_logs, competitions (+19 more)

### Community 8 - "base.html"
Cohesion: 0.11
Nodes (22): admin_queue(), admin_sales(), admin_sales_new(), missions_page(), score_page(), score_history(), EP-09 — Admin Panel, MVP-11 — پنل مدیریت (+14 more)

### Community 9 - "OD-01 — روش ورود"
Cohesion: 0.07
Nodes (31): Before any real user, Deployment Architecture, Today, D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو), OD-01 — روش ورود, Admin (admin only), API Specification (implemented surface), CSRF (+23 more)

### Community 10 - "test_demo_stability.py"
Cohesion: 0.18
Nodes (24): admin_sales_sample(), sample_workbook_bytes(), point_wallets, جزئیات A2 — اصلاح امتیاز (DONE 2026-11-12), Tests and verification, GET /admin/sales/sample, GET /submissions/{submission_id}, POST /admin/missions/{mission_id} (+16 more)

### Community 11 - "Implementation status (engineering judgement, 2026-11-11)"
Cohesion: 0.15
Nodes (29): داخل محدوده, ۵. قوانین کسب‌وکار (BR) — خلاصه اجرایی, مأموریت و submission, leaderboard_page(), active_competition(), leaderboard(), 2026-11-11 — Documentation, agent guide and knowledge graph — [PR #8](https://github.com/iciiex/comu-center/pull/8), Known gaps (+21 more)

### Community 12 - "main.py"
Cohesion: 0.12
Nodes (8): game_bootstrap(), csrf_for(), csrf_token(), make_token(), read_token(), session_token(), _sign(), _unsign()

### Community 13 - "create_app"
Cohesion: 0.13
Nodes (24): create_app(), admin_mission_create(), admin_mission_edit(), admin_mission_new(), admin_reverse_score(), admin_sales_process(), render_error(), game_demo_login() (+16 more)

### Community 14 - "AGENTS.md — اپراتور مهندسی Kiloos Club"
Cohesion: 0.08
Nodes (25): AGENTS.md — اپراتور مهندسی Kiloos Club, B — Build, D — Decide, H — Handoff, L — Locate, P — Prove, R — Read, S — Slice (+17 more)

### Community 15 - "test_hardening.py"
Cohesion: 0.14
Nodes (18): health(), GET /health, GET /home, POST /demo-login, POST /missions/{mission_id}/submissions, test_admin_queue_carries_token_between_pages(), test_admin_queue_paginates(), test_cookie_session_still_works() (+10 more)

### Community 16 - "Settings"
Cohesion: 0.30
Nodes (15): Settings, BR-005 — همه تغییرات امتیاز رویداد مستقل و append-only هستند؛ حذف/بازنویسی ممنوع، اصلاح با رویداد اصلاحی, POST /admin/score-events/{event_id}/reverse, post(), awarded_submission(), test_a_correction_cannot_be_reversed(), test_leaderboard_reflects_the_correction(), test_missing_event_returns_404() (+7 more)

### Community 18 - "login"
Cohesion: 0.34
Nodes (14): BR-003 — امتیاز فقط پس از تحقق شرایط معتبر؛ برای مأموریت نیازمند بررسی، پس از تأیید, MVP-06 — تأیید/رد فعالیت, login(), row_id(), submit(), test_approve_redirect_keeps_queue_filter(), test_duplicate_request_id_is_idempotent(), test_full_flow_approval_scores_once() (+6 more)

### Community 19 - "روزشمار"
Cohesion: 0.12
Nodes (16): fallbackها (اگر عقب افتادی), اصل حاکم, روز ۰ — ۲۷ آبان: تحویل, روز ۱ — ۱۸ آبان: اسکلت و قرارداد, روز ۲ — ۱۹ آبان: ورود + پوسته اپ, روز ۳ — ۲۰ آبان: مأموریت‌ها (خواندن), روز ۴ — ۲۱ آبان: ثبت submission + شواهد, روز ۵ — ۲۲ آبان: پنل — صف بررسی (+8 more)

### Community 20 - "current_user"
Cohesion: 0.18
Nodes (14): conn_dep(), require_admin(), require_api_user(), require_staff(), require_user(), LoginRequired, current_user(), CurrentUser (+6 more)

### Community 21 - "CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club"
Cohesion: 0.13
Nodes (15): CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club, MoSCoW, خارج از محدوده (در MVP نه), ۱. محصول در یک نگاه, ۱۱. KPI (همه پیشنهادی — نه تعهد), ۱۲. NFR, ۱۳. گزینه‌های فناوری (تأییدنشده — `OPEN`), ۱۵. واژه‌نامه (+7 more)

### Community 22 - "test_docs.py"
Cohesion: 0.16
Nodes (9): 1. Setup and tooling, 2. Checks that fail, 4. Changing application code, 5. Sales import, 6. When the documents disagree with the code, Troubleshooting, load_tool(), test_code_map_lists_exactly_the_routes_the_app_serves() (+1 more)

### Community 23 - "سناریوی دمو — MS-01"
Cohesion: 0.13
Nodes (15): سناریوی دمو — MS-01, پرده ۱ — ویزیتور مأموریت را انجام می‌دهد (سارا), پرده ۲ — اپراتور بررسی می‌کند (حسین), پرده ۳ — امتیاز قابل توضیح (سارا), پرده ۴ — مدیر امتیاز مأموریت را عوض می‌کند (نگار), پرده ۵ — ورود داده فروش (نگار), پرده ۶ — نتیجه برای ویزیتور (سارا), ۱. آماده‌سازی صبح روز دمو (+7 more)

### Community 24 - "نقش ۰۳ — Backend"
Cohesion: 0.14
Nodes (13): Definition of Done نقش, اشتباهات رایج, امتیاز, امنیت و دسترسی, داده فروش, قبل از شروع بخوان, قرارداد خروجی هر برش, قواعد سخت دامنه (+5 more)

### Community 25 - "A — پیش از MS-01 (به ترتیب اولویت)"
Cohesion: 0.14
Nodes (14): A — پیش از MS-01 (به ترتیب اولویت), Backlog و نقشه ادامه توسعه, D — Harden (فقط پس از ثبت P→H؛ تا RC), جزئیات A10 — اسکن secret در CI, جزئیات A3 — وقت تهران, جزئیات A4 — سناریو و دوره نمونه, جزئیات A5 — شفافیت امتیاز, جزئیات A6 — ریزه‌کاری‌ها (۴ مورد DONE 2026-11-12؛ مورد ۵ باز) (+6 more)

### Community 26 - "پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها"
Cohesion: 0.15
Nodes (12): UI, داده, دسترسی و امنیت, صحت دامنه, قاعده ۳۰ ثانیه, پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها, کیفیت, ۱. چک‌لیست بازبینی PR (ترتیب اهمیت) (+4 more)

### Community 27 - "db.py"
Cohesion: 0.21
Nodes (6): apply_migrations(), connect(), init_db(), Migrations, R3 — Change the schema, Migrations

### Community 28 - "format_jalali"
Cohesion: 0.27
Nodes (6): format_jalali(), gregorian_to_jalali(), to_persian_digits(), test_digits(), test_formatting_uses_persian_digits(), test_known_dates()

### Community 29 - "نقش ۰۱ — Product / Business Analyst"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۱ — Product / Business Analyst (+3 more)

### Community 30 - "نقش ۰۲ — Solution Architect"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۲ — Solution Architect (+3 more)

### Community 31 - "نقش ۰۵ — QA"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, اولویت تست بر اساس ریسک, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل (+3 more)

### Community 32 - "conftest.py"
Cohesion: 0.29
Nodes (5): 3. Writing tests, client(), csrf(), db(), settings()

### Community 33 - "پلی‌بوک — موتور امتیاز و قوانین"
Cohesion: 0.18
Nodes (10): پلی‌بوک — موتور امتیاز و قوانین, ۱. مدل ذهنی, ۲. قرارداد داده پیشنهادی, ۳. الگوریتم (اجباری), ۴. انواع محاسبه, ۵. idempotency — سه لایه, ۶. اصلاح، برگشت، محاسبه مجدد, ۷. تست طلایی (Golden Tests) (+2 more)

### Community 34 - "نقش ۰۴ — Frontend / Mobile"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, قبل از شروع بخوان, قرارداد خروجی هر صفحه, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۴ — Frontend / Mobile (+2 more)

### Community 35 - "نقش ۰۶ — DevOps"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, حداقل‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۶ — DevOps (+2 more)

### Community 36 - "MVP-01 — احراز هویت"
Cohesion: 0.20
Nodes (9): csrf_guard(), demo_login(), game_logout(), logout(), url(), with_token(), clear_session(), set_session() (+1 more)

### Community 37 - "maintenance.py"
Cohesion: 0.25
Nodes (3): main(), build_sample_workbook(), main()

### Community 38 - "Runbook (prototype)"
Cohesion: 0.18
Nodes (11): Backup (prototype), Common issues, Configuration (environment), Escalation, Evidence retention (manual, D-003), Health, Repository health and generated documents, Reset demo data (+3 more)

### Community 39 - "پلی‌بوک — ورود داده فروش (Sales Import)"
Cohesion: 0.20
Nodes (9): پلی‌بوک — ورود داده فروش (Sales Import), ۱. چرخه عمر Import, ۲. قرارداد ورودی (اولیه — `OPEN` تا دریافت فایل واقعی), ۳. اعتبارسنجی در دو سطح, ۴. ضدتکرار, ۵. پردازش, ۶. Reconciliation, ۷. چک‌لیست برش (+1 more)

### Community 40 - "۱۲. بلوک handoff همین نشست"
Cohesion: 0.20
Nodes (10): Changes made, Context read, Contract changes, Decisions and assumptions, Files changed, Recommended next step, Remaining work, Risks / blockers (+2 more)

### Community 41 - "نقش ۰۷ — Integrator / Lead"
Cohesion: 0.22
Nodes (8): Definition of Done نقش, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۷ — Integrator / Lead, پرامپت نقش (کپی), کارهای اصلی

### Community 42 - ".from_env"
Cohesion: 0.29
Nodes (3): _int_env(), main(), R5 — Add a setting

### Community 43 - "Current Project State"
Cohesion: 0.25
Nodes (8): Current Project State, Decisions approved, Demo status, Important files and entry points, Known issues, Open decisions / assumptions, Recent migrations / API changes, Working features

### Community 44 - "3. Recipes"
Cohesion: 0.29
Nodes (7): 3. Recipes, R1 — Add a page, R2 — Add an action, R4 — Change scoring behaviour, R6 — Record a decision or an open question, R7 — Fix a defect from the backlog, R8 — Keep the map and the traceability current

### Community 45 - "03 — Deliver"
Cohesion: 0.29
Nodes (7): 03 — Deliver, 1. Gate: run these and read the output, 2. Check the behaviour yourself, 3. Update the documents, 5. Hand off, 6. Final self-check, Statuses you may write

### Community 46 - "Knowledge Graph"
Cohesion: 0.29
Nodes (7): 1. What is in `graphify-out/`, 2. How it is built, and what that means for trust, 4. Scripting against `graph.json`, 5. Graph or generated map?, 6. Keeping it current, 7. Limits, Knowledge Graph

### Community 47 - "Database ERD & Schema (prototype)"
Cohesion: 0.29
Nodes (6): Data rules, Database ERD & Schema (prototype), Relations (macro), Sales import tables (0003), Tables, Why these constraints

### Community 48 - "Agent Guide"
Cohesion: 0.33
Nodes (6): Agent Guide, Commands you will use, Find anything, Keeping this guide true, Lookup files, The three phases

### Community 49 - "Solution Architecture (prototype)"
Cohesion: 0.33
Nodes (5): Domain boundaries kept, Explicit non-decisions, Implemented shape, Next, Solution Architecture (prototype)

### Community 50 - "Admin Panel Specification (prototype)"
Cohesion: 0.33
Nodes (5): Access model, Admin Panel Specification (prototype), Implemented, Not implemented, Open

### Community 51 - "UX/UI Specification (prototype)"
Cohesion: 0.33
Nodes (5): Gaps, Implemented, Next, UX rules applied, UX/UI Specification (prototype)

### Community 52 - "QA & Test Strategy (prototype)"
Cohesion: 0.33
Nodes (5): Commands, Implemented automated coverage (71 tests on 2026-11-12), Not covered yet, QA & Test Strategy (prototype), Rule

### Community 53 - "Changelog"
Cohesion: 0.40
Nodes (5): 2026-11-09 — Demo hardening — [PR #5](https://github.com/iciiex/comu-center/pull/5), 2026-11-09 — Score corrections — [PR #6](https://github.com/iciiex/comu-center/pull/6), Before Kiloos Club, Changelog, [Unreleased]

### Community 54 - "01 — Start"
Cohesion: 0.40
Nodes (5): 01 — Start, 1. Read in this order, 2. Set up and verify, 3. Layout, 7. Where to go next

### Community 55 - "Execution Plan (working)"
Cohesion: 0.40
Nodes (4): Cut from the 9-day plan, Execution Plan (working), Next, Prototype scope delivered

### Community 56 - "Product Strategy & Scope (پروژه Kiloos Club)"
Cohesion: 0.40
Nodes (4): Product Strategy & Scope (پروژه Kiloos Club), آخرین تطبیق, خلاصه قابل اتکا, قاعده

### Community 57 - "مستندات پروژه Kiloos Club"
Cohesion: 0.40
Nodes (4): شروع، ادامه و تحویل (راهنمای ایجنت), قواعد, مستندات پروژه Kiloos Club, منبع اصلی

### Community 58 - "Kiloos Club — Prototype"
Cohesion: 0.40
Nodes (4): Kiloos Club — Prototype, ایمنی داده, ساختار, مستندات

### Community 60 - "02 — Continue"
Cohesion: 0.50
Nodes (4): 02 — Continue, 1. The loop, with this repository's commands, 4. Which document to update for which change, 5. Boundaries

## Knowledge Gaps
- **5 isolated node(s):** `EP-13 — QA`, `GET /`, `DELETE /api/v1/game/missions/{mission_id}/draft`, `PUT /api/v1/game/missions/{mission_id}/draft`, `PATCH /api/v1/game/profile`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 384 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `create_app` to `repo.py`, `conftest.py`, `game.py`, `MVP-01 — احراز هویت`, `test_game_api.py`, `score_events`, `base.html`, `.from_env`, `test_demo_stability.py`, `main.py`, `Implementation status (engineering judgement, 2026-11-11)`, `test_hardening.py`, `Settings`, `current_user`, `test_docs.py`, `db.py`, `format_jalali`?**
  _High betweenness centrality (0.111) - this node is a cross-community bridge._
- **Are the 84 inferred relationships involving `Settings` (e.g. with `create_app()` and `main()`) actually correct?**
  _`Settings` has 84 INFERRED edges - model-reasoned connections that need verification._
- **What connects `EP-13 — QA`, `GET /`, `DELETE /api/v1/game/missions/{mission_id}/draft` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `repo.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07222222222222222 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `conftest.py`, `award_mission_approval`, `test_sales.py`, `D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE`, `maintenance.py`, `test_game_api.py`, `score_events`, `base.html`, `.from_env`, `test_demo_stability.py`, `main.py`, `create_app`, `test_hardening.py`, `login`, `current_user`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `create_app()` (e.g. with `Settings` and `to_persian_digits()`) actually correct?**
  _`create_app()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `award_mission_approval` be split into smaller, more focused modules?**
  _Cohesion score 0.06451612903225806 - nodes in this community are weakly interconnected._
# Graph Report - kiloos-club  (2026-11-12)

## Corpus Check
- 83 files · ~70,217 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1168 nodes · 3385 edges · 75 communities (70 shown, 5 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 406 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Settings
- Implementation status (engineering judgement, 2026-11-11)
- game.py
- conftest.py
- create_app
- award_mission_approval
- users
- OD-01 — روش ورود
- missions
- AGENTS.md — اپراتور مهندسی Kiloos Club
- OD-04 — فرمول امتیاز فروش
- main.py
- Connection
- repo.py
- D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE
- test_game_api.py
- sales.py
- D-001 — استفاده از FastAPI + SQLite برای Prototype
- MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18
- current_user
- سناریوی دمو — MS-01
- نقش ۰۳ — Backend
- db.py
- Tribal Gamification API Contract (proposal)
- پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها
- format_jalali
- base.html
- نقش ۰۱ — Product / Business Analyst
- نقش ۰۲ — Solution Architect
- نقش ۰۵ — QA
- config.py
- Runbook (prototype)
- روزشمار
- پلی‌بوک — موتور امتیاز و قوانین
- نقش ۰۴ — Frontend / Mobile
- نقش ۰۶ — DevOps
- admin_decide
- tribal.py
- 3. Queries
- پلی‌بوک — ورود داده فروش (Sales Import)
- BR-001 — نمایش مأموریت فقط با: وضعیت Active + داخل بازه زمانی + عضویت در جامعه هدف + عدم نقض محدودیت دسترسی
- test_docs.py
- ۱۲. بلوک handoff همین نشست
- نقش ۰۷ — Integrator / Lead
- .from_env
- Database ERD & Schema (prototype)
- Sales Quest Arena — Backend-for-Frontend Alignment
- seed_demo
- Tribal Gamification — Architecture and Two-Agent Plan
- پلی‌بوک — برش عمودی (Vertical Slice)
- admin_sales_upload
- review_submission
- 3. Recipes
- 03 — Deliver
- Knowledge Graph
- 3. Target architecture
- Scoring Engine (prototype)
- پلی‌بوک — ۹ روز تا Prototype (MS-01)
- game_progress
- Agent Guide
- Admin Panel Specification (prototype)
- UX/UI Specification (prototype)
- QA & Test Strategy (prototype)
- 01 — Start
- Troubleshooting
- Backlog و نقشه ادامه توسعه
- Product Strategy & Scope (پروژه Kiloos Club)
- Kiloos Club — Prototype
- 02 — Continue
- Technical Design (prototype)
- 1. Shared contract
- migrations/README.md
- scoring-rule-matrix.md

## God Nodes (most connected - your core abstractions)
1. `Settings` - 99 edges
2. `create_app()` - 93 edges
3. `login()` - 72 edges
4. `users` - 47 edges
5. `score_events` - 47 edges
6. `post()` - 46 edges
7. `missions` - 35 edges
8. `submissions` - 35 edges
9. `row_id()` - 31 edges
10. `test_demo_script_main_path_and_optional_correction()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `2.6 A test` --references--> `Settings`  [INFERRED]
  docs/agent-guide/02-continue.md → app/config.py
- `Migrations` --references--> `apply_migrations()`  [INFERRED]
  docs/architecture/database-erd.md → app/db.py
- `CSRF` --references--> `csrf_guard()`  [INFERRED]
  docs/engineering/api-spec.md → app/main.py
- `Persistence boundary` --references--> `game_progress()`  [INFERRED]
  docs/engineering/game-bff-alignment.md → app/main.py
- `R2 — Add an action` --references--> `DomainError`  [INFERRED]
  docs/agent-guide/02-continue.md → app/repo.py

## Import Cycles
- None detected.

## Communities (75 total, 5 thin omitted)

### Community 0 - "Settings"
Cohesion: 0.08
Nodes (90): ۶. الگوی پیام commit / PR, Settings, admin_queue(), admin_sales(), sample_workbook_bytes(), point_transactions, point_wallets, score_events (+82 more)

### Community 1 - "Implementation status (engineering judgement, 2026-11-11)"
Cohesion: 0.06
Nodes (61): CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club, MoSCoW, خارج از محدوده (در MVP نه), داخل محدوده, ۱. محصول در یک نگاه, ۱۰. تحویل و فازها, ۱۱. KPI (همه پیشنهادی — نه تعهد), ۱۲. NFR (+53 more)

### Community 2 - "game.py"
Cohesion: 0.15
Nodes (36): bootstrap(), catalog(), _clean_answers(), _collect_flags(), complete_mission(), _daily_mission(), _date_diff(), _day_key() (+28 more)

### Community 3 - "conftest.py"
Cohesion: 0.08
Nodes (28): tribal_bootstrap(), competitions, organizations, ix_org_memberships_unit_period, ix_org_memberships_user_period, ix_org_units_parent, ix_org_units_type, org_memberships (+20 more)

### Community 4 - "create_app"
Cohesion: 0.10
Nodes (36): create_app(), admin_mission_archive(), admin_mission_create(), admin_mission_edit(), admin_mission_new(), admin_mission_publish(), admin_mission_update(), admin_missions() (+28 more)

### Community 5 - "award_mission_approval"
Cohesion: 0.14
Nodes (23): _ensure_rule_version(), award_mission_approval(), award_sales_record(), _existing(), find_rule_version(), _now(), _persist_award(), reversal_of() (+15 more)

### Community 6 - "users"
Cohesion: 0.11
Nodes (26): demo_login(), game_logout(), health(), logout(), sales_page_context(), clear_session(), make_token(), set_session() (+18 more)

### Community 7 - "OD-01 — روش ورود"
Cohesion: 0.08
Nodes (30): Before any real user, Deployment Architecture, Today, D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو), OD-01 — روش ورود, OD-11 — یکپارچگی, Admin (admin only), API Specification (implemented surface) (+22 more)

### Community 8 - "missions"
Cohesion: 0.14
Nodes (23): home(), mission_page(), render_error(), purge_evidence(), count_queue(), count_user_submissions(), evidence(), get_mission_for_user() (+15 more)

### Community 9 - "AGENTS.md — اپراتور مهندسی Kiloos Club"
Cohesion: 0.08
Nodes (25): AGENTS.md — اپراتور مهندسی Kiloos Club, B — Build, D — Decide, H — Handoff, L — Locate, P — Prove, R — Read, S — Slice (+17 more)

### Community 10 - "OD-04 — فرمول امتیاز فروش"
Cohesion: 0.25
Nodes (24): ۱۴. تصمیم‌های باز (خلاصه — جزئیات در `context/open-decisions.seed.json`), تصمیم‌های پیش‌فرض قابل بازگشت (ASSUMPTION), D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه), D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه), OD-02 — ساختار سازمانی, OD-03 — نمونه فایل فروش, OD-04 — فرمول امتیاز فروش, OD-05 — SKUهای هدف (+16 more)

### Community 11 - "main.py"
Cohesion: 0.14
Nodes (9): csrf_guard(), game_bootstrap(), csrf_for(), csrf_token(), CurrentUser, read_token(), session_token(), _sign() (+1 more)

### Community 12 - "Connection"
Cohesion: 0.16
Nodes (17): admin_sale_detail(), create_sales_import(), list_missions_admin(), list_sales_imports(), reversal_for(), reverse_score_event(), sales_external_ids(), sales_import() (+9 more)

### Community 13 - "repo.py"
Cohesion: 0.21
Nodes (15): archive_mission(), audit(), create_mission(), create_submission(), DomainError, _new_id(), now_iso(), _parse_day() (+7 more)

### Community 14 - "D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE"
Cohesion: 0.11
Nodes (22): 2026-11-09 — Sales import — [PR #7](https://github.com/iciiex/comu-center/pull/7), ix_sales_records_import, ux_sales_records_external, 4. Commit and pull request, D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE, Delivered after the prototype window, Authorization rules, Contract (SAMPLE) (+14 more)

### Community 15 - "test_game_api.py"
Cohesion: 0.21
Nodes (21): game_complete_mission(), game_demo_users(), game_history(), GET /api/v1/game/bootstrap, GET /api/v1/game/demo-users, GET /api/v1/game/history, POST /api/v1/game/demo-login, POST /api/v1/game/missions/{mission_id}/completions (+13 more)

### Community 16 - "sales.py"
Cohesion: 0.17
Nodes (11): _decimal(), _duplicate(), _invalid(), money_points(), parse_workbook(), _raw(), _row_status(), _sale_date() (+3 more)

### Community 17 - "D-001 — استفاده از FastAPI + SQLite برای Prototype"
Cohesion: 0.14
Nodes (21): 5. Invariants you must not break, ADR-0001: FastAPI + SQLite for the prototype, Consequences, Decision, Follow-up, D-001 — استفاده از FastAPI + SQLite برای Prototype, Decision Log, تصمیم‌های ثبت‌شده (+13 more)

### Community 18 - "MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18"
Cohesion: 0.15
Nodes (17): MASTER_PROMPT — پرامپت آماده برای شروع هر ایجنت, نسخه انگلیسی (برای ابزارهای انگلیسی‌زبان), نسخه فارسی (کپی کن), چطور این را به ابزارهای مختلف بدهیم, Context, Options, راهنما, Cut from the 9-day plan (+9 more)

### Community 20 - "current_user"
Cohesion: 0.19
Nodes (13): conn_dep(), require_admin(), require_api_user(), require_staff(), require_user(), LoginRequired, current_user(), 4. How a request flows (+5 more)

### Community 21 - "سناریوی دمو — MS-01"
Cohesion: 0.12
Nodes (15): سناریوی دمو — MS-01, پرده ۱ — ویزیتور مأموریت را انجام می‌دهد (سارا), پرده ۲ — اپراتور بررسی می‌کند (حسین), پرده ۳ — امتیاز قابل توضیح (سارا), پرده ۴ — مدیر امتیاز مأموریت را عوض می‌کند (نگار), پرده ۵ — ورود داده فروش (نگار), پرده ۶ — نتیجه برای ویزیتور (سارا), ۱. آماده‌سازی صبح روز دمو (+7 more)

### Community 22 - "نقش ۰۳ — Backend"
Cohesion: 0.13
Nodes (14): Definition of Done نقش, اشتباهات رایج, امتیاز, امنیت و دسترسی, داده فروش, قبل از شروع بخوان, قرارداد خروجی هر برش, قواعد سخت دامنه (+6 more)

### Community 23 - "db.py"
Cohesion: 0.20
Nodes (6): apply_migrations(), connect(), init_db(), now_iso(), _audit(), R3 — Change the schema

### Community 24 - "Tribal Gamification API Contract (proposal)"
Cohesion: 0.14
Nodes (14): 10. Contract review gates (before implementation), 2. Player and organization reads, 3. Campaigns and mission runs, 4. Review workload, 5. League and ranking reads, 6. Badges and achievements, 7. Admin/back-office APIs, 8. Proposed DTO outlines (+6 more)

### Community 25 - "پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها"
Cohesion: 0.15
Nodes (12): UI, داده, دسترسی و امنیت, صحت دامنه, قاعده ۳۰ ثانیه, پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها, کیفیت, ۱. چک‌لیست بازبینی PR (ترتیب اهمیت) (+4 more)

### Community 26 - "format_jalali"
Cohesion: 0.27
Nodes (6): format_jalali(), gregorian_to_jalali(), to_persian_digits(), test_digits(), test_formatting_uses_persian_digits(), test_known_dates()

### Community 27 - "base.html"
Cohesion: 0.24
Nodes (7): missions_page(), submit_mission(), GET /missions, GET /missions/{mission_id}, GET /score, POST /missions/{mission_id}/submissions, test_forms_render_a_csrf_field()

### Community 28 - "نقش ۰۱ — Product / Business Analyst"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۱ — Product / Business Analyst (+3 more)

### Community 29 - "نقش ۰۲ — Solution Architect"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۲ — Solution Architect (+3 more)

### Community 30 - "نقش ۰۵ — QA"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, اولویت تست بر اساس ریسک, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل (+3 more)

### Community 32 - "Runbook (prototype)"
Cohesion: 0.17
Nodes (11): Backup (prototype), Common issues, Configuration (environment), Escalation, Evidence retention (manual, D-003), Health, Repository health and generated documents, Reset demo data (+3 more)

### Community 33 - "روزشمار"
Cohesion: 0.18
Nodes (11): روز ۰ — ۲۷ آبان: تحویل, روز ۱ — ۱۸ آبان: اسکلت و قرارداد, روز ۲ — ۱۹ آبان: ورود + پوسته اپ, روز ۳ — ۲۰ آبان: مأموریت‌ها (خواندن), روز ۴ — ۲۱ آبان: ثبت submission + شواهد, روز ۵ — ۲۲ آبان: پنل — صف بررسی, روز ۶ — ۲۳ آبان: موتور امتیاز, روز ۷ — ۲۴ آبان: کیف امتیاز + تاریخچه (+3 more)

### Community 34 - "پلی‌بوک — موتور امتیاز و قوانین"
Cohesion: 0.18
Nodes (10): پلی‌بوک — موتور امتیاز و قوانین, ۱. مدل ذهنی, ۲. قرارداد داده پیشنهادی, ۳. الگوریتم (اجباری), ۴. انواع محاسبه, ۵. idempotency — سه لایه, ۶. اصلاح، برگشت، محاسبه مجدد, ۷. تست طلایی (Golden Tests) (+2 more)

### Community 35 - "نقش ۰۴ — Frontend / Mobile"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, قبل از شروع بخوان, قرارداد خروجی هر صفحه, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۴ — Frontend / Mobile (+2 more)

### Community 36 - "نقش ۰۶ — DevOps"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, حداقل‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۶ — DevOps (+2 more)

### Community 37 - "admin_decide"
Cohesion: 0.27
Nodes (7): admin_decide(), admin_review(), evidence_file(), submission_page(), score_event_for_source(), submission_evidences(), GET /evidence/{evidence_id}

### Community 38 - "tribal.py"
Cohesion: 0.27
Nodes (4): _decode_cursor(), _encode_cursor(), get_unit(), list_units()

### Community 39 - "3. Queries"
Cohesion: 0.18
Nodes (8): 3. Queries, Architecture Decision Records, Template, Domain boundaries kept, Explicit non-decisions, Implemented shape, Next, Solution Architecture (prototype)

### Community 40 - "پلی‌بوک — ورود داده فروش (Sales Import)"
Cohesion: 0.20
Nodes (9): پلی‌بوک — ورود داده فروش (Sales Import), ۱. چرخه عمر Import, ۲. قرارداد ورودی (اولیه — `OPEN` تا دریافت فایل واقعی), ۳. اعتبارسنجی در دو سطح, ۴. ضدتکرار, ۵. پردازش, ۶. Reconciliation, ۷. چک‌لیست برش (+1 more)

### Community 41 - "BR-001 — نمایش مأموریت فقط با: وضعیت Active + داخل بازه زمانی + عضویت در جامعه هدف + عدم نقض محدودیت دسترسی"
Cohesion: 0.22
Nodes (10): 2026-11-09 — Demo hardening — [PR #5](https://github.com/iciiex/comu-center/pull/5), 2026-11-09 — Kiloos Club prototype — [PR #4](https://github.com/iciiex/comu-center/pull/4), 2026-11-09 — Score corrections — [PR #6](https://github.com/iciiex/comu-center/pull/6), 2026-11-11 — Documentation, agent guide and knowledge graph — [PR #8](https://github.com/iciiex/comu-center/pull/8), Before Kiloos Club, Changelog, [Unreleased], POST /missions/{id}/submissions (+2 more)

### Community 42 - "test_docs.py"
Cohesion: 0.27
Nodes (4): 2. Checks that fail, load_tool(), test_code_map_lists_exactly_the_routes_the_app_serves(), test_generated_agent_docs_are_fresh()

### Community 43 - "۱۲. بلوک handoff همین نشست"
Cohesion: 0.20
Nodes (10): Changes made, Context read, Contract changes, Decisions and assumptions, Files changed, Recommended next step, Remaining work, Risks / blockers (+2 more)

### Community 44 - "نقش ۰۷ — Integrator / Lead"
Cohesion: 0.22
Nodes (8): Definition of Done نقش, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۷ — Integrator / Lead, پرامپت نقش (کپی), کارهای اصلی

### Community 45 - ".from_env"
Cohesion: 0.28
Nodes (4): _int_env(), main(), main(), R5 — Add a setting

### Community 46 - "Database ERD & Schema (prototype)"
Cohesion: 0.22
Nodes (6): Data rules, Database ERD & Schema (prototype), Migrations, Relations (macro), Sales import tables (0003), Why these constraints

### Community 47 - "Sales Quest Arena — Backend-for-Frontend Alignment"
Cohesion: 0.22
Nodes (9): Agreement for this integration, API contract (same-origin BFF), Completion request / response sketch, Delivery sequence / acceptance, Frontend facts and compatibility gap, Not decided / not included, Persistence boundary, Sales Quest Arena — Backend-for-Frontend Alignment (+1 more)

### Community 48 - "seed_demo"
Cohesion: 0.36
Nodes (3): _id(), _iso(), seed_demo()

### Community 49 - "Tribal Gamification — Architecture and Two-Agent Plan"
Cohesion: 0.25
Nodes (8): 2. Current architecture and impact, 4. Conceptual ERD (proposal), 5. Frontend information architecture, 6. Two-agent implementation plan, 8. Still requires owner/product input before implementation, Backend (current prototype), Frontend (current public main), Tribal Gamification — Architecture and Two-Agent Plan

### Community 50 - "پلی‌بوک — برش عمودی (Vertical Slice)"
Cohesion: 0.29
Nodes (6): پلی‌بوک — برش عمودی (Vertical Slice), ۱. برش را تعریف کن, ۲. قرارداد اول (Contract-first), ۳. ترتیب ساخت, ۴. معیار «تمام» برش, ۵. ضدالگوها

### Community 51 - "admin_sales_upload"
Cohesion: 0.33
Nodes (6): admin_sales_new(), admin_sales_sample(), admin_sales_upload(), render_error(), GET /admin/sales/sample, POST /admin/sales

### Community 52 - "review_submission"
Cohesion: 0.38
Nodes (4): review_submission(), ScoringError, جزئیات A1 — تأییدِ بدون امتیاز (DONE 2026-11-12), Data written on approval (one transaction)

### Community 53 - "3. Recipes"
Cohesion: 0.29
Nodes (7): 3. Recipes, R1 — Add a page, R2 — Add an action, R4 — Change scoring behaviour, R6 — Record a decision or an open question, R7 — Fix a defect from the backlog, R8 — Keep the map and the traceability current

### Community 54 - "03 — Deliver"
Cohesion: 0.29
Nodes (7): 03 — Deliver, 1. Gate: run these and read the output, 2. Check the behaviour yourself, 3. Update the documents, 5. Hand off, 6. Final self-check, Statuses you may write

### Community 55 - "Knowledge Graph"
Cohesion: 0.29
Nodes (7): 1. What is in `graphify-out/`, 2. How it is built, and what that means for trust, 4. Scripting against `graph.json`, 5. Graph or generated map?, 6. Keeping it current, 7. Limits, Knowledge Graph

### Community 56 - "3. Target architecture"
Cohesion: 0.29
Nodes (7): 3.1 Configurable organization tree, 3.2 RBAC and data visibility, 3.3 Admin Excel ingestion and reference data, 3.4 Campaigns, missions and review, 3.5 Scoring, ranking and league, 3.6 Badges, flags, audit and feature flag, 3. Target architecture

### Community 57 - "Scoring Engine (prototype)"
Cohesion: 0.29
Nodes (6): Explainability, Not implemented (explicit), Rule selection, Sales records — SAMPLE per-amount rule, Scoring Engine (prototype), Test coverage (executed)

### Community 58 - "پلی‌بوک — ۹ روز تا Prototype (MS-01)"
Cohesion: 0.33
Nodes (5): fallbackها (اگر عقب افتادی), اصل حاکم, سناریوی دمو (۷ دقیقه), پلی‌بوک — ۹ روز تا Prototype (MS-01), چک‌لیست «قابل نمایش»

### Community 59 - "game_progress"
Cohesion: 0.33
Nodes (6): game_progress(), Tables, 1. Product direction recorded, 7. Safety, scale and DoD, Sales Quest Arena BFF (prototype, separate game economy), GET /api/v1/game/progress

### Community 60 - "Agent Guide"
Cohesion: 0.33
Nodes (6): Agent Guide, Commands you will use, Find anything, Keeping this guide true, Lookup files, The three phases

### Community 61 - "Admin Panel Specification (prototype)"
Cohesion: 0.33
Nodes (5): Access model, Admin Panel Specification (prototype), Implemented, Not implemented, Open

### Community 62 - "UX/UI Specification (prototype)"
Cohesion: 0.33
Nodes (5): Gaps, Implemented, Next, UX rules applied, UX/UI Specification (prototype)

### Community 63 - "QA & Test Strategy (prototype)"
Cohesion: 0.33
Nodes (5): Commands, Implemented automated coverage (71 tests on 2026-11-12), Not covered yet, QA & Test Strategy (prototype), Rule

### Community 64 - "01 — Start"
Cohesion: 0.40
Nodes (5): 01 — Start, 1. Read in this order, 2. Set up and verify, 3. Layout, 7. Where to go next

### Community 65 - "Troubleshooting"
Cohesion: 0.40
Nodes (5): 1. Setup and tooling, 4. Changing application code, 5. Sales import, 6. When the documents disagree with the code, Troubleshooting

### Community 66 - "Backlog و نقشه ادامه توسعه"
Cohesion: 0.40
Nodes (5): Backlog و نقشه ادامه توسعه, D — Harden (فقط پس از ثبت P→H؛ تا RC), شواهد اجرا (2026-11-11), شواهد اجرا (2026-11-12 — برش پایداری دمو), قاعده نگهداری این فایل

### Community 67 - "Product Strategy & Scope (پروژه Kiloos Club)"
Cohesion: 0.40
Nodes (4): Product Strategy & Scope (پروژه Kiloos Club), آخرین تطبیق, خلاصه قابل اتکا, قاعده

### Community 68 - "Kiloos Club — Prototype"
Cohesion: 0.40
Nodes (4): Kiloos Club — Prototype, ایمنی داده, ساختار, مستندات

### Community 69 - "02 — Continue"
Cohesion: 0.50
Nodes (4): 02 — Continue, 1. The loop, with this repository's commands, 4. Which document to update for which change, 5. Boundaries

### Community 70 - "Technical Design (prototype)"
Cohesion: 0.50
Nodes (3): Design rules in code, Gaps, Technical Design (prototype)

### Community 71 - "1. Shared contract"
Cohesion: 0.50
Nodes (4): 1. Shared contract, Authentication and security, Common resource conventions, Common response/error format

## Knowledge Gaps
- **5 isolated node(s):** `EP-13 — QA`, `GET /`, `DELETE /api/v1/game/missions/{mission_id}/draft`, `PUT /api/v1/game/missions/{mission_id}/draft`, `PATCH /api/v1/game/profile`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 414 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `create_app` to `Settings`, `Implementation status (engineering judgement, 2026-11-11)`, `game.py`, `conftest.py`, `users`, `missions`, `main.py`, `Connection`, `repo.py`, `test_game_api.py`, `current_user`, `db.py`, `format_jalali`, `base.html`, `admin_decide`, `tribal.py`, `test_docs.py`, `.from_env`, `admin_sales_upload`, `game_progress`?**
  _High betweenness centrality (0.167) - this node is a cross-community bridge._
- **Are the 84 inferred relationships involving `Settings` (e.g. with `create_app()` and `main()`) actually correct?**
  _`Settings` has 84 INFERRED edges - model-reasoned connections that need verification._
- **What connects `EP-13 — QA`, `GET /`, `DELETE /api/v1/game/missions/{mission_id}/draft` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Settings` be split into smaller, more focused modules?**
  _Cohesion score 0.07819398946019085 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `conftest.py`, `create_app`, `award_mission_approval`, `users`, `3. Queries`, `missions`, `main.py`, `.from_env`, `test_game_api.py`, `seed_demo`, `current_user`, `base.html`, `config.py`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `create_app()` (e.g. with `Settings` and `to_persian_digits()`) actually correct?**
  _`create_app()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `Implementation status (engineering judgement, 2026-11-11)` be split into smaller, more focused modules?**
  _Cohesion score 0.05888376856118792 - nodes in this community are weakly interconnected._
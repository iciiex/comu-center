# Graph Report - kiloos-club  (2026-11-12)

## Corpus Check
- 76 files · ~63,614 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1082 nodes · 3199 edges · 67 communities (59 shown, 8 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 400 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Settings
- repo.py
- game.py
- main.py
- OD-01 — روش ورود
- test_game_api.py
- MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18
- AGENTS.md — اپراتور مهندسی Kiloos Club
- create_app
- OD-04 — فرمول امتیاز فروش
- sales.py
- D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE
- current_user
- Implementation status (engineering judgement, 2026-11-11)
- D-001 — استفاده از FastAPI + SQLite برای Prototype
- BR-001 — نمایش مأموریت فقط با: وضعیت Active + داخل بازه زمانی + عضویت در جامعه هدف + عدم نقض محدودیت دسترسی
- MVP-04 — مدیریت مأموریت (تعریف/انتشار)
- base.html
- 3. Queries
- pathlib
- CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club
- نقش ۰۳ — Backend
- پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها
- maintenance.py
- format_jalali
- D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه)
- ۱۰. تحویل و فازها
- نقش ۰۱ — Product / Business Analyst
- نقش ۰۲ — Solution Architect
- نقش ۰۵ — QA
- پلی‌بوک — موتور امتیاز و قوانین
- نقش ۰۴ — Frontend / Mobile
- نقش ۰۶ — DevOps
- db.py
- seed_demo
- پلی‌بوک — ورود داده فروش (Sales Import)
- ۱۲. بلوک handoff همین نشست
- نقش ۰۷ — Integrator / Lead
- A — پیش از MS-01 (به ترتیب اولویت)
- سناریوی دمو — MS-01
- پلی‌بوک — برش عمودی (Vertical Slice)
- config.py
- 3. Recipes
- 03 — Deliver
- Knowledge Graph
- Database ERD & Schema (prototype)
- Scoring Engine (prototype)
- MVP-01 — احراز هویت
- sample_sales.py
- Agent Guide
- ۳. مسیر اصلی
- Admin Panel Specification (prototype)
- UX/UI Specification (prototype)
- QA & Test Strategy (prototype)
- 01 — Start
- 02 — Continue
- Backlog و نقشه ادامه توسعه
- Product Strategy & Scope (پروژه Kiloos Club)
- مستندات پروژه Kiloos Club
- Kiloos Club — Prototype
- main
- Technical Design (prototype)
- Product Requirements Document (working copy)
- migrations/README.md
- scoring-rule-matrix.md

## God Nodes (most connected - your core abstractions)
1. `Settings` - 98 edges
2. `create_app()` - 80 edges
3. `login()` - 66 edges
4. `score_events` - 47 edges
5. `post()` - 46 edges
6. `users` - 40 edges
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

## Communities (67 total, 8 thin omitted)

### Community 0 - "Settings"
Cohesion: 0.06
Nodes (107): Settings, admin_queue(), admin_sales(), health(), sample_workbook_bytes(), users, sales_imports, ux_sales_imports_fingerprint (+99 more)

### Community 1 - "repo.py"
Cohesion: 0.06
Nodes (86): ۶. الگوی پیام commit / PR, admin_decide(), admin_review(), admin_sale_detail(), home(), submission_page(), archive_mission(), audit() (+78 more)

### Community 2 - "game.py"
Cohesion: 0.15
Nodes (36): bootstrap(), catalog(), _clean_answers(), _collect_flags(), complete_mission(), _daily_mission(), _date_diff(), _day_key() (+28 more)

### Community 3 - "main.py"
Cohesion: 0.10
Nodes (12): csrf_guard(), game_bootstrap(), url_session(), csrf_for(), csrf_token(), CurrentUser, make_token(), read_token() (+4 more)

### Community 4 - "OD-01 — روش ورود"
Cohesion: 0.08
Nodes (30): Before any real user, Deployment Architecture, Today, D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو), OD-01 — روش ورود, OD-11 — یکپارچگی, Admin (admin only), API Specification (implemented surface) (+22 more)

### Community 5 - "test_game_api.py"
Cohesion: 0.13
Nodes (28): game_complete_mission(), game_history(), game_progress(), Sales Quest Arena BFF (prototype, separate game economy), Agreement for this integration, API contract (same-origin BFF), Completion request / response sketch, Delivery sequence / acceptance (+20 more)

### Community 6 - "MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18"
Cohesion: 0.11
Nodes (24): MASTER_PROMPT — پرامپت آماده برای شروع هر ایجنت, نسخه انگلیسی (برای ابزارهای انگلیسی‌زبان), نسخه فارسی (کپی کن), چطور این را به ابزارهای مختلف بدهیم, fallbackها (اگر عقب افتادی), اصل حاکم, سناریوی دمو (۷ دقیقه), پلی‌بوک — ۹ روز تا Prototype (MS-01) (+16 more)

### Community 7 - "AGENTS.md — اپراتور مهندسی Kiloos Club"
Cohesion: 0.08
Nodes (25): AGENTS.md — اپراتور مهندسی Kiloos Club, B — Build, D — Decide, H — Handoff, L — Locate, P — Prove, R — Read, S — Slice (+17 more)

### Community 8 - "create_app"
Cohesion: 0.15
Nodes (20): create_app(), admin_reverse_score(), admin_sales_new(), admin_sales_process(), admin_sales_sample(), admin_sales_upload(), render_error(), hardening() (+12 more)

### Community 9 - "OD-04 — فرمول امتیاز فروش"
Cohesion: 0.25
Nodes (23): ۱۴. تصمیم‌های باز (خلاصه — جزئیات در `context/open-decisions.seed.json`), تصمیم‌های پیش‌فرض قابل بازگشت (ASSUMPTION), D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه), OD-02 — ساختار سازمانی, OD-03 — نمونه فایل فروش, OD-04 — فرمول امتیاز فروش, OD-05 — SKUهای هدف, OD-06 — اعتبارسنجی مأموریت (+15 more)

### Community 10 - "sales.py"
Cohesion: 0.17
Nodes (11): _decimal(), _duplicate(), _invalid(), money_points(), parse_workbook(), _raw(), _row_status(), _sale_date() (+3 more)

### Community 11 - "D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE"
Cohesion: 0.13
Nodes (19): sales_user_map(), 2026-11-09 — Sales import — [PR #7](https://github.com/iciiex/comu-center/pull/7), ix_sales_records_import, 4. Commit and pull request, D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE, Delivered after the prototype window, Authorization rules, Contract (SAMPLE) (+11 more)

### Community 12 - "current_user"
Cohesion: 0.14
Nodes (18): conn_dep(), go(), require_admin(), require_api_user(), require_staff(), require_user(), root(), submit_mission() (+10 more)

### Community 13 - "Implementation status (engineering judgement, 2026-11-11)"
Cohesion: 0.26
Nodes (19): داخل محدوده, ۵. قوانین کسب‌وکار (BR) — خلاصه اجرایی, leaderboard_page(), active_competition(), leaderboard(), C — تکمیل MVP (پس از تأیید مسیر؛ به ترتیب پیشنهادی), جزئیات A8 — اسناد کهنه یا متناقض, Implementation status (engineering judgement, 2026-11-11) (+11 more)

### Community 14 - "D-001 — استفاده از FastAPI + SQLite برای Prototype"
Cohesion: 0.15
Nodes (18): 5. Invariants you must not break, ADR-0001: FastAPI + SQLite for the prototype, Consequences, Decision, Follow-up, Options, D-001 — استفاده از FastAPI + SQLite برای Prototype, Decision Log (+10 more)

### Community 16 - "BR-001 — نمایش مأموریت فقط با: وضعیت Active + داخل بازه زمانی + عضویت در جامعه هدف + عدم نقض محدودیت دسترسی"
Cohesion: 0.13
Nodes (17): روز ۰ — ۲۷ آبان: تحویل, روز ۱ — ۱۸ آبان: اسکلت و قرارداد, روز ۲ — ۱۹ آبان: ورود + پوسته اپ, روز ۳ — ۲۰ آبان: مأموریت‌ها (خواندن), روز ۴ — ۲۱ آبان: ثبت submission + شواهد, روز ۵ — ۲۲ آبان: پنل — صف بررسی, روز ۶ — ۲۳ آبان: موتور امتیاز, روز ۷ — ۲۴ آبان: کیف امتیاز + تاریخچه (+9 more)

### Community 17 - "MVP-04 — مدیریت مأموریت (تعریف/انتشار)"
Cohesion: 0.19
Nodes (15): admin_mission_archive(), admin_mission_create(), admin_mission_edit(), admin_mission_new(), admin_mission_publish(), admin_mission_update(), admin_missions(), mission_by_id() (+7 more)

### Community 18 - "base.html"
Cohesion: 0.18
Nodes (10): evidence_file(), mission_page(), missions_page(), score_page(), MVP-13 — تاریخچه امتیازات, GET /evidence/{evidence_id}, GET /leaderboard, GET /missions (+2 more)

### Community 19 - "3. Queries"
Cohesion: 0.12
Nodes (14): 2026-11-09 — Demo hardening — [PR #5](https://github.com/iciiex/comu-center/pull/5), 2026-11-09 — Kiloos Club prototype — [PR #4](https://github.com/iciiex/comu-center/pull/4), 2026-11-09 — Score corrections — [PR #6](https://github.com/iciiex/comu-center/pull/6), Before Kiloos Club, Changelog, [Unreleased], 3. Queries, Architecture Decision Records (+6 more)

### Community 20 - "pathlib"
Cohesion: 0.15
Nodes (9): 1. Setup and tooling, 2. Checks that fail, 4. Changing application code, 5. Sales import, 6. When the documents disagree with the code, Troubleshooting, load_tool(), test_code_map_lists_exactly_the_routes_the_app_serves() (+1 more)

### Community 21 - "CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club"
Cohesion: 0.13
Nodes (15): CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club, MoSCoW, خارج از محدوده (در MVP نه), ۱. محصول در یک نگاه, ۱۱. KPI (همه پیشنهادی — نه تعهد), ۱۲. NFR, ۱۳. گزینه‌های فناوری (تأییدنشده — `OPEN`), ۱۵. واژه‌نامه (+7 more)

### Community 22 - "نقش ۰۳ — Backend"
Cohesion: 0.14
Nodes (13): Definition of Done نقش, اشتباهات رایج, امتیاز, امنیت و دسترسی, داده فروش, قبل از شروع بخوان, قرارداد خروجی هر برش, قواعد سخت دامنه (+5 more)

### Community 23 - "پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها"
Cohesion: 0.15
Nodes (12): UI, داده, دسترسی و امنیت, صحت دامنه, قاعده ۳۰ ثانیه, پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها, کیفیت, ۱. چک‌لیست بازبینی PR (ترتیب اهمیت) (+4 more)

### Community 24 - "maintenance.py"
Cohesion: 0.21
Nodes (6): now_iso(), _audit(), main(), purge_evidence(), test_dry_run_deletes_nothing(), test_evidence_retention_purges_only_old_files()

### Community 25 - "format_jalali"
Cohesion: 0.27
Nodes (6): format_jalali(), gregorian_to_jalali(), to_persian_digits(), test_digits(), test_formatting_uses_persian_digits(), test_known_dates()

### Community 26 - "D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه)"
Cohesion: 0.17
Nodes (13): D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه), Known issues, Backup (prototype), Common issues, Configuration (environment), Escalation, Evidence retention (manual, D-003), Health (+5 more)

### Community 27 - "۱۰. تحویل و فازها"
Cohesion: 0.21
Nodes (12): ۱۰. تحویل و فازها, Known gaps, In progress, چه چیزی هنوز نیست (عمداً), EP-02 — Organization, EP-04 — Mission Execution, EP-08 — Competition & Leaderboard, EP-10 — Reports (+4 more)

### Community 28 - "نقش ۰۱ — Product / Business Analyst"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۱ — Product / Business Analyst (+3 more)

### Community 29 - "نقش ۰۲ — Solution Architect"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۲ — Solution Architect (+3 more)

### Community 30 - "نقش ۰۵ — QA"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, اولویت تست بر اساس ریسک, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل (+3 more)

### Community 31 - "پلی‌بوک — موتور امتیاز و قوانین"
Cohesion: 0.18
Nodes (10): پلی‌بوک — موتور امتیاز و قوانین, ۱. مدل ذهنی, ۲. قرارداد داده پیشنهادی, ۳. الگوریتم (اجباری), ۴. انواع محاسبه, ۵. idempotency — سه لایه, ۶. اصلاح، برگشت، محاسبه مجدد, ۷. تست طلایی (Golden Tests) (+2 more)

### Community 32 - "نقش ۰۴ — Frontend / Mobile"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, قبل از شروع بخوان, قرارداد خروجی هر صفحه, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۴ — Frontend / Mobile (+2 more)

### Community 33 - "نقش ۰۶ — DevOps"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, حداقل‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۶ — DevOps (+2 more)

### Community 34 - "db.py"
Cohesion: 0.25
Nodes (5): apply_migrations(), connect(), init_db(), R3 — Change the schema, Migrations

### Community 35 - "seed_demo"
Cohesion: 0.27
Nodes (6): _id(), _iso(), seed_demo(), competitions, organizations, sales_user_map

### Community 36 - "پلی‌بوک — ورود داده فروش (Sales Import)"
Cohesion: 0.20
Nodes (9): پلی‌بوک — ورود داده فروش (Sales Import), ۱. چرخه عمر Import, ۲. قرارداد ورودی (اولیه — `OPEN` تا دریافت فایل واقعی), ۳. اعتبارسنجی در دو سطح, ۴. ضدتکرار, ۵. پردازش, ۶. Reconciliation, ۷. چک‌لیست برش (+1 more)

### Community 37 - "۱۲. بلوک handoff همین نشست"
Cohesion: 0.20
Nodes (10): Changes made, Context read, Contract changes, Decisions and assumptions, Files changed, Recommended next step, Remaining work, Risks / blockers (+2 more)

### Community 38 - "نقش ۰۷ — Integrator / Lead"
Cohesion: 0.22
Nodes (8): Definition of Done نقش, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۷ — Integrator / Lead, پرامپت نقش (کپی), کارهای اصلی

### Community 39 - "A — پیش از MS-01 (به ترتیب اولویت)"
Cohesion: 0.25
Nodes (8): A — پیش از MS-01 (به ترتیب اولویت), جزئیات A10 — اسکن secret در CI, جزئیات A3 — وقت تهران, جزئیات A4 — سناریو و دوره نمونه, جزئیات A5 — شفافیت امتیاز, جزئیات A6 — ریزه‌کاری‌ها (۴ مورد DONE 2026-11-12؛ مورد ۵ باز), جزئیات A7 — نسخه وابستگی‌ها, جزئیات A9

### Community 40 - "سناریوی دمو — MS-01"
Cohesion: 0.25
Nodes (8): سناریوی دمو — MS-01, ۱. آماده‌سازی صبح روز دمو, ۲. حساب‌های نمایشی, ۴. بخش اختیاری — اصلاح امتیاز (نگار), ۶. کارهایی که در دمو نباید انجام شود, ۷. اگر چیزی خراب شد, ۸. پرسش‌هایی که در همین جلسه باید از کارفرما گرفته شود, ۹. تمرین

### Community 41 - "پلی‌بوک — برش عمودی (Vertical Slice)"
Cohesion: 0.29
Nodes (6): پلی‌بوک — برش عمودی (Vertical Slice), ۱. برش را تعریف کن, ۲. قرارداد اول (Contract-first), ۳. ترتیب ساخت, ۴. معیار «تمام» برش, ۵. ضدالگوها

### Community 43 - "3. Recipes"
Cohesion: 0.29
Nodes (7): 3. Recipes, R1 — Add a page, R2 — Add an action, R4 — Change scoring behaviour, R6 — Record a decision or an open question, R7 — Fix a defect from the backlog, R8 — Keep the map and the traceability current

### Community 44 - "03 — Deliver"
Cohesion: 0.29
Nodes (7): 03 — Deliver, 1. Gate: run these and read the output, 2. Check the behaviour yourself, 3. Update the documents, 5. Hand off, 6. Final self-check, Statuses you may write

### Community 45 - "Knowledge Graph"
Cohesion: 0.29
Nodes (7): 1. What is in `graphify-out/`, 2. How it is built, and what that means for trust, 4. Scripting against `graph.json`, 5. Graph or generated map?, 6. Keeping it current, 7. Limits, Knowledge Graph

### Community 46 - "Database ERD & Schema (prototype)"
Cohesion: 0.29
Nodes (6): Data rules, Database ERD & Schema (prototype), Relations (macro), Sales import tables (0003), Tables, Why these constraints

### Community 47 - "Scoring Engine (prototype)"
Cohesion: 0.29
Nodes (6): Explainability, Not implemented (explicit), Rule selection, Sales records — SAMPLE per-amount rule, Scoring Engine (prototype), Test coverage (executed)

### Community 48 - "MVP-01 — احراز هویت"
Cohesion: 0.47
Nodes (6): demo_login(), 2026-11-11 — Documentation, agent guide and knowledge graph — [PR #8](https://github.com/iciiex/comu-center/pull/8), ۴. چه چیزی تحویل می‌شود, EP-01 — Auth & User Mgmt, MVP-01 — احراز هویت, MVP-03 — داشبورد کاربر (امتیاز، مأموریت، پیشرفت)

### Community 50 - "Agent Guide"
Cohesion: 0.33
Nodes (6): Agent Guide, Commands you will use, Find anything, Keeping this guide true, Lookup files, The three phases

### Community 51 - "۳. مسیر اصلی"
Cohesion: 0.33
Nodes (6): پرده ۲ — اپراتور بررسی می‌کند (حسین), پرده ۳ — امتیاز قابل توضیح (سارا), پرده ۴ — مدیر امتیاز مأموریت را عوض می‌کند (نگار), پرده ۵ — ورود داده فروش (نگار), پرده ۶ — نتیجه برای ویزیتور (سارا), ۳. مسیر اصلی

### Community 52 - "Admin Panel Specification (prototype)"
Cohesion: 0.33
Nodes (5): Access model, Admin Panel Specification (prototype), Implemented, Not implemented, Open

### Community 53 - "UX/UI Specification (prototype)"
Cohesion: 0.33
Nodes (5): Gaps, Implemented, Next, UX rules applied, UX/UI Specification (prototype)

### Community 54 - "QA & Test Strategy (prototype)"
Cohesion: 0.33
Nodes (5): Commands, Implemented automated coverage (71 tests on 2026-11-12), Not covered yet, QA & Test Strategy (prototype), Rule

### Community 55 - "01 — Start"
Cohesion: 0.40
Nodes (5): 01 — Start, 1. Read in this order, 2. Set up and verify, 3. Layout, 7. Where to go next

### Community 56 - "02 — Continue"
Cohesion: 0.40
Nodes (4): 02 — Continue, 1. The loop, with this repository's commands, 4. Which document to update for which change, 5. Boundaries

### Community 57 - "Backlog و نقشه ادامه توسعه"
Cohesion: 0.40
Nodes (5): Backlog و نقشه ادامه توسعه, D — Harden (فقط پس از ثبت P→H؛ تا RC), شواهد اجرا (2026-11-11), شواهد اجرا (2026-11-12 — برش پایداری دمو), قاعده نگهداری این فایل

### Community 58 - "Product Strategy & Scope (پروژه Kiloos Club)"
Cohesion: 0.40
Nodes (4): Product Strategy & Scope (پروژه Kiloos Club), آخرین تطبیق, خلاصه قابل اتکا, قاعده

### Community 59 - "مستندات پروژه Kiloos Club"
Cohesion: 0.40
Nodes (4): شروع، ادامه و تحویل (راهنمای ایجنت), قواعد, مستندات پروژه Kiloos Club, منبع اصلی

### Community 60 - "Kiloos Club — Prototype"
Cohesion: 0.40
Nodes (4): Kiloos Club — Prototype, ایمنی داده, ساختار, مستندات

### Community 62 - "Technical Design (prototype)"
Cohesion: 0.50
Nodes (3): Design rules in code, Gaps, Technical Design (prototype)

## Knowledge Gaps
- **5 isolated node(s):** `EP-13 — QA`, `GET /`, `DELETE /api/v1/game/missions/{mission_id}/draft`, `PUT /api/v1/game/missions/{mission_id}/draft`, `PATCH /api/v1/game/profile`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 384 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `create_app` to `Settings`, `repo.py`, `db.py`, `main.py`, `game.py`, `test_game_api.py`, `config.py`, `current_user`, `Implementation status (engineering judgement, 2026-11-11)`, `MVP-01 — احراز هویت`, `MVP-04 — مدیریت مأموریت (تعریف/انتشار)`, `base.html`, `pathlib`, `format_jalali`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Are the 83 inferred relationships involving `Settings` (e.g. with `create_app()` and `main()`) actually correct?**
  _`Settings` has 83 INFERRED edges - model-reasoned connections that need verification._
- **What connects `EP-13 — QA`, `GET /`, `DELETE /api/v1/game/missions/{mission_id}/draft` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Settings` be split into smaller, more focused modules?**
  _Cohesion score 0.060944925915571706 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `repo.py`, `main.py`, `seed_demo`, `test_game_api.py`, `create_app`, `config.py`, `current_user`, `3. Queries`, `maintenance.py`, `main`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `create_app()` (e.g. with `Settings` and `to_persian_digits()`) actually correct?**
  _`create_app()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `repo.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05546813532651455 - nodes in this community are weakly interconnected._
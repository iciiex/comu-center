# Graph Report - kiloos-club  (2026-11-18)

## Corpus Check
- 98 files · ~98,038 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1515 nodes · 4920 edges · 75 communities (72 shown, 3 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 455 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- game.py
- make_play
- test_kilos_play.py
- play_data.py
- Settings
- play_accounts
- play.py
- MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18
- users
- test_demo_stability.py
- award_mission_approval
- main.py
- create_submission
- login
- Implementation status (engineering judgement, 2026-11-11)
- repo.py
- Tribal Gamification — Architecture and Two-Agent Plan
- conftest.py
- page
- org_units
- AGENTS.md — اپراتور مهندسی Kiloos Club
- now
- OD-01 — روش ورود
- create_app
- sales.py
- pathlib
- post
- D-001 — استفاده از FastAPI + SQLite برای Prototype
- A — پیش از MS-01 (به ترتیب اولویت)
- kilos-play-demo.md
- D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه)
- sqlite3
- D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه)
- agent-guide/README.md
- Tribal Gamification API Contract (proposal)
- current_user
- D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE
- CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club
- MVP-11 — پنل مدیریت
- test_uat_legacy_auth.py
- D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو)
- Current Project State
- نقش ۰۳ — Backend
- db.py
- پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها
- format_jalali
- نقش ۰۱ — Product / Business Analyst
- نقش ۰۲ — Solution Architect
- نقش ۰۵ — QA
- sales_user_map
- 3. Recipes
- روزشمار
- پلی‌بوک — موتور امتیاز و قوانین
- نقش ۰۴ — Frontend / Mobile
- نقش ۰۶ — DevOps
- تمرین نهایی کیلوس‌پلی
- سند تحویل پروژه Kiloos Club (Handover)
- پلی‌بوک — ورود داده فروش (Sales Import)
- ۱۲. بلوک handoff همین نشست
- MVP-07 — موتور امتیازدهی
- نقش ۰۷ — Integrator / Lead
- پلی‌بوک — برش عمودی (Vertical Slice)
- 03 — Deliver
- Knowledge Graph
- ۳. مسیر اصلی
- Kiloos Club — Prototype
- Agent Guide
- راهنمای نمایش و تحویل کیلوس‌پلی
- Admin Panel Specification (prototype)
- UX/UI Specification (prototype)
- QA & Test Strategy (prototype)
- Product Strategy & Scope (پروژه Kiloos Club)
- قرارداد مهندسی کیلوس‌پلی
- scoring-rule-matrix.md

## God Nodes (most connected - your core abstractions)
1. `Settings` - 110 edges
2. `create_app()` - 105 edges
3. `login()` - 75 edges
4. `users` - 53 edges
5. `make_play()` - 47 edges
6. `score_events` - 47 edges
7. `play_accounts` - 47 edges
8. `PlayError` - 46 edges
9. `post()` - 46 edges
10. `one()` - 39 edges

## Surprising Connections (you probably didn't know these)
- `2.6 A test` --references--> `Settings`  [INFERRED]
  docs/agent-guide/02-continue.md → app/config.py
- `R3 — Change the schema` --references--> `apply_migrations()`  [INFERRED]
  docs/agent-guide/02-continue.md → app/db.py
- `Migrations` --references--> `apply_migrations()`  [INFERRED]
  docs/architecture/database-erd.md → app/db.py
- `2.2 An action (POST)` --references--> `DomainError`  [INFERRED]
  docs/agent-guide/02-continue.md → app/repo.py
- `R2 — Add an action` --references--> `DomainError`  [INFERRED]
  docs/agent-guide/02-continue.md → app/repo.py

## Import Cycles
- None detected.

## Communities (75 total, 3 thin omitted)

### Community 0 - "game.py"
Cohesion: 0.07
Nodes (70): _all_missions(), bootstrap(), catalog(), _clean_answers(), _collect_flags(), complete_mission(), _daily_mission(), _date_diff() (+62 more)

### Community 1 - "make_play"
Cohesion: 0.10
Nodes (50): PlayError, when(), writing(), make_play(), action(), admin_login(), admin_login_page(), back() (+42 more)

### Community 2 - "test_kilos_play.py"
Cohesion: 0.09
Nodes (33): D-006 — جداسازی دموی خانوادگی کیلوس‌پلی, GET /play/{area}/{page}, GET /play/{area}/result/{result_id}, GET /play/entrance, GET /play/family/game/{key}, GET /play/pulse, GET /play/state/{code}, POST /play/action (+25 more)

### Community 3 - "play_data.py"
Cohesion: 0.12
Nodes (36): achievements(), add_score(), balance(), campaigns(), competitions(), day(), epoch(), family_stats() (+28 more)

### Community 4 - "Settings"
Cohesion: 0.12
Nodes (24): _int_env(), Settings, main(), purge_evidence(), main(), R5 — Add a setting, GET /home, POST /demo-login (+16 more)

### Community 5 - "play_accounts"
Cohesion: 0.15
Nodes (39): family_members(), history(), ledger(), rows(), play_accounts, play_audit, play_cards, play_claims (+31 more)

### Community 6 - "play.py"
Cohesion: 0.20
Nodes (32): audit(), choice(), fmt(), integer(), iso_date(), need(), one(), request_id() (+24 more)

### Community 7 - "MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18"
Cohesion: 0.08
Nodes (35): ۱۰. تحویل و فازها, MASTER_PROMPT — پرامپت آماده برای شروع هر ایجنت, نسخه انگلیسی (برای ابزارهای انگلیسی‌زبان), نسخه فارسی (کپی کن), چطور این را به ابزارهای مختلف بدهیم, ADR-0001: FastAPI + SQLite for the prototype, Consequences, Context (+27 more)

### Community 8 - "users"
Cohesion: 0.12
Nodes (29): admin_sale_detail(), sales_page_context(), list_queue(), sales_record_counts(), sales_score_events(), score_event_detail(), seed_demo(), competitions (+21 more)

### Community 9 - "test_demo_stability.py"
Cohesion: 0.17
Nodes (28): ۶. الگوی پیام commit / PR, sample_workbook_bytes(), missions, point_wallets, Tests and verification, BR-003 — امتیاز فقط پس از تحقق شرایط معتبر؛ برای مأموریت نیازمند بررسی، پس از تأیید, EP-05 — Verification, EP-06 — Scoring (+20 more)

### Community 10 - "award_mission_approval"
Cohesion: 0.14
Nodes (19): _audit(), process_sales_import(), review_submission(), award_mission_approval(), award_sales_record(), _existing(), find_rule_version(), _now() (+11 more)

### Community 11 - "main.py"
Cohesion: 0.10
Nodes (11): demo_login(), game_bootstrap(), csrf_for(), csrf_token(), make_token(), read_token(), session_token(), set_session() (+3 more)

### Community 12 - "create_submission"
Cohesion: 0.13
Nodes (26): admin_mission_archive(), admin_mission_create(), admin_mission_publish(), admin_mission_update(), go(), submit_mission(), render_error(), archive_mission() (+18 more)

### Community 13 - "login"
Cohesion: 0.20
Nodes (27): admin_sales_sample(), admin_sales_upload(), render_error(), sales_external_ids(), sales_imports, ux_sales_imports_fingerprint, BR-010 — فایل فروش: شناسه پردازش، گزارش رکورد نامعتبر، بدون امتیاز تکراری، قابل پیگیری، اصلاح با تاریخچه, MVP-08 — ورود داده فروش از فایل (+19 more)

### Community 14 - "Implementation status (engineering judgement, 2026-11-11)"
Cohesion: 0.15
Nodes (31): داخل محدوده, ۵. قوانین کسب‌وکار (BR) — خلاصه اجرایی, مأموریت و submission, active_competition(), leaderboard(), 2026-11-11 — Documentation, agent guide and knowledge graph — [PR #8](https://github.com/iciiex/comu-center/pull/8), C — تکمیل MVP (پس از تأیید مسیر؛ به ترتیب پیشنهادی), جزئیات A8 — اسناد کهنه یا متناقض (+23 more)

### Community 15 - "repo.py"
Cohesion: 0.15
Nodes (19): admin_decide(), admin_review(), evidence_file(), submission_page(), create_sales_import(), evidence(), get_mission_for_user(), list_missions_admin() (+11 more)

### Community 16 - "Tribal Gamification — Architecture and Two-Agent Plan"
Cohesion: 0.07
Nodes (30): game_progress(), Tables, 1. Product direction recorded, 2. Current architecture and impact, 3.1 Configurable organization tree, 3.2 RBAC and data visibility, 3.3 Admin Excel ingestion and reference data, 3.4 Campaigns, missions and review (+22 more)

### Community 17 - "conftest.py"
Cohesion: 0.12
Nodes (14): tribal_bootstrap(), GET /api/v1/tribal/bootstrap, GET /api/v1/tribal/org-units, client(), csrf(), db(), play_client(), play_settings() (+6 more)

### Community 18 - "page"
Cohesion: 0.12
Nodes (19): admin_mission_edit(), admin_mission_new(), admin_missions(), admin_reverse_score(), admin_sales_new(), admin_sales_process(), _http_error(), leaderboard_page() (+11 more)

### Community 19 - "org_units"
Cohesion: 0.14
Nodes (17): _decode_cursor(), _encode_cursor(), get_unit(), list_units(), ix_org_memberships_unit_period, ix_org_memberships_user_period, ix_org_units_parent, ix_org_units_type (+9 more)

### Community 20 - "AGENTS.md — اپراتور مهندسی Kiloos Club"
Cohesion: 0.08
Nodes (25): AGENTS.md — اپراتور مهندسی Kiloos Club, B — Build, D — Decide, H — Handoff, L — Locate, P — Prove, R — Read, S — Slice (+17 more)

### Community 21 - "now"
Cohesion: 0.21
Nodes (21): dump(), now(), advance(), deal(), eligible_guessers(), feedback(), fetch(), finish() (+13 more)

### Community 22 - "OD-01 — روش ورود"
Cohesion: 0.25
Nodes (24): ۱۴. تصمیم‌های باز (خلاصه — جزئیات در `context/open-decisions.seed.json`), تصمیم‌های پیش‌فرض قابل بازگشت (ASSUMPTION), OD-01 — روش ورود, OD-02 — ساختار سازمانی, OD-03 — نمونه فایل فروش, OD-04 — فرمول امتیاز فروش, OD-05 — SKUهای هدف, OD-06 — اعتبارسنجی مأموریت (+16 more)

### Community 23 - "create_app"
Cohesion: 0.13
Nodes (20): create_app(), game_demo_login(), game_demo_users(), game_logout(), hardening(), health(), legacy_demo_users(), login_page() (+12 more)

### Community 24 - "sales.py"
Cohesion: 0.17
Nodes (11): _decimal(), _duplicate(), _invalid(), money_points(), parse_workbook(), _raw(), _row_status(), _sale_date() (+3 more)

### Community 25 - "pathlib"
Cohesion: 0.11
Nodes (12): build_sample_workbook(), main(), 1. Setup and tooling, 2. Checks that fail, 3. Writing tests, 4. Changing application code, 5. Sales import, 6. When the documents disagree with the code (+4 more)

### Community 26 - "post"
Cohesion: 0.25
Nodes (16): ux_score_events_corrects, BR-005 — همه تغییرات امتیاز رویداد مستقل و append-only هستند؛ حذف/بازنویسی ممنوع، اصلاح با رویداد اصلاحی, EP-08 — Competition & Leaderboard, POST /admin/score-events/{event_id}/reverse, post(), awarded_submission(), test_a_correction_cannot_be_reversed(), test_leaderboard_reflects_the_correction() (+8 more)

### Community 27 - "D-001 — استفاده از FastAPI + SQLite برای Prototype"
Cohesion: 0.10
Nodes (19): 2026-11-09 — Kiloos Club prototype — [PR #4](https://github.com/iciiex/comu-center/pull/4), 01 — Start, 1. Read in this order, 2. Set up and verify, 3. Layout, 5. Invariants you must not break, 7. Where to go next, Architecture Decision Records (+11 more)

### Community 28 - "A — پیش از MS-01 (به ترتیب اولویت)"
Cohesion: 0.12
Nodes (19): home(), score_page(), list_active_missions(), list_user_submissions(), wallet_balance(), Design rules in code, Flows, Gaps (+11 more)

### Community 29 - "kilos-play-demo.md"
Cohesion: 0.16
Nodes (9): آزمون‌ها و شواهد بازآزمایی, بخش‌هایی از شواهد تصویری اجرای محلی, فایل‌ها و قرارداد اجرایی, مرحلهٔ بعد: UAT روی میزبان نهایی, کیلوس‌پلی | گزارش اصلاح پنج یافتهٔ UAT, شروع، ادامه و تحویل (راهنمای ایجنت), قواعد, مستندات پروژه Kiloos Club (+1 more)

### Community 30 - "D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه)"
Cohesion: 0.11
Nodes (20): 2026-11-09 — Demo hardening — [PR #5](https://github.com/iciiex/comu-center/pull/5), 2026-11-09 — Score corrections — [PR #6](https://github.com/iciiex/comu-center/pull/6), 2026-11-18 — اصلاح پنج یافتهٔ UAT کیلوس‌پلی, 2026-11-18 — کیلوس‌پلی (نسخهٔ نمایشی), Before Kiloos Club, Changelog, [Unreleased], D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه) (+12 more)

### Community 31 - "sqlite3"
Cohesion: 0.16
Nodes (11): _id(), _iso(), GET /health, GET /missions/{mission_id}, test_duplicate_request_id_is_idempotent(), test_full_flow_approval_scores_once(), test_health_declares_prototype(), test_login_page_lists_demo_users() (+3 more)

### Community 32 - "D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه)"
Cohesion: 0.11
Nodes (18): 3. Queries, D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه), سناریوی دمو — MS-01, ۱. آماده‌سازی صبح روز دمو, ۲. حساب‌های نمایشی, ۴. بخش اختیاری — اصلاح امتیاز (نگار), ۶. کارهایی که در دمو نباید انجام شود, ۷. اگر چیزی خراب شد (+10 more)

### Community 34 - "Tribal Gamification API Contract (proposal)"
Cohesion: 0.11
Nodes (18): 10. Contract review gates (before implementation), 1. Shared contract, 2. Player and organization reads, 3. Campaigns and mission runs, 4. Review workload, 5. League and ranking reads, 6. Badges and achievements, 7. Admin/back-office APIs (+10 more)

### Community 35 - "current_user"
Cohesion: 0.18
Nodes (14): csrf_guard(), require_admin(), require_api_user(), require_staff(), require_user(), LoginRequired, current_user(), 4. How a request flows (+6 more)

### Community 36 - "D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE"
Cohesion: 0.19
Nodes (15): 2026-11-09 — Sales import — [PR #7](https://github.com/iciiex/comu-center/pull/7), 4. Commit and pull request, D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE, Delivered after the prototype window, Authorization rules, Dedupe, Demo, Lifecycle (+7 more)

### Community 37 - "CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club"
Cohesion: 0.13
Nodes (15): CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club, MoSCoW, خارج از محدوده (در MVP نه), ۱. محصول در یک نگاه, ۱۱. KPI (همه پیشنهادی — نه تعهد), ۱۲. NFR, ۱۳. گزینه‌های فناوری (تأییدنشده — `OPEN`), ۱۵. واژه‌نامه (+7 more)

### Community 38 - "MVP-11 — پنل مدیریت"
Cohesion: 0.23
Nodes (13): admin_queue(), admin_sales(), count_queue(), EP-09 — Admin Panel, MVP-11 — پنل مدیریت, GET /admin/sales, GET /admin/sales/new, GET /admin/submissions (+5 more)

### Community 39 - "test_uat_legacy_auth.py"
Cohesion: 0.23
Nodes (13): root(), GET /, GET /api/v1/game/demo-users, GET /login, GET /play/, POST /api/v1/game/demo-login, test_game_demo_login_is_disabled_outside_dev_and_test(), test_play_is_not_mounted_outside_demo() (+5 more)

### Community 40 - "D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو)"
Cohesion: 0.14
Nodes (14): Before any real user, Deployment Architecture, Today, D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو), Admin (admin only), API Specification (implemented surface), Authentication modes, Error codes (domain layer) (+6 more)

### Community 41 - "Current Project State"
Cohesion: 0.13
Nodes (13): fallbackها (اگر عقب افتادی), اصل حاکم, سناریوی دمو (۷ دقیقه), پلی‌بوک — ۹ روز تا Prototype (MS-01), چک‌لیست «قابل نمایش», Current Project State, Decisions approved, Demo status (+5 more)

### Community 42 - "نقش ۰۳ — Backend"
Cohesion: 0.14
Nodes (13): Definition of Done نقش, اشتباهات رایج, امتیاز, امنیت و دسترسی, داده فروش, قبل از شروع بخوان, قرارداد خروجی هر برش, قواعد سخت دامنه (+5 more)

### Community 43 - "db.py"
Cohesion: 0.22
Nodes (8): apply_migrations(), connect(), init_db(), now_iso(), conn_dep(), initialize(), connection(), protect()

### Community 44 - "پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها"
Cohesion: 0.15
Nodes (12): UI, داده, دسترسی و امنیت, صحت دامنه, قاعده ۳۰ ثانیه, پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها, کیفیت, ۱. چک‌لیست بازبینی PR (ترتیب اهمیت) (+4 more)

### Community 45 - "format_jalali"
Cohesion: 0.27
Nodes (6): format_jalali(), gregorian_to_jalali(), to_persian_digits(), test_digits(), test_formatting_uses_persian_digits(), test_known_dates()

### Community 46 - "نقش ۰۱ — Product / Business Analyst"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۱ — Product / Business Analyst (+3 more)

### Community 47 - "نقش ۰۲ — Solution Architect"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۲ — Solution Architect (+3 more)

### Community 48 - "نقش ۰۵ — QA"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, اولویت تست بر اساس ریسک, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل (+3 more)

### Community 49 - "sales_user_map"
Cohesion: 0.18
Nodes (11): sales_records(), sales_user_map(), Data rules, Database ERD & Schema (prototype), Known gaps, Migrations, Relations (macro), Sales import tables (0003) (+3 more)

### Community 50 - "3. Recipes"
Cohesion: 0.17
Nodes (12): 02 — Continue, 1. The loop, with this repository's commands, 3. Recipes, 4. Which document to update for which change, 5. Boundaries, R1 — Add a page, R2 — Add an action, R3 — Change the schema (+4 more)

### Community 51 - "روزشمار"
Cohesion: 0.18
Nodes (11): روز ۰ — ۲۷ آبان: تحویل, روز ۱ — ۱۸ آبان: اسکلت و قرارداد, روز ۲ — ۱۹ آبان: ورود + پوسته اپ, روز ۳ — ۲۰ آبان: مأموریت‌ها (خواندن), روز ۴ — ۲۱ آبان: ثبت submission + شواهد, روز ۵ — ۲۲ آبان: پنل — صف بررسی, روز ۶ — ۲۳ آبان: موتور امتیاز, روز ۷ — ۲۴ آبان: کیف امتیاز + تاریخچه (+3 more)

### Community 52 - "پلی‌بوک — موتور امتیاز و قوانین"
Cohesion: 0.18
Nodes (10): پلی‌بوک — موتور امتیاز و قوانین, ۱. مدل ذهنی, ۲. قرارداد داده پیشنهادی, ۳. الگوریتم (اجباری), ۴. انواع محاسبه, ۵. idempotency — سه لایه, ۶. اصلاح، برگشت، محاسبه مجدد, ۷. تست طلایی (Golden Tests) (+2 more)

### Community 53 - "نقش ۰۴ — Frontend / Mobile"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, قبل از شروع بخوان, قرارداد خروجی هر صفحه, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۴ — Frontend / Mobile (+2 more)

### Community 54 - "نقش ۰۶ — DevOps"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, حداقل‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۶ — DevOps (+2 more)

### Community 55 - "تمرین نهایی کیلوس‌پلی"
Cohesion: 0.18
Nodes (11): تمرین نهایی کیلوس‌پلی, محیط، دستگاه و مرورگر, نتیجهٔ واقعی شیر و مرغ, پذیرش نهایی — هنوز انجام نشده, پیوست · شواهد بازی و دفتر, پیوست · شواهد فروش و اتصال, ۱ · مسیر کامل از فروش تا بازی, ۲ · خطا و بازیابی (+3 more)

### Community 56 - "سند تحویل پروژه Kiloos Club (Handover)"
Cohesion: 0.18
Nodes (11): اجرای نسخه تحویل, سند تحویل پروژه Kiloos Club (Handover), شواهد اجرا, ۰. تحویل برش پایداری دمو — 2026-11-12, ۱۰. تاریخچه کوتاه, ۱۱. آنچه این سند تضمین نمی‌کند, ۲. از کجا شروع کنم, ۳. اجرا و راستی‌آزمایی (+3 more)

### Community 57 - "پلی‌بوک — ورود داده فروش (Sales Import)"
Cohesion: 0.20
Nodes (9): پلی‌بوک — ورود داده فروش (Sales Import), ۱. چرخه عمر Import, ۲. قرارداد ورودی (اولیه — `OPEN` تا دریافت فایل واقعی), ۳. اعتبارسنجی در دو سطح, ۴. ضدتکرار, ۵. پردازش, ۶. Reconciliation, ۷. چک‌لیست برش (+1 more)

### Community 58 - "۱۲. بلوک handoff همین نشست"
Cohesion: 0.20
Nodes (10): Changes made, Context read, Contract changes, Decisions and assumptions, Files changed, Recommended next step, Remaining work, Risks / blockers (+2 more)

### Community 59 - "MVP-07 — موتور امتیازدهی"
Cohesion: 0.38
Nodes (7): BR-004 — هر فعالیت شناسه یکتا دارد؛ برای یک فعالیت تأییدشده بیش از یک بار امتیاز ایجاد نمی‌شود, MVP-07 — موتور امتیازدهی, test_active_rule_version_selection_after_retirement(), test_award_is_idempotent(), test_event_has_traceable_explain(), test_seeded_approval_created_one_event(), test_wallet_matches_ledger()

### Community 60 - "نقش ۰۷ — Integrator / Lead"
Cohesion: 0.22
Nodes (8): Definition of Done نقش, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۷ — Integrator / Lead, پرامپت نقش (کپی), کارهای اصلی

### Community 61 - "پلی‌بوک — برش عمودی (Vertical Slice)"
Cohesion: 0.29
Nodes (6): پلی‌بوک — برش عمودی (Vertical Slice), ۱. برش را تعریف کن, ۲. قرارداد اول (Contract-first), ۳. ترتیب ساخت, ۴. معیار «تمام» برش, ۵. ضدالگوها

### Community 62 - "03 — Deliver"
Cohesion: 0.29
Nodes (7): 03 — Deliver, 1. Gate: run these and read the output, 2. Check the behaviour yourself, 3. Update the documents, 5. Hand off, 6. Final self-check, Statuses you may write

### Community 63 - "Knowledge Graph"
Cohesion: 0.29
Nodes (7): 1. What is in `graphify-out/`, 2. How it is built, and what that means for trust, 4. Scripting against `graph.json`, 5. Graph or generated map?, 6. Keeping it current, 7. Limits, Knowledge Graph

### Community 64 - "۳. مسیر اصلی"
Cohesion: 0.29
Nodes (7): پرده ۱ — ویزیتور مأموریت را انجام می‌دهد (سارا), پرده ۲ — اپراتور بررسی می‌کند (حسین), پرده ۳ — امتیاز قابل توضیح (سارا), پرده ۴ — مدیر امتیاز مأموریت را عوض می‌کند (نگار), پرده ۵ — ورود داده فروش (نگار), پرده ۶ — نتیجه برای ویزیتور (سارا), ۳. مسیر اصلی

### Community 65 - "Kiloos Club — Prototype"
Cohesion: 0.29
Nodes (7): Kiloos Club — Prototype, اجرا, ایمنی داده, حساب‌های نمایشی, ساختار, مستندات, کیلوس‌پلی — دموی خانواده

### Community 66 - "Agent Guide"
Cohesion: 0.33
Nodes (6): Agent Guide, Commands you will use, Find anything, Keeping this guide true, Lookup files, The three phases

### Community 67 - "راهنمای نمایش و تحویل کیلوس‌پلی"
Cohesion: 0.33
Nodes (6): اجرا, دو بازی دیگر, راهنمای نمایش و تحویل کیلوس‌پلی, رفتار مشخص و گام بعد, نمایش سر تا سر: فروش امروز، بازی امشب, گزارش فازها و فایل‌ها

### Community 68 - "Admin Panel Specification (prototype)"
Cohesion: 0.33
Nodes (5): Access model, Admin Panel Specification (prototype), Implemented, Not implemented, Open

### Community 69 - "UX/UI Specification (prototype)"
Cohesion: 0.33
Nodes (5): Gaps, Implemented, Next, UX rules applied, UX/UI Specification (prototype)

### Community 70 - "QA & Test Strategy (prototype)"
Cohesion: 0.33
Nodes (5): Commands, Implemented automated coverage (71 tests on 2026-11-12), Not covered yet, QA & Test Strategy (prototype), Rule

### Community 71 - "Product Strategy & Scope (پروژه Kiloos Club)"
Cohesion: 0.40
Nodes (4): Product Strategy & Scope (پروژه Kiloos Club), آخرین تطبیق, خلاصه قابل اتکا, قاعده

### Community 72 - "قرارداد مهندسی کیلوس‌پلی"
Cohesion: 0.50
Nodes (4): قرارداد HTTP و حالت زنده, قرارداد مهندسی کیلوس‌پلی, قواعد دادهٔ نمونه, معماری و دامنه

## Knowledge Gaps
- **6 isolated node(s):** `EP-13 — QA`, `DELETE /api/v1/game/missions/{mission_id}/draft`, `PUT /api/v1/game/missions/{mission_id}/draft`, `PATCH /api/v1/game/profile`, `GET /play/admin/game/{key}` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 459 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `create_app` to `game.py`, `make_play`, `test_kilos_play.py`, `Settings`, `users`, `test_demo_stability.py`, `main.py`, `create_submission`, `login`, `repo.py`, `Tribal Gamification — Architecture and Two-Agent Plan`, `conftest.py`, `page`, `pathlib`, `A — پیش از MS-01 (به ترتیب اولویت)`, `current_user`, `MVP-11 — پنل مدیریت`, `test_uat_legacy_auth.py`, `db.py`, `format_jalali`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **Are the 89 inferred relationships involving `Settings` (e.g. with `create_app()` and `main()`) actually correct?**
  _`Settings` has 89 INFERRED edges - model-reasoned connections that need verification._
- **What connects `EP-13 — QA`, `DELETE /api/v1/game/missions/{mission_id}/draft`, `PUT /api/v1/game/missions/{mission_id}/draft` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `game.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07414500683994528 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه)`, `make_play`, `game.py`, `current_user`, `play.py`, `MVP-11 — پنل مدیریت`, `users`, `test_demo_stability.py`, `test_uat_legacy_auth.py`, `main.py`, `login`, `conftest.py`, `create_app`, `post`, `MVP-07 — موتور امتیازدهی`, `sqlite3`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `create_app()` (e.g. with `Settings` and `to_persian_digits()`) actually correct?**
  _`create_app()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `make_play` be split into smaller, more focused modules?**
  _Cohesion score 0.09836065573770492 - nodes in this community are weakly interconnected._
# Graph Report - kiloos-club  (2026-11-12)

## Corpus Check
- 85 files · ~71,592 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1189 nodes · 3469 edges · 67 communities (63 shown, 4 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 409 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Settings
- repo.py
- game.py
- users
- MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18
- sales.py
- create_app
- main.py
- AGENTS.md — اپراتور مهندسی Kiloos Club
- test_game_api.py
- D-001 — استفاده از FastAPI + SQLite برای Prototype
- OD-04 — فرمول امتیاز فروش
- OD-01 — روش ورود
- سند تحویل پروژه Kiloos Club (Handover)
- OD-12 — ظرفیت
- config.py
- seed.py
- D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE
- current_user
- C — تکمیل MVP (پس از تأیید مسیر؛ به ترتیب پیشنهادی)
- test_hardening.py
- D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه)
- CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club
- Implementation status (engineering judgement, 2026-11-11)
- test_docs.py
- نقش ۰۳ — Backend
- A — پیش از MS-01 (به ترتیب اولویت)
- Tribal Gamification API Contract (proposal)
- پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها
- format_jalali
- نقش ۰۱ — Product / Business Analyst
- نقش ۰۲ — Solution Architect
- نقش ۰۵ — QA
- پلی‌بوک — موتور امتیاز و قوانین
- نقش ۰۴ — Frontend / Mobile
- نقش ۰۶ — DevOps
- sqlite3
- 3. Recipes
- Runbook (prototype)
- پلی‌بوک — ورود داده فروش (Sales Import)
- روزشمار
- نقش ۰۷ — Integrator / Lead
- Database ERD & Schema (prototype)
- Sales Quest Arena — Backend-for-Frontend Alignment
- Tribal Gamification — Architecture and Two-Agent Plan
- سناریوی دمو — MS-01
- پلی‌بوک — برش عمودی (Vertical Slice)
- 03 — Deliver
- Knowledge Graph
- 3. Target architecture
- csrf_token
- game_progress
- leaderboard
- Agent Guide
- ۳. مسیر اصلی
- Admin Panel Specification (prototype)
- UX/UI Specification (prototype)
- QA & Test Strategy (prototype)
- 01 — Start
- Product Strategy & Scope (پروژه Kiloos Club)
- مستندات پروژه Kiloos Club
- Technical Design (prototype)
- 1. Shared contract
- migrations/README.md
- scoring-rule-matrix.md

## God Nodes (most connected - your core abstractions)
1. `Settings` - 103 edges
2. `create_app()` - 95 edges
3. `login()` - 75 edges
4. `users` - 51 edges
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

## Communities (67 total, 4 thin omitted)

### Community 0 - "Settings"
Cohesion: 0.06
Nodes (106): Settings, admin_mission_new(), admin_missions(), admin_queue(), admin_sales(), sample_workbook_bytes(), audit_logs, point_transactions (+98 more)

### Community 1 - "repo.py"
Cohesion: 0.05
Nodes (88): ۶. الگوی پیام commit / PR, admin_decide(), admin_mission_archive(), admin_mission_create(), admin_mission_publish(), admin_mission_update(), admin_review(), admin_sale_detail() (+80 more)

### Community 2 - "game.py"
Cohesion: 0.10
Nodes (53): _all_missions(), bootstrap(), catalog(), _clean_answers(), _collect_flags(), complete_mission(), _daily_mission(), _date_diff() (+45 more)

### Community 3 - "users"
Cohesion: 0.07
Nodes (41): evidence_file(), purge_evidence(), evidence(), list_queue(), score_event_detail(), _id(), _iso(), seed_demo() (+33 more)

### Community 4 - "MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18"
Cohesion: 0.10
Nodes (27): ۱۰. تحویل و فازها, MASTER_PROMPT — پرامپت آماده برای شروع هر ایجنت, نسخه انگلیسی (برای ابزارهای انگلیسی‌زبان), نسخه فارسی (کپی کن), چطور این را به ابزارهای مختلف بدهیم, fallbackها (اگر عقب افتادی), اصل حاکم, سناریوی دمو (۷ دقیقه) (+19 more)

### Community 5 - "sales.py"
Cohesion: 0.12
Nodes (18): admin_sales_new(), admin_sales_sample(), admin_sales_upload(), render_error(), sales_page_context(), _decimal(), _duplicate(), _invalid() (+10 more)

### Community 6 - "create_app"
Cohesion: 0.13
Nodes (23): create_app(), admin_mission_edit(), admin_reverse_score(), admin_sales_process(), demo_login(), game_demo_login(), game_logout(), hardening() (+15 more)

### Community 7 - "main.py"
Cohesion: 0.12
Nodes (7): make_token(), read_token(), _sign(), _unsign(), _decode_cursor(), _encode_cursor(), list_units()

### Community 8 - "AGENTS.md — اپراتور مهندسی Kiloos Club"
Cohesion: 0.08
Nodes (25): AGENTS.md — اپراتور مهندسی Kiloos Club, B — Build, D — Decide, H — Handoff, L — Locate, P — Prove, R — Read, S — Slice (+17 more)

### Community 9 - "test_game_api.py"
Cohesion: 0.20
Nodes (22): game_complete_mission(), game_demo_users(), game_history(), GET /api/v1/game/bootstrap, GET /api/v1/game/demo-users, GET /api/v1/game/history, POST /api/v1/game/demo-login, POST /api/v1/game/logout (+14 more)

### Community 10 - "D-001 — استفاده از FastAPI + SQLite برای Prototype"
Cohesion: 0.10
Nodes (19): 2026-11-09 — Demo hardening — [PR #5](https://github.com/iciiex/comu-center/pull/5), 2026-11-09 — Kiloos Club prototype — [PR #4](https://github.com/iciiex/comu-center/pull/4), 2026-11-09 — Score corrections — [PR #6](https://github.com/iciiex/comu-center/pull/6), Before Kiloos Club, Changelog, [Unreleased], 3. Queries, Architecture Decision Records (+11 more)

### Community 11 - "OD-04 — فرمول امتیاز فروش"
Cohesion: 0.28
Nodes (21): ۱۴. تصمیم‌های باز (خلاصه — جزئیات در `context/open-decisions.seed.json`), تصمیم‌های پیش‌فرض قابل بازگشت (ASSUMPTION), D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه), OD-02 — ساختار سازمانی, OD-03 — نمونه فایل فروش, OD-04 — فرمول امتیاز فروش, OD-05 — SKUهای هدف, OD-06 — اعتبارسنجی مأموریت (+13 more)

### Community 12 - "OD-01 — روش ورود"
Cohesion: 0.12
Nodes (21): D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو), OD-01 — روش ورود, Admin (admin only), API Specification (implemented surface), CSRF, Error codes (domain layer), Known gaps, Public (+13 more)

### Community 13 - "سند تحویل پروژه Kiloos Club (Handover)"
Cohesion: 0.10
Nodes (21): Changes made, Context read, Contract changes, Decisions and assumptions, Files changed, Recommended next step, Remaining work, Risks / blockers (+13 more)

### Community 14 - "OD-12 — ظرفیت"
Cohesion: 0.11
Nodes (18): ADR-0001: FastAPI + SQLite for the prototype, Consequences, Context, Decision, Follow-up, Options, Before any real user, Deployment Architecture (+10 more)

### Community 15 - "config.py"
Cohesion: 0.16
Nodes (5): _int_env(), main(), build_sample_workbook(), main(), R5 — Add a setting

### Community 16 - "seed.py"
Cohesion: 0.15
Nodes (7): apply_migrations(), connect(), init_db(), now_iso(), _audit(), main(), R3 — Change the schema

### Community 17 - "D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE"
Cohesion: 0.16
Nodes (18): 2026-11-09 — Sales import — [PR #7](https://github.com/iciiex/comu-center/pull/7), 4. Commit and pull request, D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE, OD-11 — یکپارچگی, Delivered after the prototype window, Authorization rules, Dedupe, Demo (+10 more)

### Community 19 - "current_user"
Cohesion: 0.16
Nodes (15): conn_dep(), require_admin(), require_api_user(), require_staff(), require_user(), root(), LoginRequired, current_user() (+7 more)

### Community 20 - "C — تکمیل MVP (پس از تأیید مسیر؛ به ترتیب پیشنهادی)"
Cohesion: 0.20
Nodes (15): داخل محدوده, sales_user_map(), Known gaps, C — تکمیل MVP (پس از تأیید مسیر؛ به ترتیب پیشنهادی), جزئیات A8 — اسناد کهنه یا متناقض, Contract (SAMPLE), In progress, Sales import (admin) (+7 more)

### Community 21 - "test_hardening.py"
Cohesion: 0.17
Nodes (12): health(), csrf_for(), 2026-11-11 — Documentation, agent guide and knowledge graph — [PR #8](https://github.com/iciiex/comu-center/pull/8), EP-01 — Auth & User Mgmt, MVP-01 — احراز هویت, GET /health, GET /home, test_cookie_session_still_works() (+4 more)

### Community 22 - "D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه)"
Cohesion: 0.13
Nodes (14): 5. Invariants you must not break, D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه), Contract, Corrections (reversal events) — D-004, Explainability, Not implemented (explicit), Rule selection, Sales records — SAMPLE per-amount rule (+6 more)

### Community 23 - "CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club"
Cohesion: 0.13
Nodes (15): CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club, MoSCoW, خارج از محدوده (در MVP نه), ۱. محصول در یک نگاه, ۱۱. KPI (همه پیشنهادی — نه تعهد), ۱۲. NFR, ۱۳. گزینه‌های فناوری (تأییدنشده — `OPEN`), ۱۵. واژه‌نامه (+7 more)

### Community 24 - "Implementation status (engineering judgement, 2026-11-11)"
Cohesion: 0.22
Nodes (15): ۵. قوانین کسب‌وکار (BR) — خلاصه اجرایی, روز ۳ — ۲۰ آبان: مأموریت‌ها (خواندن), روز ۴ — ۲۱ آبان: ثبت submission + شواهد, مأموریت و submission, پرده ۱ — ویزیتور مأموریت را انجام می‌دهد (سارا), POST /missions/{id}/submissions, Visitor, ۴. چه چیزی تحویل می‌شود (+7 more)

### Community 25 - "test_docs.py"
Cohesion: 0.16
Nodes (9): 1. Setup and tooling, 2. Checks that fail, 4. Changing application code, 5. Sales import, 6. When the documents disagree with the code, Troubleshooting, load_tool(), test_code_map_lists_exactly_the_routes_the_app_serves() (+1 more)

### Community 26 - "نقش ۰۳ — Backend"
Cohesion: 0.14
Nodes (13): Definition of Done نقش, اشتباهات رایج, امتیاز, امنیت و دسترسی, داده فروش, قبل از شروع بخوان, قرارداد خروجی هر برش, قواعد سخت دامنه (+5 more)

### Community 27 - "A — پیش از MS-01 (به ترتیب اولویت)"
Cohesion: 0.18
Nodes (13): home(), score_page(), wallet_balance(), A — پیش از MS-01 (به ترتیب اولویت), جزئیات A10 — اسکن secret در CI, جزئیات A3 — وقت تهران, جزئیات A4 — سناریو و دوره نمونه, جزئیات A5 — شفافیت امتیاز (+5 more)

### Community 28 - "Tribal Gamification API Contract (proposal)"
Cohesion: 0.14
Nodes (14): 10. Contract review gates (before implementation), 2. Player and organization reads, 3. Campaigns and mission runs, 4. Review workload, 5. League and ranking reads, 6. Badges and achievements, 7. Admin/back-office APIs, 8. Proposed DTO outlines (+6 more)

### Community 29 - "پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها"
Cohesion: 0.15
Nodes (12): UI, داده, دسترسی و امنیت, صحت دامنه, قاعده ۳۰ ثانیه, پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها, کیفیت, ۱. چک‌لیست بازبینی PR (ترتیب اهمیت) (+4 more)

### Community 30 - "format_jalali"
Cohesion: 0.27
Nodes (6): format_jalali(), gregorian_to_jalali(), to_persian_digits(), test_digits(), test_formatting_uses_persian_digits(), test_known_dates()

### Community 31 - "نقش ۰۱ — Product / Business Analyst"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۱ — Product / Business Analyst (+3 more)

### Community 32 - "نقش ۰۲ — Solution Architect"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۲ — Solution Architect (+3 more)

### Community 33 - "نقش ۰۵ — QA"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, اولویت تست بر اساس ریسک, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل (+3 more)

### Community 34 - "پلی‌بوک — موتور امتیاز و قوانین"
Cohesion: 0.18
Nodes (10): پلی‌بوک — موتور امتیاز و قوانین, ۱. مدل ذهنی, ۲. قرارداد داده پیشنهادی, ۳. الگوریتم (اجباری), ۴. انواع محاسبه, ۵. idempotency — سه لایه, ۶. اصلاح، برگشت، محاسبه مجدد, ۷. تست طلایی (Golden Tests) (+2 more)

### Community 35 - "نقش ۰۴ — Frontend / Mobile"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, قبل از شروع بخوان, قرارداد خروجی هر صفحه, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۴ — Frontend / Mobile (+2 more)

### Community 36 - "نقش ۰۶ — DevOps"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, حداقل‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۶ — DevOps (+2 more)

### Community 37 - "sqlite3"
Cohesion: 0.25
Nodes (8): tribal_disabled_response(), tribal_org_unit(), tribal_org_units(), GET /api/v1/tribal/org-units, GET /api/v1/tribal/org-units/{unit_id}, _id(), test_org_units_api_is_gated_when_feature_is_off(), test_org_units_api_is_tenant_scoped_and_paginated()

### Community 38 - "3. Recipes"
Cohesion: 0.18
Nodes (11): 02 — Continue, 1. The loop, with this repository's commands, 3. Recipes, 4. Which document to update for which change, 5. Boundaries, R1 — Add a page, R2 — Add an action, R4 — Change scoring behaviour (+3 more)

### Community 39 - "Runbook (prototype)"
Cohesion: 0.18
Nodes (11): Backup (prototype), Common issues, Configuration (environment), Escalation, Evidence retention (manual, D-003), Health, Repository health and generated documents, Reset demo data (+3 more)

### Community 40 - "پلی‌بوک — ورود داده فروش (Sales Import)"
Cohesion: 0.20
Nodes (9): پلی‌بوک — ورود داده فروش (Sales Import), ۱. چرخه عمر Import, ۲. قرارداد ورودی (اولیه — `OPEN` تا دریافت فایل واقعی), ۳. اعتبارسنجی در دو سطح, ۴. ضدتکرار, ۵. پردازش, ۶. Reconciliation, ۷. چک‌لیست برش (+1 more)

### Community 41 - "روزشمار"
Cohesion: 0.22
Nodes (9): روز ۰ — ۲۷ آبان: تحویل, روز ۱ — ۱۸ آبان: اسکلت و قرارداد, روز ۲ — ۱۹ آبان: ورود + پوسته اپ, روز ۵ — ۲۲ آبان: پنل — صف بررسی, روز ۶ — ۲۳ آبان: موتور امتیاز, روز ۷ — ۲۴ آبان: کیف امتیاز + تاریخچه, روز ۸ — ۲۵ آبان: رتبه‌بندی + ورود داده فروش (نمایشی), روز ۹ — ۲۶ آبان: مدیریت مأموریت + صیقل دمو (+1 more)

### Community 42 - "نقش ۰۷ — Integrator / Lead"
Cohesion: 0.22
Nodes (8): Definition of Done نقش, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۷ — Integrator / Lead, پرامپت نقش (کپی), کارهای اصلی

### Community 43 - "Database ERD & Schema (prototype)"
Cohesion: 0.22
Nodes (6): Data rules, Database ERD & Schema (prototype), Migrations, Relations (macro), Sales import tables (0003), Why these constraints

### Community 44 - "Sales Quest Arena — Backend-for-Frontend Alignment"
Cohesion: 0.22
Nodes (9): Agreement for this integration, API contract (same-origin BFF), Completion request / response sketch, Delivery sequence / acceptance, Frontend facts and compatibility gap, Not decided / not included, Persistence boundary, Sales Quest Arena — Backend-for-Frontend Alignment (+1 more)

### Community 45 - "Tribal Gamification — Architecture and Two-Agent Plan"
Cohesion: 0.25
Nodes (8): 2. Current architecture and impact, 4. Conceptual ERD (proposal), 5. Frontend information architecture, 6. Two-agent implementation plan, 8. Still requires owner/product input before implementation, Backend (current prototype), Frontend (current public main), Tribal Gamification — Architecture and Two-Agent Plan

### Community 46 - "سناریوی دمو — MS-01"
Cohesion: 0.25
Nodes (8): سناریوی دمو — MS-01, ۱. آماده‌سازی صبح روز دمو, ۲. حساب‌های نمایشی, ۴. بخش اختیاری — اصلاح امتیاز (نگار), ۶. کارهایی که در دمو نباید انجام شود, ۷. اگر چیزی خراب شد, ۸. پرسش‌هایی که در همین جلسه باید از کارفرما گرفته شود, ۹. تمرین

### Community 47 - "پلی‌بوک — برش عمودی (Vertical Slice)"
Cohesion: 0.29
Nodes (6): پلی‌بوک — برش عمودی (Vertical Slice), ۱. برش را تعریف کن, ۲. قرارداد اول (Contract-first), ۳. ترتیب ساخت, ۴. معیار «تمام» برش, ۵. ضدالگوها

### Community 48 - "03 — Deliver"
Cohesion: 0.29
Nodes (7): 03 — Deliver, 1. Gate: run these and read the output, 2. Check the behaviour yourself, 3. Update the documents, 5. Hand off, 6. Final self-check, Statuses you may write

### Community 49 - "Knowledge Graph"
Cohesion: 0.29
Nodes (7): 1. What is in `graphify-out/`, 2. How it is built, and what that means for trust, 4. Scripting against `graph.json`, 5. Graph or generated map?, 6. Keeping it current, 7. Limits, Knowledge Graph

### Community 50 - "3. Target architecture"
Cohesion: 0.29
Nodes (7): 3.1 Configurable organization tree, 3.2 RBAC and data visibility, 3.3 Admin Excel ingestion and reference data, 3.4 Campaigns, missions and review, 3.5 Scoring, ranking and league, 3.6 Badges, flags, audit and feature flag, 3. Target architecture

### Community 51 - "csrf_token"
Cohesion: 0.40
Nodes (4): csrf_guard(), game_bootstrap(), csrf_token(), session_token()

### Community 52 - "game_progress"
Cohesion: 0.33
Nodes (6): game_progress(), Tables, 1. Product direction recorded, 7. Safety, scale and DoD, Sales Quest Arena BFF (prototype, separate game economy), GET /api/v1/game/progress

### Community 53 - "leaderboard"
Cohesion: 0.60
Nodes (5): leaderboard_page(), active_competition(), leaderboard(), BR-008 — رتبه‌بندی بر امتیازهای معتبر در بازه مشخص؛ امتیاز لغوشده/اصلاح‌شده درست محاسبه شود, MVP-09 — رتبه‌بندی

### Community 54 - "Agent Guide"
Cohesion: 0.33
Nodes (6): Agent Guide, Commands you will use, Find anything, Keeping this guide true, Lookup files, The three phases

### Community 55 - "۳. مسیر اصلی"
Cohesion: 0.33
Nodes (6): پرده ۲ — اپراتور بررسی می‌کند (حسین), پرده ۳ — امتیاز قابل توضیح (سارا), پرده ۴ — مدیر امتیاز مأموریت را عوض می‌کند (نگار), پرده ۵ — ورود داده فروش (نگار), پرده ۶ — نتیجه برای ویزیتور (سارا), ۳. مسیر اصلی

### Community 56 - "Admin Panel Specification (prototype)"
Cohesion: 0.33
Nodes (5): Access model, Admin Panel Specification (prototype), Implemented, Not implemented, Open

### Community 57 - "UX/UI Specification (prototype)"
Cohesion: 0.33
Nodes (5): Gaps, Implemented, Next, UX rules applied, UX/UI Specification (prototype)

### Community 58 - "QA & Test Strategy (prototype)"
Cohesion: 0.33
Nodes (5): Commands, Implemented automated coverage (71 tests on 2026-11-12), Not covered yet, QA & Test Strategy (prototype), Rule

### Community 59 - "01 — Start"
Cohesion: 0.40
Nodes (5): 01 — Start, 1. Read in this order, 2. Set up and verify, 3. Layout, 7. Where to go next

### Community 60 - "Product Strategy & Scope (پروژه Kiloos Club)"
Cohesion: 0.40
Nodes (4): Product Strategy & Scope (پروژه Kiloos Club), آخرین تطبیق, خلاصه قابل اتکا, قاعده

### Community 61 - "مستندات پروژه Kiloos Club"
Cohesion: 0.40
Nodes (4): شروع، ادامه و تحویل (راهنمای ایجنت), قواعد, مستندات پروژه Kiloos Club, منبع اصلی

### Community 62 - "Technical Design (prototype)"
Cohesion: 0.50
Nodes (3): Design rules in code, Gaps, Technical Design (prototype)

### Community 63 - "1. Shared contract"
Cohesion: 0.50
Nodes (4): 1. Shared contract, Authentication and security, Common resource conventions, Common response/error format

## Knowledge Gaps
- **5 isolated node(s):** `EP-13 — QA`, `GET /`, `DELETE /api/v1/game/missions/{mission_id}/draft`, `PUT /api/v1/game/missions/{mission_id}/draft`, `PATCH /api/v1/game/profile`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 414 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `create_app` to `Settings`, `repo.py`, `game.py`, `users`, `sales.py`, `sqlite3`, `main.py`, `test_game_api.py`, `config.py`, `seed.py`, `current_user`, `csrf_token`, `game_progress`, `test_hardening.py`, `leaderboard`, `test_docs.py`, `A — پیش از MS-01 (به ترتیب اولویت)`, `format_jalali`?**
  _High betweenness centrality (0.160) - this node is a cross-community bridge._
- **Are the 87 inferred relationships involving `Settings` (e.g. with `create_app()` and `main()`) actually correct?**
  _`Settings` has 87 INFERRED edges - model-reasoned connections that need verification._
- **What connects `EP-13 — QA`, `GET /`, `DELETE /api/v1/game/missions/{mission_id}/draft` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Settings` be split into smaller, more focused modules?**
  _Cohesion score 0.05655280585569885 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `repo.py`, `game.py`, `users`, `create_app`, `main.py`, `test_game_api.py`, `D-001 — استفاده از FastAPI + SQLite برای Prototype`, `config.py`, `seed.py`, `current_user`, `test_hardening.py`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `create_app()` (e.g. with `Settings` and `to_persian_digits()`) actually correct?**
  _`create_app()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `repo.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05297385178160141 - nodes in this community are weakly interconnected._
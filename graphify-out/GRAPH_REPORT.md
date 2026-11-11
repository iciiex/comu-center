# Graph Report - kiloos-club  (2026-11-11)

## Corpus Check
- 71 files · ~54,965 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 972 nodes · 2635 edges · 59 communities (55 shown, 4 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 329 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Settings
- repo.py
- score_events
- seed_demo
- test_sales.py
- main.py
- AGENTS.md — اپراتور مهندسی Kiloos Club
- create_app
- base.html
- OD-04 — فرمول امتیاز فروش
- MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18
- sales.py
- D-001 — استفاده از FastAPI + SQLite برای Prototype
- OD-01 — روش ورود
- MVP-04 — مدیریت مأموریت (تعریف/انتشار)
- BR-001 — نمایش مأموریت فقط با: وضعیت Active + داخل بازه زمانی + عضویت در جامعه هدف + عدم نقض محدودیت دسترسی
- D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE
- CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club
- Implementation status (engineering judgement, 2026-11-11)
- current_user
- test_docs.py
- نقش ۰۳ — Backend
- پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها
- format_jalali
- نقش ۰۱ — Product / Business Analyst
- نقش ۰۲ — Solution Architect
- نقش ۰۵ — QA
- A — پیش از MS-01 (به ترتیب اولویت)
- پلی‌بوک — موتور امتیاز و قوانین
- نقش ۰۴ — Frontend / Mobile
- نقش ۰۶ — DevOps
- سند تحویل پروژه Kiloos Club (Handover)
- Runbook (prototype)
- C — تکمیل MVP (پس از تأیید مسیر؛ به ترتیب پیشنهادی)
- ۱۰. تحویل و فازها
- پلی‌بوک — ورود داده فروش (Sales Import)
- ۱۲. بلوک handoff همین نشست
- نقش ۰۷ — Integrator / Lead
- سناریوی دمو — MS-01
- Scoring Engine (prototype)
- پلی‌بوک — برش عمودی (Vertical Slice)
- 03 — Deliver
- Knowledge Graph
- Current Project State
- پلی‌بوک — ۹ روز تا Prototype (MS-01)
- Agent Guide
- ۳. مسیر اصلی
- Admin Panel Specification (prototype)
- UX/UI Specification (prototype)
- QA & Test Strategy (prototype)
- 01 — Start
- Product Strategy & Scope (پروژه Kiloos Club)
- مستندات پروژه Kiloos Club
- Kiloos Club — Prototype
- Changelog
- Product Requirements Document (working copy)
- scoring-rule-matrix.md

## God Nodes (most connected - your core abstractions)
1. `Settings` - 74 edges
2. `create_app()` - 69 edges
3. `login()` - 44 edges
4. `score_events` - 37 edges
5. `users` - 34 edges
6. `post()` - 32 edges
7. `page()` - 29 edges
8. `missions` - 29 edges
9. `submissions` - 29 edges
10. `D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE` - 28 edges

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

## Communities (59 total, 4 thin omitted)

### Community 0 - "Settings"
Cohesion: 0.06
Nodes (68): _int_env(), Settings, connect(), csrf_guard(), health(), logout(), main(), purge_evidence() (+60 more)

### Community 1 - "repo.py"
Cohesion: 0.09
Nodes (53): admin_review(), admin_sale_detail(), evidence_file(), submission_page(), submit_mission(), render_error(), archive_mission(), audit() (+45 more)

### Community 2 - "score_events"
Cohesion: 0.08
Nodes (41): ۶. الگوی پیام commit / PR, _audit(), process_sales_import(), reverse_score_event(), award_mission_approval(), award_sales_record(), _existing(), find_rule_version() (+33 more)

### Community 3 - "seed_demo"
Cohesion: 0.06
Nodes (28): apply_migrations(), init_db(), now_iso(), _id(), _iso(), seed_demo(), competitions, Migrations (+20 more)

### Community 4 - "test_sales.py"
Cohesion: 0.17
Nodes (27): admin_sales_upload(), create_sales_import(), sales_external_ids(), ix_sales_records_import, sales_imports, sales_records, ux_sales_imports_fingerprint, ux_sales_records_external (+19 more)

### Community 5 - "main.py"
Cohesion: 0.11
Nodes (9): clear_session(), csrf_token(), CurrentUser, make_token(), read_token(), session_token(), set_session(), _sign() (+1 more)

### Community 6 - "AGENTS.md — اپراتور مهندسی Kiloos Club"
Cohesion: 0.08
Nodes (25): AGENTS.md — اپراتور مهندسی Kiloos Club, B — Build, D — Decide, H — Handoff, L — Locate, P — Prove, R — Read, S — Slice (+17 more)

### Community 7 - "create_app"
Cohesion: 0.16
Nodes (22): create_app(), admin_decide(), admin_reverse_score(), admin_sales_new(), admin_sales_process(), render_error(), demo_login(), go() (+14 more)

### Community 8 - "base.html"
Cohesion: 0.14
Nodes (15): admin_queue(), admin_sales(), mission_page(), missions_page(), EP-09 — Admin Panel, MVP-11 — پنل مدیریت, GET /admin/sales, GET /admin/sales/{import_id} (+7 more)

### Community 9 - "OD-04 — فرمول امتیاز فروش"
Cohesion: 0.25
Nodes (24): ۱۴. تصمیم‌های باز (خلاصه — جزئیات در `context/open-decisions.seed.json`), تصمیم‌های پیش‌فرض قابل بازگشت (ASSUMPTION), D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه), D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه), OD-02 — ساختار سازمانی, OD-03 — نمونه فایل فروش, OD-04 — فرمول امتیاز فروش, OD-05 — SKUهای هدف (+16 more)

### Community 10 - "MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18"
Cohesion: 0.11
Nodes (22): MASTER_PROMPT — پرامپت آماده برای شروع هر ایجنت, نسخه انگلیسی (برای ابزارهای انگلیسی‌زبان), نسخه فارسی (کپی کن), چطور این را به ابزارهای مختلف بدهیم, 3. Queries, Context, Options, Backlog و نقشه ادامه توسعه (+14 more)

### Community 11 - "sales.py"
Cohesion: 0.16
Nodes (11): _decimal(), _duplicate(), _invalid(), money_points(), parse_workbook(), _raw(), _row_status(), _sale_date() (+3 more)

### Community 12 - "D-001 — استفاده از FastAPI + SQLite برای Prototype"
Cohesion: 0.13
Nodes (21): 2026-11-09 — Kiloos Club prototype — [PR #4](https://github.com/iciiex/comu-center/pull/4), 5. Invariants you must not break, ADR-0001: FastAPI + SQLite for the prototype, Consequences, Decision, Follow-up, Architecture Decision Records, Template (+13 more)

### Community 13 - "OD-01 — روش ورود"
Cohesion: 0.13
Nodes (18): Before any real user, Deployment Architecture, Today, D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو), OD-01 — روش ورود, Admin (admin only), API Specification (implemented surface), CSRF (+10 more)

### Community 14 - "MVP-04 — مدیریت مأموریت (تعریف/انتشار)"
Cohesion: 0.18
Nodes (16): admin_mission_archive(), admin_mission_create(), admin_mission_edit(), admin_mission_new(), admin_mission_publish(), admin_mission_update(), admin_missions(), mission_by_id() (+8 more)

### Community 15 - "BR-001 — نمایش مأموریت فقط با: وضعیت Active + داخل بازه زمانی + عضویت در جامعه هدف + عدم نقض محدودیت دسترسی"
Cohesion: 0.13
Nodes (17): روز ۰ — ۲۷ آبان: تحویل, روز ۱ — ۱۸ آبان: اسکلت و قرارداد, روز ۲ — ۱۹ آبان: ورود + پوسته اپ, روز ۳ — ۲۰ آبان: مأموریت‌ها (خواندن), روز ۴ — ۲۱ آبان: ثبت submission + شواهد, روز ۵ — ۲۲ آبان: پنل — صف بررسی, روز ۶ — ۲۳ آبان: موتور امتیاز, روز ۷ — ۲۴ آبان: کیف امتیاز + تاریخچه (+9 more)

### Community 17 - "D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE"
Cohesion: 0.19
Nodes (15): 2026-11-09 — Sales import — [PR #7](https://github.com/iciiex/comu-center/pull/7), 4. Commit and pull request, D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE, Delivered after the prototype window, Authorization rules, Dedupe, Demo, Lifecycle (+7 more)

### Community 18 - "CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club"
Cohesion: 0.13
Nodes (15): CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club, MoSCoW, خارج از محدوده (در MVP نه), ۱. محصول در یک نگاه, ۱۱. KPI (همه پیشنهادی — نه تعهد), ۱۲. NFR, ۱۳. گزینه‌های فناوری (تأییدنشده — `OPEN`), ۱۵. واژه‌نامه (+7 more)

### Community 19 - "Implementation status (engineering judgement, 2026-11-11)"
Cohesion: 0.29
Nodes (15): ۵. قوانین کسب‌وکار (BR) — خلاصه اجرایی, home(), leaderboard_page(), active_competition(), leaderboard(), wallet_balance(), Implementation status (engineering judgement, 2026-11-11), BR-006 — رد فعالیت: وضعیت Rejected + ثبت دلیل + بدون امتیاز (+7 more)

### Community 20 - "current_user"
Cohesion: 0.20
Nodes (12): conn_dep(), require_admin(), require_staff(), require_user(), LoginRequired, current_user(), 4. How a request flows, 2.1 A page (GET) (+4 more)

### Community 21 - "test_docs.py"
Cohesion: 0.16
Nodes (9): 1. Setup and tooling, 2. Checks that fail, 4. Changing application code, 5. Sales import, 6. When the documents disagree with the code, Troubleshooting, load_tool(), test_code_map_lists_exactly_the_routes_the_app_serves() (+1 more)

### Community 22 - "نقش ۰۳ — Backend"
Cohesion: 0.14
Nodes (13): Definition of Done نقش, اشتباهات رایج, امتیاز, امنیت و دسترسی, داده فروش, قبل از شروع بخوان, قرارداد خروجی هر برش, قواعد سخت دامنه (+5 more)

### Community 23 - "پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها"
Cohesion: 0.15
Nodes (12): UI, داده, دسترسی و امنیت, صحت دامنه, قاعده ۳۰ ثانیه, پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها, کیفیت, ۱. چک‌لیست بازبینی PR (ترتیب اهمیت) (+4 more)

### Community 24 - "format_jalali"
Cohesion: 0.27
Nodes (6): format_jalali(), gregorian_to_jalali(), to_persian_digits(), test_digits(), test_formatting_uses_persian_digits(), test_known_dates()

### Community 25 - "نقش ۰۱ — Product / Business Analyst"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۱ — Product / Business Analyst (+3 more)

### Community 26 - "نقش ۰۲ — Solution Architect"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۲ — Solution Architect (+3 more)

### Community 27 - "نقش ۰۵ — QA"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, اولویت تست بر اساس ریسک, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل (+3 more)

### Community 28 - "A — پیش از MS-01 (به ترتیب اولویت)"
Cohesion: 0.18
Nodes (11): score_page(), A — پیش از MS-01 (به ترتیب اولویت), جزئیات A10 — اسکن secret در CI, جزئیات A2 — اصلاح امتیاز, جزئیات A3 — وقت تهران, جزئیات A4 — سناریو و دوره نمونه, جزئیات A5 — شفافیت امتیاز, جزئیات A6 — ریزه‌کاری‌ها (+3 more)

### Community 29 - "پلی‌بوک — موتور امتیاز و قوانین"
Cohesion: 0.18
Nodes (10): پلی‌بوک — موتور امتیاز و قوانین, ۱. مدل ذهنی, ۲. قرارداد داده پیشنهادی, ۳. الگوریتم (اجباری), ۴. انواع محاسبه, ۵. idempotency — سه لایه, ۶. اصلاح، برگشت، محاسبه مجدد, ۷. تست طلایی (Golden Tests) (+2 more)

### Community 30 - "نقش ۰۴ — Frontend / Mobile"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, قبل از شروع بخوان, قرارداد خروجی هر صفحه, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۴ — Frontend / Mobile (+2 more)

### Community 31 - "نقش ۰۶ — DevOps"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, حداقل‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۶ — DevOps (+2 more)

### Community 32 - "سند تحویل پروژه Kiloos Club (Handover)"
Cohesion: 0.18
Nodes (11): OD-11 — یکپارچگی, Not implemented (explicit), سند تحویل پروژه Kiloos Club (Handover), ۱۰. تاریخچه کوتاه, ۱۱. آنچه این سند تضمین نمی‌کند, ۲. از کجا شروع کنم, ۳. اجرا و راستی‌آزمایی, ۵. نقص‌ها و ریسک‌های شناخته‌شده (+3 more)

### Community 33 - "Runbook (prototype)"
Cohesion: 0.18
Nodes (11): Backup (prototype), Common issues, Configuration (environment), Escalation, Evidence retention (manual, D-003), Health, Repository health and generated documents, Reset demo data (+3 more)

### Community 34 - "C — تکمیل MVP (پس از تأیید مسیر؛ به ترتیب پیشنهادی)"
Cohesion: 0.36
Nodes (10): داخل محدوده, Known gaps, C — تکمیل MVP (پس از تأیید مسیر؛ به ترتیب پیشنهادی), In progress, چه چیزی هنوز نیست (عمداً), EP-10 — Reports, EP-11 — Notification, MVP-02 — پروفایل کاربر (+2 more)

### Community 35 - "۱۰. تحویل و فازها"
Cohesion: 0.22
Nodes (10): ۱۰. تحویل و فازها, 2026-11-11 — Documentation, agent guide and knowledge graph, [Unreleased], ۴. چه چیزی تحویل می‌شود, EP-01 — Auth & User Mgmt, EP-02 — Organization, EP-05 — Verification, EP-08 — Competition & Leaderboard (+2 more)

### Community 36 - "پلی‌بوک — ورود داده فروش (Sales Import)"
Cohesion: 0.20
Nodes (9): پلی‌بوک — ورود داده فروش (Sales Import), ۱. چرخه عمر Import, ۲. قرارداد ورودی (اولیه — `OPEN` تا دریافت فایل واقعی), ۳. اعتبارسنجی در دو سطح, ۴. ضدتکرار, ۵. پردازش, ۶. Reconciliation, ۷. چک‌لیست برش (+1 more)

### Community 37 - "۱۲. بلوک handoff همین نشست"
Cohesion: 0.20
Nodes (10): Changes made, Context read, Contract changes, Decisions and assumptions, Files changed, Recommended next step, Remaining work, Risks / blockers (+2 more)

### Community 38 - "نقش ۰۷ — Integrator / Lead"
Cohesion: 0.22
Nodes (8): Definition of Done نقش, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۷ — Integrator / Lead, پرامپت نقش (کپی), کارهای اصلی

### Community 39 - "سناریوی دمو — MS-01"
Cohesion: 0.25
Nodes (8): سناریوی دمو — MS-01, ۱. آماده‌سازی صبح روز دمو, ۲. حساب‌های نمایشی, ۴. بخش اختیاری — اصلاح امتیاز (نگار), ۶. کارهایی که در دمو نباید انجام شود, ۷. اگر چیزی خراب شد, ۸. پرسش‌هایی که در همین جلسه باید از کارفرما گرفته شود, ۹. تمرین

### Community 40 - "Scoring Engine (prototype)"
Cohesion: 0.25
Nodes (7): Data written on approval (one transaction), Explainability, Not implemented (explicit), Rule selection, Sales records — SAMPLE per-amount rule, Scoring Engine (prototype), Test coverage (executed)

### Community 41 - "پلی‌بوک — برش عمودی (Vertical Slice)"
Cohesion: 0.29
Nodes (6): پلی‌بوک — برش عمودی (Vertical Slice), ۱. برش را تعریف کن, ۲. قرارداد اول (Contract-first), ۳. ترتیب ساخت, ۴. معیار «تمام» برش, ۵. ضدالگوها

### Community 42 - "03 — Deliver"
Cohesion: 0.29
Nodes (7): 03 — Deliver, 1. Gate: run these and read the output, 2. Check the behaviour yourself, 3. Update the documents, 5. Hand off, 6. Final self-check, Statuses you may write

### Community 43 - "Knowledge Graph"
Cohesion: 0.29
Nodes (7): 1. What is in `graphify-out/`, 2. How it is built, and what that means for trust, 4. Scripting against `graph.json`, 5. Graph or generated map?, 6. Keeping it current, 7. Limits, Knowledge Graph

### Community 44 - "Current Project State"
Cohesion: 0.29
Nodes (7): Current Project State, Decisions approved, Demo status, Important files and entry points, Known issues, Open decisions / assumptions, Tests and verification

### Community 45 - "پلی‌بوک — ۹ روز تا Prototype (MS-01)"
Cohesion: 0.33
Nodes (5): fallbackها (اگر عقب افتادی), اصل حاکم, سناریوی دمو (۷ دقیقه), پلی‌بوک — ۹ روز تا Prototype (MS-01), چک‌لیست «قابل نمایش»

### Community 46 - "Agent Guide"
Cohesion: 0.33
Nodes (6): Agent Guide, Commands you will use, Find anything, Keeping this guide true, Lookup files, The three phases

### Community 47 - "۳. مسیر اصلی"
Cohesion: 0.33
Nodes (6): پرده ۲ — اپراتور بررسی می‌کند (حسین), پرده ۳ — امتیاز قابل توضیح (سارا), پرده ۴ — مدیر امتیاز مأموریت را عوض می‌کند (نگار), پرده ۵ — ورود داده فروش (نگار), پرده ۶ — نتیجه برای ویزیتور (سارا), ۳. مسیر اصلی

### Community 48 - "Admin Panel Specification (prototype)"
Cohesion: 0.33
Nodes (5): Access model, Admin Panel Specification (prototype), Implemented, Not implemented, Open

### Community 49 - "UX/UI Specification (prototype)"
Cohesion: 0.33
Nodes (5): Gaps, Implemented, Next, UX rules applied, UX/UI Specification (prototype)

### Community 50 - "QA & Test Strategy (prototype)"
Cohesion: 0.33
Nodes (5): Commands, Implemented automated coverage (58 tests on 2026-11-11), Not covered yet, QA & Test Strategy (prototype), Rule

### Community 51 - "01 — Start"
Cohesion: 0.40
Nodes (5): 01 — Start, 1. Read in this order, 2. Set up and verify, 3. Layout, 7. Where to go next

### Community 52 - "Product Strategy & Scope (پروژه Kiloos Club)"
Cohesion: 0.40
Nodes (4): Product Strategy & Scope (پروژه Kiloos Club), آخرین تطبیق, خلاصه قابل اتکا, قاعده

### Community 53 - "مستندات پروژه Kiloos Club"
Cohesion: 0.40
Nodes (4): شروع، ادامه و تحویل (راهنمای ایجنت), قواعد, مستندات پروژه Kiloos Club, منبع اصلی

### Community 54 - "Kiloos Club — Prototype"
Cohesion: 0.40
Nodes (4): Kiloos Club — Prototype, ایمنی داده, ساختار, مستندات

### Community 55 - "Changelog"
Cohesion: 0.50
Nodes (4): 2026-11-09 — Demo hardening — [PR #5](https://github.com/iciiex/comu-center/pull/5), 2026-11-09 — Score corrections — [PR #6](https://github.com/iciiex/comu-center/pull/6), Before Kiloos Club, Changelog

## Knowledge Gaps
- **2 isolated node(s):** `EP-13 — QA`, `GET /`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 367 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `create_app` to `Settings`, `repo.py`, `seed_demo`, `test_sales.py`, `main.py`, `base.html`, `MVP-04 — مدیریت مأموریت (تعریف/انتشار)`, `Implementation status (engineering judgement, 2026-11-11)`, `current_user`, `test_docs.py`, `format_jalali`, `A — پیش از MS-01 (به ترتیب اولویت)`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Are the 61 inferred relationships involving `Settings` (e.g. with `create_app()` and `main()`) actually correct?**
  _`Settings` has 61 INFERRED edges - model-reasoned connections that need verification._
- **What connects `EP-13 — QA`, `GET /` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Settings` be split into smaller, more focused modules?**
  _Cohesion score 0.06048906048906049 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `repo.py`, `score_events`, `seed_demo`, `test_sales.py`, `main.py`, `create_app`, `MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18`, `current_user`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `create_app()` (e.g. with `Settings` and `to_persian_digits()`) actually correct?**
  _`create_app()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `repo.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08530020703933748 - nodes in this community are weakly interconnected._
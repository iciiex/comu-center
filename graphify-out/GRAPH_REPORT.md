# Graph Report - kiloos-club  (2026-11-12)

## Corpus Check
- 72 files · ~58,910 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1004 nodes · 2933 edges · 61 communities (54 shown, 7 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 389 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Settings
- repo.py
- main.py
- create_app
- score_events
- OD-01 — روش ورود
- MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18
- AGENTS.md — اپراتور مهندسی Kiloos Club
- OD-04 — فرمول امتیاز فروش
- D-001 — استفاده از FastAPI + SQLite برای Prototype
- sales.py
- D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE
- CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club
- test_docs.py
- A — پیش از MS-01 (به ترتیب اولویت)
- نقش ۰۳ — Backend
- seed_demo
- پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها
- format_jalali
- نقش ۰۱ — Product / Business Analyst
- نقش ۰۲ — Solution Architect
- نقش ۰۵ — QA
- maintenance.py
- پلی‌بوک — موتور امتیاز و قوانین
- نقش ۰۴ — Frontend / Mobile
- نقش ۰۶ — DevOps
- db.py
- Runbook (prototype)
- داخل محدوده
- Implementation status (engineering judgement, 2026-11-11)
- پلی‌بوک — ورود داده فروش (Sales Import)
- ۱۲. بلوک handoff همین نشست
- روزشمار
- نقش ۰۷ — Integrator / Lead
- Scoring Engine (prototype)
- BR-001 — نمایش مأموریت فقط با: وضعیت Active + داخل بازه زمانی + عضویت در جامعه هدف + عدم نقض محدودیت دسترسی
- سناریوی دمو — MS-01
- Current Project State
- config.py
- 3. Recipes
- 03 — Deliver
- Knowledge Graph
- Database ERD & Schema (prototype)
- پلی‌بوک — ۹ روز تا Prototype (MS-01)
- sample_sales.py
- Agent Guide
- ۳. مسیر اصلی
- Admin Panel Specification (prototype)
- UX/UI Specification (prototype)
- QA & Test Strategy (prototype)
- Changelog
- 01 — Start
- Product Strategy & Scope (پروژه Kiloos Club)
- مستندات پروژه Kiloos Club
- Kiloos Club — Prototype
- 02 — Continue
- Product Requirements Document (working copy)
- migrations/README.md
- scoring-rule-matrix.md

## God Nodes (most connected - your core abstractions)
1. `Settings` - 88 edges
2. `create_app()` - 71 edges
3. `login()` - 57 edges
4. `post()` - 46 edges
5. `score_events` - 46 edges
6. `users` - 38 edges
7. `missions` - 35 edges
8. `submissions` - 35 edges
9. `row_id()` - 31 edges
10. `test_demo_script_main_path_and_optional_correction()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `2.6 A test` --references--> `Settings`  [INFERRED]
  docs/agent-guide/02-continue.md → app/config.py
- `R2 — Add an action` --references--> `DomainError`  [INFERRED]
  docs/agent-guide/02-continue.md → app/repo.py
- `روز ۱ — ۱۸ آبان: اسکلت و قرارداد` --references--> `submission_evidences()`  [INFERRED]
  .agent/playbooks/prototype-9-days.md → app/repo.py
- `Tables` --references--> `submission_evidences()`  [INFERRED]
  docs/architecture/database-erd.md → app/repo.py
- `4. Changing application code` --references--> `score_event_detail()`  [INFERRED]
  docs/agent-guide/troubleshooting.md → app/repo.py

## Import Cycles
- None detected.

## Communities (61 total, 7 thin omitted)

### Community 0 - "Settings"
Cohesion: 0.08
Nodes (85): Settings, admin_sales(), admin_sales_sample(), sample_workbook_bytes(), ux_score_events_corrects, sales_imports, ux_sales_imports_fingerprint, جزئیات A2 — اصلاح امتیاز (DONE 2026-11-12) (+77 more)

### Community 1 - "repo.py"
Cohesion: 0.08
Nodes (62): admin_review(), admin_sale_detail(), evidence_file(), home(), submission_page(), submit_mission(), render_error(), active_competition() (+54 more)

### Community 2 - "main.py"
Cohesion: 0.05
Nodes (44): csrf_guard(), demo_login(), logout(), require_admin(), require_staff(), require_user(), LoginRequired, clear_session() (+36 more)

### Community 3 - "create_app"
Cohesion: 0.06
Nodes (56): create_app(), admin_decide(), admin_mission_archive(), admin_mission_create(), admin_mission_edit(), admin_mission_new(), admin_mission_publish(), admin_mission_update() (+48 more)

### Community 4 - "score_events"
Cohesion: 0.08
Nodes (42): پلی‌بوک — برش عمودی (Vertical Slice), ۱. برش را تعریف کن, ۲. قرارداد اول (Contract-first), ۳. ترتیب ساخت, ۴. معیار «تمام» برش, ۵. ضدالگوها, ۶. الگوی پیام commit / PR, award_mission_approval() (+34 more)

### Community 5 - "OD-01 — روش ورود"
Cohesion: 0.08
Nodes (30): Before any real user, Deployment Architecture, Today, D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو), OD-01 — روش ورود, OD-11 — یکپارچگی, Admin (admin only), API Specification (implemented surface) (+22 more)

### Community 6 - "MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18"
Cohesion: 0.11
Nodes (23): ۱۰. تحویل و فازها, MASTER_PROMPT — پرامپت آماده برای شروع هر ایجنت, نسخه انگلیسی (برای ابزارهای انگلیسی‌زبان), نسخه فارسی (کپی کن), چطور این را به ابزارهای مختلف بدهیم, Context, Options, راهنما (+15 more)

### Community 7 - "AGENTS.md — اپراتور مهندسی Kiloos Club"
Cohesion: 0.08
Nodes (25): AGENTS.md — اپراتور مهندسی Kiloos Club, B — Build, D — Decide, H — Handoff, L — Locate, P — Prove, R — Read, S — Slice (+17 more)

### Community 8 - "OD-04 — فرمول امتیاز فروش"
Cohesion: 0.26
Nodes (23): ۱۴. تصمیم‌های باز (خلاصه — جزئیات در `context/open-decisions.seed.json`), تصمیم‌های پیش‌فرض قابل بازگشت (ASSUMPTION), 3. Queries, D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه), D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه), OD-02 — ساختار سازمانی, OD-03 — نمونه فایل فروش, OD-04 — فرمول امتیاز فروش (+15 more)

### Community 9 - "D-001 — استفاده از FastAPI + SQLite برای Prototype"
Cohesion: 0.13
Nodes (20): 2026-11-09 — Kiloos Club prototype — [PR #4](https://github.com/iciiex/comu-center/pull/4), 5. Invariants you must not break, ADR-0001: FastAPI + SQLite for the prototype, Consequences, Decision, Follow-up, Architecture Decision Records, Template (+12 more)

### Community 10 - "sales.py"
Cohesion: 0.17
Nodes (11): _decimal(), _duplicate(), _invalid(), money_points(), parse_workbook(), _raw(), _row_status(), _sale_date() (+3 more)

### Community 11 - "D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE"
Cohesion: 0.14
Nodes (18): 2026-11-09 — Sales import — [PR #7](https://github.com/iciiex/comu-center/pull/7), ix_sales_records_import, ux_sales_records_external, 4. Commit and pull request, D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE, Delivered after the prototype window, Authorization rules, Contract (SAMPLE) (+10 more)

### Community 13 - "CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club"
Cohesion: 0.13
Nodes (15): CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club, MoSCoW, خارج از محدوده (در MVP نه), ۱. محصول در یک نگاه, ۱۱. KPI (همه پیشنهادی — نه تعهد), ۱۲. NFR, ۱۳. گزینه‌های فناوری (تأییدنشده — `OPEN`), ۱۵. واژه‌نامه (+7 more)

### Community 14 - "test_docs.py"
Cohesion: 0.16
Nodes (9): 1. Setup and tooling, 2. Checks that fail, 4. Changing application code, 5. Sales import, 6. When the documents disagree with the code, Troubleshooting, load_tool(), test_code_map_lists_exactly_the_routes_the_app_serves() (+1 more)

### Community 15 - "A — پیش از MS-01 (به ترتیب اولویت)"
Cohesion: 0.13
Nodes (14): A — پیش از MS-01 (به ترتیب اولویت), Backlog و نقشه ادامه توسعه, D — Harden (فقط پس از ثبت P→H؛ تا RC), جزئیات A10 — اسکن secret در CI, جزئیات A3 — وقت تهران, جزئیات A4 — سناریو و دوره نمونه, جزئیات A5 — شفافیت امتیاز, جزئیات A6 — ریزه‌کاری‌ها (۴ مورد DONE 2026-11-12؛ مورد ۵ باز) (+6 more)

### Community 16 - "نقش ۰۳ — Backend"
Cohesion: 0.14
Nodes (13): Definition of Done نقش, اشتباهات رایج, امتیاز, امنیت و دسترسی, داده فروش, قبل از شروع بخوان, قرارداد خروجی هر برش, قواعد سخت دامنه (+5 more)

### Community 17 - "seed_demo"
Cohesion: 0.22
Nodes (8): init_db(), _id(), _iso(), main(), seed_demo(), competitions, organizations, sales_user_map

### Community 18 - "پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها"
Cohesion: 0.15
Nodes (12): UI, داده, دسترسی و امنیت, صحت دامنه, قاعده ۳۰ ثانیه, پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها, کیفیت, ۱. چک‌لیست بازبینی PR (ترتیب اهمیت) (+4 more)

### Community 19 - "format_jalali"
Cohesion: 0.27
Nodes (6): format_jalali(), gregorian_to_jalali(), to_persian_digits(), test_digits(), test_formatting_uses_persian_digits(), test_known_dates()

### Community 20 - "نقش ۰۱ — Product / Business Analyst"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۱ — Product / Business Analyst (+3 more)

### Community 21 - "نقش ۰۲ — Solution Architect"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۲ — Solution Architect (+3 more)

### Community 22 - "نقش ۰۵ — QA"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, اولویت تست بر اساس ریسک, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل (+3 more)

### Community 23 - "maintenance.py"
Cohesion: 0.23
Nodes (3): _audit(), main(), purge_evidence()

### Community 24 - "پلی‌بوک — موتور امتیاز و قوانین"
Cohesion: 0.18
Nodes (10): پلی‌بوک — موتور امتیاز و قوانین, ۱. مدل ذهنی, ۲. قرارداد داده پیشنهادی, ۳. الگوریتم (اجباری), ۴. انواع محاسبه, ۵. idempotency — سه لایه, ۶. اصلاح، برگشت، محاسبه مجدد, ۷. تست طلایی (Golden Tests) (+2 more)

### Community 25 - "نقش ۰۴ — Frontend / Mobile"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, قبل از شروع بخوان, قرارداد خروجی هر صفحه, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۴ — Frontend / Mobile (+2 more)

### Community 26 - "نقش ۰۶ — DevOps"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, حداقل‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۶ — DevOps (+2 more)

### Community 27 - "db.py"
Cohesion: 0.22
Nodes (5): apply_migrations(), connect(), now_iso(), R3 — Change the schema, Migrations

### Community 28 - "Runbook (prototype)"
Cohesion: 0.18
Nodes (11): Backup (prototype), Common issues, Configuration (environment), Escalation, Evidence retention (manual, D-003), Health, Repository health and generated documents, Reset demo data (+3 more)

### Community 29 - "داخل محدوده"
Cohesion: 0.31
Nodes (10): داخل محدوده, Known gaps, In progress, ۴. چه چیزی تحویل می‌شود, چه چیزی هنوز نیست (عمداً), EP-10 — Reports, EP-11 — Notification, MVP-02 — پروفایل کاربر (+2 more)

### Community 30 - "Implementation status (engineering judgement, 2026-11-11)"
Cohesion: 0.40
Nodes (10): ۵. قوانین کسب‌وکار (BR) — خلاصه اجرایی, C — تکمیل MVP (پس از تأیید مسیر؛ به ترتیب پیشنهادی), Implementation status (engineering judgement, 2026-11-11), BR-006 — رد فعالیت: وضعیت Rejected + ثبت دلیل + بدون امتیاز, BR-007 — امتیاز فروش با قوانین قابل تنظیم؛ فرمول دقیق `OPEN` (OD-04), BR-008 — رتبه‌بندی بر امتیازهای معتبر در بازه مشخص؛ امتیاز لغوشده/اصلاح‌شده درست محاسبه شود, BR-012 — کاربر غیرفعال نمی‌تواند مأموریت جدید ثبت کند؛ سوابق و امتیاز حفظ می‌شود, BR-013 — هر رقابت: جامعه هدف + بازه زمانی + معیار رتبه‌بندی مشخص (+2 more)

### Community 31 - "پلی‌بوک — ورود داده فروش (Sales Import)"
Cohesion: 0.20
Nodes (9): پلی‌بوک — ورود داده فروش (Sales Import), ۱. چرخه عمر Import, ۲. قرارداد ورودی (اولیه — `OPEN` تا دریافت فایل واقعی), ۳. اعتبارسنجی در دو سطح, ۴. ضدتکرار, ۵. پردازش, ۶. Reconciliation, ۷. چک‌لیست برش (+1 more)

### Community 32 - "۱۲. بلوک handoff همین نشست"
Cohesion: 0.20
Nodes (10): Changes made, Context read, Contract changes, Decisions and assumptions, Files changed, Recommended next step, Remaining work, Risks / blockers (+2 more)

### Community 33 - "روزشمار"
Cohesion: 0.22
Nodes (9): روز ۰ — ۲۷ آبان: تحویل, روز ۱ — ۱۸ آبان: اسکلت و قرارداد, روز ۲ — ۱۹ آبان: ورود + پوسته اپ, روز ۵ — ۲۲ آبان: پنل — صف بررسی, روز ۶ — ۲۳ آبان: موتور امتیاز, روز ۷ — ۲۴ آبان: کیف امتیاز + تاریخچه, روز ۸ — ۲۵ آبان: رتبه‌بندی + ورود داده فروش (نمایشی), روز ۹ — ۲۶ آبان: مدیریت مأموریت + صیقل دمو (+1 more)

### Community 34 - "نقش ۰۷ — Integrator / Lead"
Cohesion: 0.22
Nodes (8): Definition of Done نقش, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۷ — Integrator / Lead, پرامپت نقش (کپی), کارهای اصلی

### Community 35 - "Scoring Engine (prototype)"
Cohesion: 0.22
Nodes (8): Corrections (reversal events) — D-004, Explainability, Not implemented (explicit), Rule selection, Rules that are still `SAMPLE`, Sales records — SAMPLE per-amount rule, Scoring Engine (prototype), Test coverage (executed)

### Community 36 - "BR-001 — نمایش مأموریت فقط با: وضعیت Active + داخل بازه زمانی + عضویت در جامعه هدف + عدم نقض محدودیت دسترسی"
Cohesion: 0.29
Nodes (8): روز ۳ — ۲۰ آبان: مأموریت‌ها (خواندن), روز ۴ — ۲۱ آبان: ثبت submission + شواهد, مأموریت و submission, پرده ۱ — ویزیتور مأموریت را انجام می‌دهد (سارا), POST /missions/{id}/submissions, Visitor, BR-001 — نمایش مأموریت فقط با: وضعیت Active + داخل بازه زمانی + عضویت در جامعه هدف + عدم نقض محدودیت دسترسی, BR-002 — ثبت فعالیت فقط با: مأموریت فعال + کاربر واجد شرایط + عدم عبور از سقف تعداد + تکمیل اطلاعات الزامی

### Community 37 - "سناریوی دمو — MS-01"
Cohesion: 0.25
Nodes (8): سناریوی دمو — MS-01, ۱. آماده‌سازی صبح روز دمو, ۲. حساب‌های نمایشی, ۴. بخش اختیاری — اصلاح امتیاز (نگار), ۶. کارهایی که در دمو نباید انجام شود, ۷. اگر چیزی خراب شد, ۸. پرسش‌هایی که در همین جلسه باید از کارفرما گرفته شود, ۹. تمرین

### Community 38 - "Current Project State"
Cohesion: 0.25
Nodes (8): Current Project State, Decisions approved, Demo status, Important files and entry points, Known issues, Next recommended tasks, Open decisions / assumptions, Recent migrations / API changes

### Community 40 - "3. Recipes"
Cohesion: 0.29
Nodes (7): 3. Recipes, R1 — Add a page, R2 — Add an action, R4 — Change scoring behaviour, R6 — Record a decision or an open question, R7 — Fix a defect from the backlog, R8 — Keep the map and the traceability current

### Community 41 - "03 — Deliver"
Cohesion: 0.29
Nodes (7): 03 — Deliver, 1. Gate: run these and read the output, 2. Check the behaviour yourself, 3. Update the documents, 5. Hand off, 6. Final self-check, Statuses you may write

### Community 42 - "Knowledge Graph"
Cohesion: 0.29
Nodes (7): 1. What is in `graphify-out/`, 2. How it is built, and what that means for trust, 4. Scripting against `graph.json`, 5. Graph or generated map?, 6. Keeping it current, 7. Limits, Knowledge Graph

### Community 43 - "Database ERD & Schema (prototype)"
Cohesion: 0.29
Nodes (6): Data rules, Database ERD & Schema (prototype), Relations (macro), Sales import tables (0003), Tables, Why these constraints

### Community 44 - "پلی‌بوک — ۹ روز تا Prototype (MS-01)"
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
Nodes (5): Commands, Implemented automated coverage (71 tests on 2026-11-12), Not covered yet, QA & Test Strategy (prototype), Rule

### Community 51 - "Changelog"
Cohesion: 0.40
Nodes (5): 2026-11-09 — Demo hardening — [PR #5](https://github.com/iciiex/comu-center/pull/5), 2026-11-09 — Score corrections — [PR #6](https://github.com/iciiex/comu-center/pull/6), Before Kiloos Club, Changelog, [Unreleased]

### Community 52 - "01 — Start"
Cohesion: 0.40
Nodes (5): 01 — Start, 1. Read in this order, 2. Set up and verify, 3. Layout, 7. Where to go next

### Community 53 - "Product Strategy & Scope (پروژه Kiloos Club)"
Cohesion: 0.40
Nodes (4): Product Strategy & Scope (پروژه Kiloos Club), آخرین تطبیق, خلاصه قابل اتکا, قاعده

### Community 54 - "مستندات پروژه Kiloos Club"
Cohesion: 0.40
Nodes (4): شروع، ادامه و تحویل (راهنمای ایجنت), قواعد, مستندات پروژه Kiloos Club, منبع اصلی

### Community 55 - "Kiloos Club — Prototype"
Cohesion: 0.40
Nodes (4): Kiloos Club — Prototype, ایمنی داده, ساختار, مستندات

### Community 56 - "02 — Continue"
Cohesion: 0.50
Nodes (4): 02 — Continue, 1. The loop, with this repository's commands, 4. Which document to update for which change, 5. Boundaries

## Knowledge Gaps
- **2 isolated node(s):** `EP-13 — QA`, `GET /`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 371 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Settings` to `main.py`, `create_app`, `score_events`, `config.py`, `OD-04 — فرمول امتیاز فروش`, `seed_demo`, `maintenance.py`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Are the 74 inferred relationships involving `Settings` (e.g. with `create_app()` and `main()`) actually correct?**
  _`Settings` has 74 INFERRED edges - model-reasoned connections that need verification._
- **What connects `EP-13 — QA`, `GET /` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Settings` be split into smaller, more focused modules?**
  _Cohesion score 0.07887109077040427 - nodes in this community are weakly interconnected._
- **Why does `create_app()` connect `create_app` to `Settings`, `repo.py`, `main.py`, `config.py`, `test_docs.py`, `seed_demo`, `format_jalali`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `create_app()` (e.g. with `Settings` and `to_persian_digits()`) actually correct?**
  _`create_app()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `repo.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07647058823529412 - nodes in this community are weakly interconnected._
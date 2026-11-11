# Graph Report - kiloos-club  (2026-11-11)

## Corpus Check
- 71 files · ~55,054 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 972 nodes · 2635 edges · 52 communities (49 shown, 3 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 329 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- repo.py
- Settings
- Implementation status (engineering judgement, 2026-11-11)
- main.py
- test_sales.py
- base.html
- MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18
- apply_migrations
- D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE
- AGENTS.md — اپراتور مهندسی Kiloos Club
- OD-01 — روش ورود
- sales.py
- current_user
- D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو)
- روزشمار
- create_app
- MVP-04 — مدیریت مأموریت (تعریف/انتشار)
- page
- D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه)
- نقش ۰۳ — Backend
- test_docs.py
- پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها
- نقش ۰۱ — Product / Business Analyst
- نقش ۰۲ — Solution Architect
- نقش ۰۵ — QA
- sales_user_map
- پلی‌بوک — موتور امتیاز و قوانین
- نقش ۰۴ — Frontend / Mobile
- نقش ۰۶ — DevOps
- MS-03 — MVP Dev — پس از تأیید مسیر
- پلی‌بوک — ورود داده فروش (Sales Import)
- ۱۲. بلوک handoff همین نشست
- نقش ۰۷ — Integrator / Lead
- سناریوی دمو — MS-01
- سند تحویل پروژه Kiloos Club (Handover)
- پلی‌بوک — برش عمودی (Vertical Slice)
- 03 — Deliver
- Knowledge Graph
- ۳. مسیر اصلی
- Kiloos Club — Prototype
- Agent Guide
- Solution Architecture (prototype)
- Admin Panel Specification (prototype)
- UX/UI Specification (prototype)
- QA & Test Strategy (prototype)
- 01 — Start
- Product Strategy & Scope (پروژه Kiloos Club)
- مستندات پروژه Kiloos Club
- Technical Design (prototype)
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

## Communities (52 total, 3 thin omitted)

### Community 0 - "repo.py"
Cohesion: 0.05
Nodes (89): ۶. الگوی پیام commit / PR, admin_review(), admin_sale_detail(), evidence_file(), submission_page(), submit_mission(), render_error(), archive_mission() (+81 more)

### Community 1 - "Settings"
Cohesion: 0.06
Nodes (64): _int_env(), Settings, connect(), health(), main(), purge_evidence(), build_sample_workbook(), main() (+56 more)

### Community 2 - "Implementation status (engineering judgement, 2026-11-11)"
Cohesion: 0.06
Nodes (62): CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club, MoSCoW, خارج از محدوده (در MVP نه), داخل محدوده, ۱. محصول در یک نگاه, ۱۰. تحویل و فازها, ۱۱. KPI (همه پیشنهادی — نه تعهد), ۱۲. NFR (+54 more)

### Community 3 - "main.py"
Cohesion: 0.07
Nodes (16): init_db(), format_jalali(), gregorian_to_jalali(), to_persian_digits(), CurrentUser, make_token(), read_token(), _sign() (+8 more)

### Community 4 - "test_sales.py"
Cohesion: 0.17
Nodes (27): admin_sales_upload(), create_sales_import(), sales_external_ids(), ix_sales_records_import, sales_imports, sales_records, ux_sales_imports_fingerprint, ux_sales_records_external (+19 more)

### Community 5 - "base.html"
Cohesion: 0.11
Nodes (20): admin_decide(), admin_missions(), admin_queue(), admin_sales(), mission_page(), missions_page(), score_page(), EP-09 — Admin Panel (+12 more)

### Community 6 - "MS-01 — Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18"
Cohesion: 0.11
Nodes (27): MASTER_PROMPT — پرامپت آماده برای شروع هر ایجنت, نسخه انگلیسی (برای ابزارهای انگلیسی‌زبان), نسخه فارسی (کپی کن), چطور این را به ابزارهای مختلف بدهیم, 2026-11-09 — Kiloos Club prototype — [PR #4](https://github.com/iciiex/comu-center/pull/4), 5. Invariants you must not break, ADR-0001: FastAPI + SQLite for the prototype, Consequences (+19 more)

### Community 7 - "apply_migrations"
Cohesion: 0.07
Nodes (24): apply_migrations(), now_iso(), _audit(), Migrations, 02 — Continue, 1. The loop, with this repository's commands, 3. Recipes, 4. Which document to update for which change (+16 more)

### Community 8 - "D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE"
Cohesion: 0.12
Nodes (26): 2026-11-09 — Demo hardening — [PR #5](https://github.com/iciiex/comu-center/pull/5), 2026-11-09 — Sales import — [PR #7](https://github.com/iciiex/comu-center/pull/7), 2026-11-09 — Score corrections — [PR #6](https://github.com/iciiex/comu-center/pull/6), 2026-11-11 — Documentation, agent guide and knowledge graph — [PR #8](https://github.com/iciiex/comu-center/pull/8), Before Kiloos Club, Changelog, [Unreleased], 4. Commit and pull request (+18 more)

### Community 9 - "AGENTS.md — اپراتور مهندسی Kiloos Club"
Cohesion: 0.08
Nodes (25): AGENTS.md — اپراتور مهندسی Kiloos Club, B — Build, D — Decide, H — Handoff, L — Locate, P — Prove, R — Read, S — Slice (+17 more)

### Community 10 - "OD-01 — روش ورود"
Cohesion: 0.25
Nodes (24): ۱۴. تصمیم‌های باز (خلاصه — جزئیات در `context/open-decisions.seed.json`), تصمیم‌های پیش‌فرض قابل بازگشت (ASSUMPTION), OD-01 — روش ورود, OD-02 — ساختار سازمانی, OD-03 — نمونه فایل فروش, OD-04 — فرمول امتیاز فروش, OD-05 — SKUهای هدف, OD-06 — اعتبارسنجی مأموریت (+16 more)

### Community 11 - "sales.py"
Cohesion: 0.16
Nodes (11): _decimal(), _duplicate(), _invalid(), money_points(), parse_workbook(), _raw(), _row_status(), _sale_date() (+3 more)

### Community 12 - "current_user"
Cohesion: 0.16
Nodes (16): conn_dep(), go(), require_admin(), require_staff(), require_user(), root(), url_session(), LoginRequired (+8 more)

### Community 13 - "D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو)"
Cohesion: 0.12
Nodes (16): Before any real user, Deployment Architecture, Today, D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو), Admin (admin only), API Specification (implemented surface), CSRF, Error codes (domain layer) (+8 more)

### Community 14 - "روزشمار"
Cohesion: 0.12
Nodes (16): fallbackها (اگر عقب افتادی), اصل حاکم, روز ۰ — ۲۷ آبان: تحویل, روز ۱ — ۱۸ آبان: اسکلت و قرارداد, روز ۲ — ۱۹ آبان: ورود + پوسته اپ, روز ۳ — ۲۰ آبان: مأموریت‌ها (خواندن), روز ۴ — ۲۱ آبان: ثبت submission + شواهد, روز ۵ — ۲۲ آبان: پنل — صف بررسی (+8 more)

### Community 16 - "create_app"
Cohesion: 0.19
Nodes (11): create_app(), csrf_guard(), demo_login(), login_rate_limited(), logout(), url(), with_token(), clear_session() (+3 more)

### Community 17 - "MVP-04 — مدیریت مأموریت (تعریف/انتشار)"
Cohesion: 0.20
Nodes (14): admin_mission_archive(), admin_mission_create(), admin_mission_edit(), admin_mission_new(), admin_mission_publish(), admin_mission_update(), mission_by_id(), MVP-04 — مدیریت مأموریت (تعریف/انتشار) (+6 more)

### Community 18 - "page"
Cohesion: 0.18
Nodes (14): admin_reverse_score(), admin_sales_new(), admin_sales_process(), render_error(), hardening(), home(), _http_error(), login_page() (+6 more)

### Community 19 - "D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه)"
Cohesion: 0.13
Nodes (16): D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه), Decision Log, تصمیم‌های ثبت‌شده, قالب, Known issues, Backup (prototype), Common issues, Configuration (environment) (+8 more)

### Community 20 - "نقش ۰۳ — Backend"
Cohesion: 0.13
Nodes (14): Definition of Done نقش, اشتباهات رایج, امتیاز, امنیت و دسترسی, داده فروش, قبل از شروع بخوان, قرارداد خروجی هر برش, قواعد سخت دامنه (+6 more)

### Community 21 - "test_docs.py"
Cohesion: 0.16
Nodes (9): 1. Setup and tooling, 2. Checks that fail, 4. Changing application code, 5. Sales import, 6. When the documents disagree with the code, Troubleshooting, load_tool(), test_code_map_lists_exactly_the_routes_the_app_serves() (+1 more)

### Community 22 - "پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها"
Cohesion: 0.15
Nodes (12): UI, داده, دسترسی و امنیت, صحت دامنه, قاعده ۳۰ ثانیه, پلی‌بوک — بازبینی، ادغام و تحویل بین ایجنت‌ها, کیفیت, ۱. چک‌لیست بازبینی PR (ترتیب اهمیت) (+4 more)

### Community 23 - "نقش ۰۱ — Product / Business Analyst"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۱ — Product / Business Analyst (+3 more)

### Community 24 - "نقش ۰۲ — Solution Architect"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۲ — Solution Architect (+3 more)

### Community 25 - "نقش ۰۵ — QA"
Cohesion: 0.17
Nodes (11): Definition of Done نقش, اشتباهات رایج, اولویت تست بر اساس ریسک, خروجی‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل (+3 more)

### Community 26 - "sales_user_map"
Cohesion: 0.17
Nodes (10): sales_user_map(), Contract (SAMPLE), Dedupe, Demo, Lifecycle, Reconciliation (shown on the detail page), Row outcomes, Sales Import (EP-07) — implemented slice (+2 more)

### Community 27 - "پلی‌بوک — موتور امتیاز و قوانین"
Cohesion: 0.18
Nodes (10): پلی‌بوک — موتور امتیاز و قوانین, ۱. مدل ذهنی, ۲. قرارداد داده پیشنهادی, ۳. الگوریتم (اجباری), ۴. انواع محاسبه, ۵. idempotency — سه لایه, ۶. اصلاح، برگشت، محاسبه مجدد, ۷. تست طلایی (Golden Tests) (+2 more)

### Community 28 - "نقش ۰۴ — Frontend / Mobile"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, قبل از شروع بخوان, قرارداد خروجی هر صفحه, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۴ — Frontend / Mobile (+2 more)

### Community 29 - "نقش ۰۶ — DevOps"
Cohesion: 0.18
Nodes (10): Definition of Done نقش, اشتباهات رایج, حداقل‌های الزامی, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۶ — DevOps (+2 more)

### Community 30 - "MS-03 — MVP Dev — پس از تأیید مسیر"
Cohesion: 0.24
Nodes (10): راهنما, Cut from the 9-day plan, Execution Plan (working), Milestones, Next, Prototype scope delivered, ۱. پروژه در یک نگاه, MS-03 — MVP Dev — پس از تأیید مسیر (+2 more)

### Community 31 - "پلی‌بوک — ورود داده فروش (Sales Import)"
Cohesion: 0.20
Nodes (9): پلی‌بوک — ورود داده فروش (Sales Import), ۱. چرخه عمر Import, ۲. قرارداد ورودی (اولیه — `OPEN` تا دریافت فایل واقعی), ۳. اعتبارسنجی در دو سطح, ۴. ضدتکرار, ۵. پردازش, ۶. Reconciliation, ۷. چک‌لیست برش (+1 more)

### Community 32 - "۱۲. بلوک handoff همین نشست"
Cohesion: 0.20
Nodes (10): Changes made, Context read, Contract changes, Decisions and assumptions, Files changed, Recommended next step, Remaining work, Risks / blockers (+2 more)

### Community 33 - "نقش ۰۷ — Integrator / Lead"
Cohesion: 0.22
Nodes (8): Definition of Done نقش, قبل از شروع بخوان, قواعد این نقش, مأموریت, مالکیت فایل, نقش ۰۷ — Integrator / Lead, پرامپت نقش (کپی), کارهای اصلی

### Community 34 - "سناریوی دمو — MS-01"
Cohesion: 0.25
Nodes (8): سناریوی دمو — MS-01, ۱. آماده‌سازی صبح روز دمو, ۲. حساب‌های نمایشی, ۴. بخش اختیاری — اصلاح امتیاز (نگار), ۶. کارهایی که در دمو نباید انجام شود, ۷. اگر چیزی خراب شد, ۸. پرسش‌هایی که در همین جلسه باید از کارفرما گرفته شود, ۹. تمرین

### Community 35 - "سند تحویل پروژه Kiloos Club (Handover)"
Cohesion: 0.25
Nodes (8): سند تحویل پروژه Kiloos Club (Handover), ۱۰. تاریخچه کوتاه, ۱۱. آنچه این سند تضمین نمی‌کند, ۲. از کجا شروع کنم, ۳. اجرا و راستی‌آزمایی, ۵. نقص‌ها و ریسک‌های شناخته‌شده, ۷. قدم‌های بعدی به ترتیب پیشنهادی, ۹. ابزارهای نگهداری دانش

### Community 36 - "پلی‌بوک — برش عمودی (Vertical Slice)"
Cohesion: 0.29
Nodes (6): پلی‌بوک — برش عمودی (Vertical Slice), ۱. برش را تعریف کن, ۲. قرارداد اول (Contract-first), ۳. ترتیب ساخت, ۴. معیار «تمام» برش, ۵. ضدالگوها

### Community 37 - "03 — Deliver"
Cohesion: 0.29
Nodes (7): 03 — Deliver, 1. Gate: run these and read the output, 2. Check the behaviour yourself, 3. Update the documents, 5. Hand off, 6. Final self-check, Statuses you may write

### Community 38 - "Knowledge Graph"
Cohesion: 0.29
Nodes (7): 1. What is in `graphify-out/`, 2. How it is built, and what that means for trust, 4. Scripting against `graph.json`, 5. Graph or generated map?, 6. Keeping it current, 7. Limits, Knowledge Graph

### Community 39 - "۳. مسیر اصلی"
Cohesion: 0.29
Nodes (7): پرده ۱ — ویزیتور مأموریت را انجام می‌دهد (سارا), پرده ۲ — اپراتور بررسی می‌کند (حسین), پرده ۳ — امتیاز قابل توضیح (سارا), پرده ۴ — مدیر امتیاز مأموریت را عوض می‌کند (نگار), پرده ۵ — ورود داده فروش (نگار), پرده ۶ — نتیجه برای ویزیتور (سارا), ۳. مسیر اصلی

### Community 40 - "Kiloos Club — Prototype"
Cohesion: 0.29
Nodes (6): Kiloos Club — Prototype, اجرا, ایمنی داده, حساب‌های نمایشی, ساختار, مستندات

### Community 41 - "Agent Guide"
Cohesion: 0.33
Nodes (6): Agent Guide, Commands you will use, Find anything, Keeping this guide true, Lookup files, The three phases

### Community 42 - "Solution Architecture (prototype)"
Cohesion: 0.33
Nodes (5): Domain boundaries kept, Explicit non-decisions, Implemented shape, Next, Solution Architecture (prototype)

### Community 43 - "Admin Panel Specification (prototype)"
Cohesion: 0.33
Nodes (5): Access model, Admin Panel Specification (prototype), Implemented, Not implemented, Open

### Community 44 - "UX/UI Specification (prototype)"
Cohesion: 0.33
Nodes (5): Gaps, Implemented, Next, UX rules applied, UX/UI Specification (prototype)

### Community 45 - "QA & Test Strategy (prototype)"
Cohesion: 0.33
Nodes (5): Commands, Implemented automated coverage (58 tests on 2026-11-11), Not covered yet, QA & Test Strategy (prototype), Rule

### Community 46 - "01 — Start"
Cohesion: 0.40
Nodes (5): 01 — Start, 1. Read in this order, 2. Set up and verify, 3. Layout, 7. Where to go next

### Community 47 - "Product Strategy & Scope (پروژه Kiloos Club)"
Cohesion: 0.40
Nodes (4): Product Strategy & Scope (پروژه Kiloos Club), آخرین تطبیق, خلاصه قابل اتکا, قاعده

### Community 48 - "مستندات پروژه Kiloos Club"
Cohesion: 0.40
Nodes (4): شروع، ادامه و تحویل (راهنمای ایجنت), قواعد, مستندات پروژه Kiloos Club, منبع اصلی

### Community 49 - "Technical Design (prototype)"
Cohesion: 0.50
Nodes (3): Design rules in code, Gaps, Technical Design (prototype)

## Knowledge Gaps
- **2 isolated node(s):** `EP-13 — QA`, `GET /`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 368 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `create_app` to `repo.py`, `Settings`, `Implementation status (engineering judgement, 2026-11-11)`, `main.py`, `test_sales.py`, `base.html`, `current_user`, `MVP-04 — مدیریت مأموریت (تعریف/انتشار)`, `page`, `test_docs.py`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Are the 61 inferred relationships involving `Settings` (e.g. with `create_app()` and `main()`) actually correct?**
  _`Settings` has 61 INFERRED edges - model-reasoned connections that need verification._
- **What connects `EP-13 — QA`, `GET /` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `repo.py` be split into smaller, more focused modules?**
  _Cohesion score 0.053548387096774196 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `Settings` to `repo.py`, `main.py`, `test_sales.py`, `D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE`, `current_user`, `create_app`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `create_app()` (e.g. with `Settings` and `to_persian_digits()`) actually correct?**
  _`create_app()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `Settings` be split into smaller, more focused modules?**
  _Cohesion score 0.06317064728279681 - nodes in this community are weakly interconnected._
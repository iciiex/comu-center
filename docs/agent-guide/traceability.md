# Traceability

> **GENERATED** by `.agent/tools/knowledge_map.py` — do not edit by hand.
> Regenerate with `make docs` (or `python3 .agent/tools/knowledge_map.py`).
> `tests/test_docs.py` fails when this file no longer matches the code.

Which requirement lives where: every `MVP-xx`, `BR-xxx`, `EP-xx`, `OD-xx`, `D-xxx`, `ADR`
and `MS` id, the code that implements it, the tests that check it and the documents that
mention it.

Two sources feed this file:

1. **Curated links** in `.agent/context/traceability.json` — written by an agent after reading the code
   (last reviewed 2026-11-11). The generator verifies that every
   symbol named there still exists, so a rename breaks the check instead of leaving a
   stale row.
2. **Automatic scan** of ids written in code, tests, templates, migrations and markdown.

**State is implementation state, not approval.** `implemented` · `partial` ·
`demo-only` · `sample` · `missing`. Nothing in this file is `APPROVED`; only
`docs/decisions/decision-log.md` can approve a decision (`AGENTS.md` §3).

## 1. MVP scope

| ID | Title | State | Code | Tests | Gaps and notes | Backlog |
|---|---|---|---|---|---|---|
| **MVP-01** | احراز هویت | demo-only | `main.csrf_guard`, `main.demo_login`, `main.login_page`, `main.logout`, `security.current_user`, `security.make_token`, `security.read_token` | `test_flow::test_login_page_lists_demo_users`, `test_hardening::test_cookie_session_still_works`, `test_hardening::test_expired_token_is_rejected`, `test_hardening::test_login_is_rate_limited`, `test_hardening::test_session_token_in_url_works_without_cookies` | Demo user picker without credentials (OD-01 open). Signed token, expiry, CSRF and role checks are real. Demo login is not disabled outside dev/test, and a `?s=` link keeps working after logout. | B2, C9 |
| **MVP-02** | پروفایل کاربر | missing | — | — | No profile route or page. Only the user's name and role appear in the header of `base.html`. | C7 |
| **MVP-03** | داشبورد کاربر (امتیاز، مأموریت، پیشرفت) | implemented | `app/templates/home.html`, `main.home`, `repo.leaderboard`, `repo.list_active_missions`, `repo.list_user_submissions`, `repo.wallet_balance` | `test_hardening::test_cookie_session_still_works` | Balance, rank, active missions and the last three submissions. No progress-to-target view. Times are shown in UTC, not Asia/Tehran. | A3, A5 |
| **MVP-04** | مدیریت مأموریت (تعریف/انتشار) | implemented | `main.admin_mission_archive`, `main.admin_mission_create`, `main.admin_mission_publish`, `main.admin_mission_update`, `main.admin_missions`, `repo.archive_mission`, `repo.create_mission`, `repo.publish_mission`, `repo.update_mission` | `test_flow::test_mission_edit_publishes_new_rule_version`, `test_flow::test_visitors_and_operators_have_no_admin_powers` | One mission type (photo), organization-wide audience, Gregorian date input read as UTC day bounds. Changing only the date window does not move the rule version's `effective_from`. | A1, A3 |
| **MVP-05** | ثبت فعالیت + شواهد | implemented | `main.evidence_file`, `main.submission_page`, `main.submit_mission`, `repo.create_submission`, `repo.evidence` | `test_flow::test_duplicate_request_id_is_idempotent`, `test_flow::test_full_flow_approval_scores_once`, `test_flow::test_mission_respects_max_per_user`, `test_hardening::test_forged_csrf_upload_creates_nothing` | Type and size are checked from the client-declared content type only; identical images are not flagged; a replayed or over-cap submit leaves an orphan file on disk. | C5 |
| **MVP-06** | تأیید/رد فعالیت | implemented | `main.admin_decide`, `main.admin_queue`, `main.admin_review`, `repo.list_queue`, `repo.review_submission` | `test_flow::test_approve_redirect_keeps_queue_filter`, `test_flow::test_full_flow_approval_scores_once`, `test_flow::test_reject_requires_reason_and_awards_nothing`, `test_hardening::test_admin_queue_paginates` | Status change and score award are two separate transactions: approval can end as `approved` with no score event. Staff can approve their own submission. | A1, C6 |
| **MVP-07** | موتور امتیازدهی | implemented | `scoring._persist_award`, `scoring.award_mission_approval`, `scoring.award_sales_record`, `scoring.find_rule_version`, `scoring.reverse_event` | `test_scoring::test_active_rule_version_selection_after_retirement`, `test_scoring::test_award_is_idempotent`, `test_scoring::test_event_has_traceable_explain`, `test_scoring::test_wallet_matches_ledger` | Two calculations exist: `fixed` (mission) and `per_unit_amount` (sales, SAMPLE). All point values are SAMPLE. `float` is used in the reversal path. | C8 |
| **MVP-08** | ورود داده فروش از فایل | sample | `main.admin_sale_detail`, `main.admin_sales_process`, `main.admin_sales_upload`, `repo.create_sales_import`, `repo.process_sales_import`, `sales.parse_workbook`, `sales.validate_rows` | `test_sales::test_process_creates_each_score_once`, `test_sales::test_processing_failure_rolls_back_all_events`, `test_sales::test_row_errors_do_not_block_valid_rows`, `test_sales::test_upload_validates_without_scoring` | XLSX only, SAMPLE column contract and SAMPLE formula (OD-03, OD-04). The detail page shows the first 200 rows only; a Jalali date is read as a Gregorian year. | B4, C4, C10 |
| **MVP-09** | رتبه‌بندی | partial | `main.leaderboard_page`, `repo.active_competition`, `repo.leaderboard` | `test_corrections::test_leaderboard_reflects_the_correction` | Individual ranking in the active period, computed on read, top 50 only (a user below 50 gets no rank). The period exists only in the seed. | A4, C2 |
| **MVP-10** | رقابت گروهی | missing | — | — | No team concept in the schema or the code. | B3, C11 |
| **MVP-11** | پنل مدیریت | partial | `app/templates/base.html`, `main.admin_missions`, `main.admin_queue`, `main.admin_sales` | `test_flow::test_visitors_and_operators_have_no_admin_powers`, `test_sales::test_only_admin_can_use_sales_import` | Three sections exist: review queue, missions, sales import. No users, organization, competitions, reports, permissions or settings. Score correction has no link from the panel. | A2, A6, C1, C2, C3 |
| **MVP-12** | گزارش عملکرد پایه | missing | — | — | No report and no CSV export. | C3 |
| **MVP-13** | تاریخچه امتیازات | implemented | `app/templates/score.html`, `main.score_page`, `repo.score_history` | `test_corrections::test_reversal_creates_negative_event_and_fixes_projections`, `test_flow::test_full_flow_approval_scores_once` | Last 30 events with a correction marker. Rows link nowhere, and sales points have no explanation view. | A5 |

## 2. Business rules

| ID | Title | State | Code | Tests | Gaps and notes | Backlog |
|---|---|---|---|---|---|---|
| **BR-001** | نمایش مأموریت فقط با: وضعیت Active + داخل بازه زمانی + عضویت در جامعه هدف + عدم نقض محدودیت دسترسی | partial | `repo.get_mission_for_user`, `repo.list_active_missions` | `test_flow::test_mission_window_and_status_filtering` | Status, date window and organization are enforced. Target-audience membership is not: every mission is organization-wide (no `mission_audiences` table). | B3 |
| **BR-002** | ثبت فعالیت فقط با: مأموریت فعال + کاربر واجد شرایط + عدم عبور از سقف تعداد + تکمیل اطلاعات الزامی | implemented | `main.submit_mission`, `repo.create_submission` | `test_flow::test_duplicate_request_id_is_idempotent`, `test_flow::test_mission_respects_max_per_user` | A rejected attempt also consumes the per-user cap (question B6-1, not yet a registered open decision). | B6 |
| **BR-003** | امتیاز فقط پس از تحقق شرایط معتبر؛ برای مأموریت نیازمند بررسی، پس از تأیید | implemented | `repo.review_submission`, `scoring.award_mission_approval` | `test_flow::test_full_flow_approval_scores_once`, `test_flow::test_reject_requires_reason_and_awards_nothing` | Holds on the tested path. When no rule version is effective the submission becomes `approved` with no score (HTTP 500). | A1 |
| **BR-004** | هر فعالیت شناسه یکتا دارد؛ برای یک فعالیت تأییدشده بیش از یک بار امتیاز ایجاد نمی‌شود | implemented | `db/migrations/0001_init.sql::ux_score_events_source`, `repo.create_submission`, `scoring.award_mission_approval` | `test_flow::test_full_flow_approval_scores_once`, `test_scoring::test_award_is_idempotent`, `test_scoring::test_seeded_approval_created_one_event` | Three layers: idempotency key `mission.approved:<id>`, a partial unique index, and the submission state machine. | — |
| **BR-005** | همه تغییرات امتیاز رویداد مستقل و append-only هستند؛ حذف/بازنویسی ممنوع، اصلاح با رویداد اصلاحی | implemented | `db/migrations/0002_score_corrections.sql::ux_score_events_corrects`, `main.admin_reverse_score`, `repo.reverse_score_event`, `scoring.reverse_event` | `test_corrections::test_a_correction_cannot_be_reversed`, `test_corrections::test_reversal_creates_negative_event_and_fixes_projections`, `test_corrections::test_second_reversal_is_rejected` | No UPDATE or DELETE on `score_events` anywhere in `app/`. Reversing a `sales_record` event returns 403, so sales points cannot be corrected yet. | A2, C8 |
| **BR-006** | رد فعالیت: وضعیت Rejected + ثبت دلیل + بدون امتیاز | implemented | `repo.review_submission` | `test_flow::test_reject_requires_reason_and_awards_nothing` | Reject without a reason is refused (`REASON_REQUIRED`, HTTP 409). | — |
| **BR-007** | امتیاز فروش با قوانین قابل تنظیم؛ فرمول دقیق `OPEN` (OD-04) | sample | `sales.money_points`, `scoring.award_sales_record` | `test_sales::test_amount_below_one_unit_scores_nothing`, `test_sales::test_process_creates_each_score_once` | `floor(amount / unit_size) * points`; both numbers are rows in `scoring_rule_versions`. The formula itself is SAMPLE until OD-04 is approved. | B4, C10 |
| **BR-008** | رتبه‌بندی بر امتیازهای معتبر در بازه مشخص؛ امتیاز لغوشده/اصلاح‌شده درست محاسبه شود | partial | `repo.active_competition`, `repo.leaderboard` | `test_corrections::test_leaderboard_reflects_the_correction` | The total is the algebraic sum of events inside the active period. A correction made after a period ends is subtracted from the current period. | B6, C8 |
| **BR-009** | تساوی امتیاز: tie-breaker — ترتیب پیشنهادی: امتیاز مأموریت‌های کلیدی ← زمان زودتر رسیدن ← معیار مصوب. **تأییدنشده** | partial | `app/templates/leaderboard.html`, `repo.leaderboard` | — | Temporary tie-break in SQL: total, then earliest first score, then name. The rule is not approved and no test covers it. | B3 |
| **BR-010** | فایل فروش: شناسه پردازش، گزارش رکورد نامعتبر، بدون امتیاز تکراری، قابل پیگیری، اصلاح با تاریخچه | partial | `db/migrations/0003_sales_import.sql::ux_sales_imports_fingerprint`, `db/migrations/0003_sales_import.sql::ux_sales_records_external`, `repo.create_sales_import`, `repo.process_sales_import`, `sales.validate_rows` | `test_sales::test_detail_page_shows_reconciliation`, `test_sales::test_duplicate_external_id_across_imports_is_skipped`, `test_sales::test_row_errors_do_not_block_valid_rows`, `test_sales::test_same_file_is_rejected_by_fingerprint` | Import id, per-row error report, no duplicate scoring and reconciliation exist. Missing: correction of sales points (403), an error report beyond 200 rows, voiding an import. | A2, C4, C10 |
| **BR-011** | قوانین امتیاز تاریخ اعتبار دارند؛ تغییر قانون امتیاز گذشته را بازنویسی نمی‌کند؛ هر نسخه شناسه دارد | implemented | `repo.create_mission`, `repo.update_mission`, `scoring.find_rule_version` | `test_flow::test_mission_edit_publishes_new_rule_version`, `test_scoring::test_active_rule_version_selection_after_retirement` | A points change retires the current version and publishes the next; past events keep their `rule_version_id`. The version is chosen at approval time, not at submit time (question B6-2). | A1, B6 |
| **BR-012** | کاربر غیرفعال نمی‌تواند مأموریت جدید ثبت کند؛ سوابق و امتیاز حفظ می‌شود | partial | `main.demo_login`, `repo.leaderboard`, `security.current_user` | — | An inactive user cannot sign in or keep a session, and is hidden from the leaderboard; history is kept. Nothing can deactivate a user (no admin screen), `is_active` has no test, and a pending submission of a deactivated user can still be approved and scored. | C1 |
| **BR-013** | هر رقابت: جامعه هدف + بازه زمانی + معیار رتبه‌بندی مشخص | partial | `repo.active_competition`, `seed.seed_demo` | — | A competition has an organization and a time window only: no audience, no ranking criterion, no management screen. The only row is created by the seed and ends 7 days after seeding. | A4, C2 |
| **BR-014** | موجودی کیف = مجموع رویدادهای معتبر؛ امتیاز داخلی پول/اعتبار قابل برداشت نیست | implemented | `repo.wallet_balance`, `scoring._persist_award` | `test_corrections::test_reversal_creates_negative_event_and_fixes_projections`, `test_scoring::test_wallet_matches_ledger` | The wallet row is written in the same transaction as the event and the ledger row. There is no redemption or cash-out path anywhere (OD-08 open). | B5 |

## 3. Epics

| ID | Title | State | Code | Tests | Gaps and notes | Backlog |
|---|---|---|---|---|---|---|
| **EP-01** | Auth & User Mgmt | demo-only | `main.demo_login`, `security.current_user` | `test_hardening::test_session_token_in_url_works_without_cookies` | Demo login only; users are created by the seed, not by a screen. | B2, C1, C9 |
| **EP-02** | Organization | partial | `seed.seed_demo` | `test_flow::test_organization_scope_blocks_foreign_submission` | One organization row; every query is organization-scoped. No branch, city or team level (OD-02 open). | B3, C1, C11 |
| **EP-03** | Mission Management | implemented | `repo.create_mission`, `repo.update_mission` | `test_flow::test_mission_edit_publishes_new_rule_version` | See MVP-04. | A1 |
| **EP-04** | Mission Execution | implemented | `main.submit_mission`, `repo.create_submission` | `test_flow::test_full_flow_approval_scores_once` | See MVP-05. | C5 |
| **EP-05** | Verification | implemented | `main.admin_decide`, `repo.review_submission` | `test_flow::test_reject_requires_reason_and_awards_nothing` | Manual review only; the auto-approve branch in `create_submission` is unreachable from the admin form and untested (OD-06 open). | A1, C6 |
| **EP-06** | Scoring | implemented | `scoring.award_mission_approval`, `scoring.reverse_event` | `test_scoring::test_award_is_idempotent` | See MVP-07. | A1, A2, C8 |
| **EP-07** | Sales Integration | sample | `repo.process_sales_import`, `sales.validate_rows` | `test_sales::test_process_creates_each_score_once` | See MVP-08. File upload only; no ERP connection (OD-11 open). | B4, C4, C10 |
| **EP-08** | Competition & Leaderboard | partial | `repo.leaderboard` | `test_corrections::test_leaderboard_reflects_the_correction` | Individual leaderboard only; no competition management and no group competition. | C2, C11 |
| **EP-09** | Admin Panel | partial | `main.admin_missions`, `main.admin_queue`, `main.admin_sales` | `test_flow::test_visitors_and_operators_have_no_admin_powers` | See MVP-11. | A2, A6, C1 |
| **EP-10** | Reports | missing | — | — | Not started. | C3 |
| **EP-11** | Notification | missing | `scoring._persist_award` | — | `outbox_events` rows are written with every score event, but nothing reads them: no notification exists. | C13 |
| **EP-12** | Infra & DevOps | partial | — | — | One CI workflow (lint, tests, boot check). No container, no staging, unpinned dependencies. The CI secret scan step never fails (see backlog A10). | A7, A10, D1, D3 |
| **EP-13** | QA | partial | — | — | HTTP-level tests with pytest only; no type check, no browser test, no load test. | D4, D6 |

## 4. Open decisions

| ID | Topic | Status | Assumption is coded in | Backlog rows |
|---|---|---|---|---|
| **OD-01** | روش ورود | OPEN | `app/main.py`, `app/security.py`, `app/templates/login.html` | B2 |
| **OD-02** | ساختار سازمانی | OPEN | — | B3 |
| **OD-03** | نمونه فایل فروش | OPEN | `app/sales.py`, `app/sample_sales.py`, `app/seed.py`, `db/migrations/0003_sales_import.sql` | B4 |
| **OD-04** | فرمول امتیاز فروش | OPEN | `app/scoring.py`, `app/seed.py`, `app/templates/admin_sales.html`, `db/migrations/0003_sales_import.sql` | B4 |
| **OD-05** | SKUهای هدف | OPEN | `app/seed.py` | B4 |
| **OD-06** | اعتبارسنجی مأموریت | OPEN | — | B5, C6 |
| **OD-07** | معیار رقابت | OPEN | — | B3 |
| **OD-08** | کیف امتیاز | OPEN | `app/templates/score.html` | B5 |
| **OD-09** | مشارکت خانواده | OPEN | — | — |
| **OD-10** | سرپرست فروش | OPEN | — | B3 |
| **OD-11** | یکپارچگی | OPEN | — | — |
| **OD-12** | ظرفیت | OPEN | — | D1, D6 |

Full text, options and impact: `docs/decisions/open-decisions.md`. The "coded in" column
lists the files to revisit when the decision is made.

## 5. Decisions and ADRs

| ID | Title | Status | Recorded in | Referenced in code |
|---|---|---|---|---|
| **D-001** | استفاده از FastAPI + SQLite برای Prototype | PROPOSED | `docs/decisions/decision-log.md` | — |
| **D-002** | حمل سشن با توکن امضاشده در URL (فقط دمو) | PROPOSED | `docs/decisions/decision-log.md` | `app/security.py` |
| **D-003** | سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه) | PROPOSED | `docs/decisions/decision-log.md` | `app/maintenance.py` |
| **D-004** | اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه) | PROPOSED | `docs/decisions/decision-log.md` | — |
| **D-005** | ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE | PROPOSED | `docs/decisions/decision-log.md` | — |
| **ADR-0001** | FastAPI + SQLite for the prototype | PROPOSED | `docs/architecture/decisions/0001-fastapi-sqlite-prototype.md` | `db/migrations/0001_init.sql` |

## 6. Milestones

| ID | Milestone — date |
|---|---|
| **MS-01** | Prototype — چهارشنبه ۲۷ آبان ۱۴۰۵ = 2026-11-18 |
| **MS-02** | Feedback — شنبه ۳۰ آبان ۱۴۰۵ = 2026-11-21 |
| **MS-03** | MVP Dev — پس از تأیید مسیر |
| **MS-04** | RC — پیش از شب یلدا ۱۴۰۵ = 2026-12-21 |
| **MS-05** | Acceptance — پس از UAT |

Source: `.agent/CONTEXT.md` §۱۰ and `docs/delivery/execution-plan.md`.

## 7. Backlog rows

| Row | Work | Status | Ids named in the row or its detail section |
|---|---|---|---|
| **A1** | تأیید و ثبت امتیاز در یک تراکنش؛ خطای قانون امتیاز به پیام فارسی تبدیل شود | TODO | MVP-06, BR-003, BR-011 |
| **A2** | اصلاح امتیاز از داخل پنل در دسترس باشد و برای امتیاز فروش هم کار کند | TODO | BR-005, BR-010, D-004 |
| **A3** | نمایش تاریخ/ساعت و تفسیر بازه‌ها به وقت تهران | TODO | MVP-03, MVP-04 |
| **A4** | سناریوی دمو + reseed صبح روز دمو + یک تمرین کامل | DOING | BR-013, MS-01 |
| **A5** | «چرا این امتیاز؟» از صفحه تاریخچه و برای امتیاز فروش | TODO | MVP-13, BR-010 |
| **A6** | ریزه‌کاری‌های UI مسیر دمو (۵ مورد) | TODO | MVP-11, D-005 |
| **A7** | قفل نسخه وابستگی‌ها (constraints) | TODO | EP-12 |
| **A8** | همسان‌سازی اسناد با کد | DOING | MVP-02, MVP-08, BR-010, BR-012, D-001, D-005 |
| **A9** | تعیین تکلیف PR #3 باز | TODO | ADR-0010 |
| **A10** | اسکن secret در CI واقعاً اجرا شود | TODO | EP-12 |
| **B1** | تأیید مسیر محصول و ثبت انتقال P→H؛ تعیین وضعیت D-001…D-005؛ ADR-0002 برای stack تولید (backend و کلاینت موبایل) | — | D-001, D-005, ADR-0001, ADR-0002 |
| **B2** | OD-01 روش ورود (موبایل + OTP یا شناسه پرسنلی) | — | OD-01 |
| **B3** | OD-02 ساختار سازمانی · OD-10 نقش سرپرست فروش · OD-07 معیار رتبه‌بندی فردی/گروهی و قاعده تساوی (BR-009) | — | BR-009, OD-02, OD-07, OD-10 |
| **B4** | OD-03 نمونه واقعی فایل فروش و فرهنگ داده (به‌ویژه تقویم ستون تاریخ) · OD-04 فرمول · OD-05 ضرایب SKU · مبنای دوره (تاریخ فروش یا زمان پردازش) · نحوه ثبت برگشت/اصلاح فروش | — | OD-03, OD-04, OD-05 |
| **B5** | OD-06 تأیید خودکار یا دستی · OD-08 امتیاز نمایشی یا قابل مصرف · D-003 مدت نگهداری تصویر شاهد | — | OD-06, OD-08, D-003 |
| **B6** | چهار قاعده ریز که در اجرا دیده شد (پایین) | — | BR-008 |
| **C1** | مدیریت کاربران، نگاشت شناسه فروش، فعال/غیرفعال‌سازی | — | MVP-11, BR-012, EP-01 |
| **C2** | مدیریت دوره رقابت، رتبه برای همه کاربران، صفحه‌بندی | — | MVP-09, BR-013 |
| **C3** | گزارش عملکرد پایه + خروجی CSV | — | MVP-12, EP-10 |
| **C4** | فایل فروش: گزارش خطا (فیلتر وضعیت، صفحه‌بندی، CSV ردیف‌های ردشده) + اعتبارسنجی تقویم تاریخ | — | MVP-08, BR-010 |
| **C5** | کنترل تصویر شاهد: نوع واقعی فایل، هشدار تصویر تکراری، پاک‌سازی فایل بدون ردیف | — | MVP-05, D-003 |
| **C6** | قواعد بازبینی: منع تأیید ارسالِ خود، اعمال B6-۱، و در صورت تصمیم OD-06 مأموریت بدون بازبینی | — | MVP-06, OD-06 |
| **C7** | صفحه پروفایل | — | MVP-02 |
| **C8** | سخت‌سازی اصلاح امتیاز: دوره‌بندی، تأیید دومرحله‌ای، اصلاح جزئی، حذف `float` | — | BR-008, D-004 |
| **C9** | احراز هویت واقعی + سشن سمت سرور؛ **همین حالا (XS):** خاموش‌بودن demo-login بیرون از dev/test | — | MVP-01, D-002 |
| **C10** | قرارداد واقعی فروش: نگاشت ستون، ضرایب SKU، مبنای دوره، ابطال import با رخداد معکوس | — | MVP-08, BR-007 |
| **C11** | رقابت گروهی/تیمی | — | MVP-10 |
| **C12** | API نسخه‌دار `/api/v1` برای کلاینت موبایل | — | — |
| **C13** | اعلان درون‌برنامه‌ای («X امتیاز اضافه شد») | — | EP-11 |
| **D1** | PostgreSQL + ابزار مهاجرت واقعی + تمرین backup/restore | — | OD-12 |
| **D2** | ذخیره‌سازی شیء برای تصاویر + پاک‌سازی زمان‌بندی‌شده | — | — |
| **D3** | استقرار: container، staging، HTTPS، کوکی امن، بستن `frame-ancestors *`، rate limit مشترک | — | — |
| **D4** | دروازه‌های کیفیت: type-check در CI، تست طلایی برای هر قانون، E2E مرورگر | — | — |
| **D5** | ورودی تاریخ شمسی در فرم‌های مدیر + صفحه مشاهده audit log | — | — |
| **D6** | آزمون بار و اعداد ظرفیت (پیش‌نیاز حالت S) | — | OD-12 |

Evidence, sizes and order: `docs/delivery/backlog.md`.

## 8. Where each id is mentioned

Use this list when a decision changes: these are the files to re-read and update.

| ID | Defined in | Files | Mentioned in |
|---|---|---|---|
| **MVP-01** | `.agent/CONTEXT.md` | 6 | `.agent/CONTEXT.md`, `AGENTS.md`, `CHANGELOG.md`, `docs/delivery/backlog.md`, `docs/handoffs/handover.md`, `docs/product/prd.md` |
| **MVP-02** | `.agent/CONTEXT.md` | 5 | `.agent/CONTEXT.md`, `README.md`, `docs/delivery/backlog.md`, `docs/handoffs/handover.md`, `docs/product/prd.md` |
| **MVP-03** | `.agent/CONTEXT.md` | 4 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/handoffs/handover.md`, `docs/product/prd.md` |
| **MVP-04** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/product/prd.md` |
| **MVP-05** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/product/prd.md` |
| **MVP-06** | `.agent/CONTEXT.md` | 4 | `.agent/CONTEXT.md`, `.agent/playbooks/vertical-slice.md`, `docs/delivery/backlog.md`, `docs/product/prd.md` |
| **MVP-07** | `.agent/CONTEXT.md` | 4 | `.agent/CONTEXT.md`, `.agent/playbooks/vertical-slice.md`, `docs/agent-guide/knowledge-graph.md`, `docs/product/prd.md` |
| **MVP-08** | `.agent/CONTEXT.md` | 4 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/handoffs/handover.md`, `docs/product/prd.md` |
| **MVP-09** | `.agent/CONTEXT.md` | 4 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/handoffs/handover.md`, `docs/product/prd.md` |
| **MVP-10** | `.agent/CONTEXT.md` | 5 | `.agent/CONTEXT.md`, `README.md`, `docs/architecture/database-erd.md`, `docs/delivery/backlog.md`, `docs/product/prd.md` |
| **MVP-11** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/product/prd.md` |
| **MVP-12** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/product/prd.md` |
| **MVP-13** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/product/prd.md` |
| **BR-001** | `.agent/CONTEXT.md` | 12 | `.agent/CONTEXT.md`, `.agent/playbooks/prototype-9-days.md`, `.agent/roles/03-backend.md`, `CHANGELOG.md`, `README.md`, `docs/delivery/demo-script.md`, `docs/engineering/api-spec.md`, `docs/handoffs/current-state.md`, `docs/handoffs/handover.md`, `docs/product/prd.md`, `docs/quality/qa-test-strategy.md`, `tests/test_flow.py` |
| **BR-002** | `.agent/CONTEXT.md` | 6 | `.agent/CONTEXT.md`, `.agent/playbooks/prototype-9-days.md`, `.agent/roles/03-backend.md`, `docs/engineering/api-spec.md`, `docs/handoffs/handover.md`, `docs/product/prd.md` |
| **BR-003** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `.agent/playbooks/vertical-slice.md`, `docs/delivery/backlog.md` |
| **BR-004** | `.agent/CONTEXT.md` | 2 | `.agent/CONTEXT.md`, `.agent/playbooks/vertical-slice.md` |
| **BR-005** | `.agent/CONTEXT.md` | 4 | `.agent/CONTEXT.md`, `docs/agent-guide/README.md`, `docs/agent-guide/knowledge-graph.md`, `docs/delivery/backlog.md` |
| **BR-006** | `.agent/CONTEXT.md` | 2 | `.agent/CONTEXT.md`, `docs/product/prd.md` |
| **BR-007** | `.agent/CONTEXT.md` | 4 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/handoffs/handover.md`, `docs/product/prd.md` |
| **BR-008** | `.agent/CONTEXT.md` | 4 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/handoffs/current-state.md`, `docs/product/prd.md` |
| **BR-009** | `.agent/CONTEXT.md` | 9 | `.agent/CONTEXT.md`, `.agent/playbooks/prototype-9-days.md`, `README.md`, `app/templates/leaderboard.html`, `docs/decisions/decision-log.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/handoffs/current-state.md`, `docs/product/prd.md` |
| **BR-010** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/product/prd.md` |
| **BR-011** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/product/prd.md` |
| **BR-012** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/product/prd.md` |
| **BR-013** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/product/prd.md` |
| **BR-014** | `.agent/CONTEXT.md` | 2 | `.agent/CONTEXT.md`, `docs/product/prd.md` |
| **EP-01** | `.agent/CONTEXT.md` | 4 | `.agent/CONTEXT.md`, `CHANGELOG.md`, `docs/delivery/backlog.md`, `docs/handoffs/handover.md` |
| **EP-02** | `.agent/CONTEXT.md` | 2 | `.agent/CONTEXT.md`, `docs/handoffs/handover.md` |
| **EP-03** | `.agent/CONTEXT.md` | 2 | `.agent/CONTEXT.md`, `docs/handoffs/handover.md` |
| **EP-04** | `.agent/CONTEXT.md` | 1 | `.agent/CONTEXT.md` |
| **EP-05** | `.agent/CONTEXT.md` | 2 | `.agent/CONTEXT.md`, `.agent/playbooks/vertical-slice.md` |
| **EP-06** | `.agent/CONTEXT.md` | 2 | `.agent/CONTEXT.md`, `.agent/playbooks/vertical-slice.md` |
| **EP-07** | `.agent/CONTEXT.md` | 15 | `.agent/CONTEXT.md`, `CHANGELOG.md`, `README.md`, `app/sales.py`, `db/migrations/0003_sales_import.sql`, `docs/README.md`, `docs/agent-guide/03-deliver.md`, `docs/agent-guide/knowledge-graph.md`, `docs/decisions/decision-log.md`, `docs/delivery/execution-plan.md`, `docs/engineering/api-spec.md`, `docs/engineering/sales-import.md`, `docs/handoffs/current-state.md`, `docs/handoffs/handover.md`, `tests/test_sales.py` |
| **EP-08** | `.agent/CONTEXT.md` | 1 | `.agent/CONTEXT.md` |
| **EP-09** | `.agent/CONTEXT.md` | 1 | `.agent/CONTEXT.md` |
| **EP-10** | `.agent/CONTEXT.md` | 5 | `.agent/CONTEXT.md`, `README.md`, `docs/delivery/backlog.md`, `docs/handoffs/current-state.md`, `docs/handoffs/handover.md` |
| **EP-11** | `.agent/CONTEXT.md` | 5 | `.agent/CONTEXT.md`, `README.md`, `docs/architecture/database-erd.md`, `docs/delivery/backlog.md`, `docs/handoffs/current-state.md` |
| **EP-12** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `docs/decisions/decision-log.md`, `docs/delivery/backlog.md` |
| **EP-13** | `.agent/CONTEXT.md` | 1 | `.agent/CONTEXT.md` |
| **OD-01** | `docs/decisions/open-decisions.md` | 17 | `.agent/CONTEXT.md`, `.agent/playbooks/prototype-9-days.md`, `CHANGELOG.md`, `README.md`, `app/main.py`, `app/security.py`, `app/templates/login.html`, `docs/README.md`, `docs/agent-guide/01-start.md`, `docs/decisions/decision-log.md`, `docs/decisions/open-decisions.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/engineering/api-spec.md`, `docs/handoffs/current-state.md`, `docs/handoffs/handover.md`, `docs/product/prd.md` |
| **OD-02** | `docs/decisions/open-decisions.md` | 7 | `.agent/CONTEXT.md`, `README.md`, `docs/architecture/database-erd.md`, `docs/decisions/open-decisions.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/handoffs/current-state.md` |
| **OD-03** | `docs/decisions/open-decisions.md` | 13 | `.agent/CONTEXT.md`, `README.md`, `app/sales.py`, `app/sample_sales.py`, `app/seed.py`, `db/migrations/0003_sales_import.sql`, `docs/agent-guide/troubleshooting.md`, `docs/decisions/decision-log.md`, `docs/decisions/open-decisions.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/engineering/sales-import.md`, `docs/handoffs/current-state.md` |
| **OD-04** | `docs/decisions/open-decisions.md` | 17 | `.agent/CONTEXT.md`, `.agent/playbooks/prototype-9-days.md`, `.agent/playbooks/scoring-and-rules.md`, `README.md`, `app/scoring.py`, `app/seed.py`, `app/templates/admin_sales.html`, `db/migrations/0003_sales_import.sql`, `docs/agent-guide/README.md`, `docs/agent-guide/knowledge-graph.md`, `docs/decisions/decision-log.md`, `docs/decisions/open-decisions.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/engineering/sales-import.md`, `docs/engineering/scoring-engine.md`, `docs/handoffs/current-state.md` |
| **OD-05** | `docs/decisions/open-decisions.md` | 8 | `.agent/CONTEXT.md`, `app/seed.py`, `docs/decisions/decision-log.md`, `docs/decisions/open-decisions.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/engineering/sales-import.md`, `docs/engineering/scoring-engine.md` |
| **OD-06** | `docs/decisions/open-decisions.md` | 5 | `.agent/CONTEXT.md`, `.agent/playbooks/prototype-9-days.md`, `docs/decisions/decision-log.md`, `docs/decisions/open-decisions.md`, `docs/delivery/backlog.md` |
| **OD-07** | `docs/decisions/open-decisions.md` | 5 | `.agent/CONTEXT.md`, `.agent/playbooks/prototype-9-days.md`, `docs/decisions/open-decisions.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md` |
| **OD-08** | `docs/decisions/open-decisions.md` | 10 | `.agent/CONTEXT.md`, `.agent/playbooks/prototype-9-days.md`, `README.md`, `app/templates/score.html`, `docs/decisions/decision-log.md`, `docs/decisions/open-decisions.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/engineering/scoring-engine.md`, `docs/handoffs/current-state.md` |
| **OD-09** | `docs/decisions/open-decisions.md` | 2 | `.agent/CONTEXT.md`, `docs/decisions/open-decisions.md` |
| **OD-10** | `docs/decisions/open-decisions.md` | 6 | `.agent/CONTEXT.md`, `docs/decisions/open-decisions.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/handoffs/current-state.md`, `docs/product/admin-panel-spec.md` |
| **OD-11** | `docs/decisions/open-decisions.md` | 5 | `.agent/CONTEXT.md`, `docs/decisions/decision-log.md`, `docs/decisions/open-decisions.md`, `docs/engineering/sales-import.md`, `docs/handoffs/handover.md` |
| **OD-12** | `docs/decisions/open-decisions.md` | 10 | `.agent/CONTEXT.md`, `docs/agent-guide/01-start.md`, `docs/architecture/decisions/0001-fastapi-sqlite-prototype.md`, `docs/architecture/deployment-architecture.md`, `docs/decisions/decision-log.md`, `docs/decisions/open-decisions.md`, `docs/delivery/backlog.md`, `docs/handoffs/current-state.md`, `docs/handoffs/handover.md`, `docs/product/prd.md` |
| **D-001** | `docs/decisions/decision-log.md` | 9 | `CHANGELOG.md`, `docs/README.md`, `docs/agent-guide/01-start.md`, `docs/architecture/decisions/0001-fastapi-sqlite-prototype.md`, `docs/decisions/decision-log.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/handoffs/current-state.md`, `docs/handoffs/handover.md` |
| **D-002** | `docs/decisions/decision-log.md` | 11 | `CHANGELOG.md`, `README.md`, `app/security.py`, `docs/agent-guide/01-start.md`, `docs/architecture/deployment-architecture.md`, `docs/decisions/decision-log.md`, `docs/delivery/backlog.md`, `docs/engineering/api-spec.md`, `docs/handoffs/current-state.md`, `docs/handoffs/handover.md`, `docs/operations/runbook.md` |
| **D-003** | `docs/decisions/decision-log.md` | 8 | `CHANGELOG.md`, `README.md`, `app/maintenance.py`, `docs/decisions/decision-log.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/handoffs/current-state.md`, `docs/operations/runbook.md` |
| **D-004** | `docs/decisions/decision-log.md` | 11 | `CHANGELOG.md`, `README.md`, `docs/agent-guide/01-start.md`, `docs/agent-guide/knowledge-graph.md`, `docs/architecture/technical-design.md`, `docs/decisions/decision-log.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/delivery/execution-plan.md`, `docs/engineering/scoring-engine.md`, `docs/handoffs/current-state.md` |
| **D-005** | `docs/decisions/decision-log.md` | 15 | `CHANGELOG.md`, `README.md`, `docs/README.md`, `docs/agent-guide/01-start.md`, `docs/agent-guide/03-deliver.md`, `docs/architecture/technical-design.md`, `docs/decisions/decision-log.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/delivery/execution-plan.md`, `docs/engineering/api-spec.md`, `docs/engineering/sales-import.md`, `docs/engineering/scoring-engine.md`, `docs/handoffs/current-state.md`, `docs/handoffs/handover.md` |
| **ADR-0001** | `docs/architecture/decisions/0001-fastapi-sqlite-prototype.md` | 10 | `CHANGELOG.md`, `README.md`, `db/migrations/0001_init.sql`, `docs/README.md`, `docs/agent-guide/knowledge-graph.md`, `docs/architecture/database-erd.md`, `docs/architecture/decisions/0001-fastapi-sqlite-prototype.md`, `docs/architecture/solution-architecture.md`, `docs/decisions/decision-log.md`, `docs/delivery/backlog.md` |
| **ADR-0002** | not defined in this repository | 4 | `docs/architecture/decisions/0001-fastapi-sqlite-prototype.md`, `docs/architecture/solution-architecture.md`, `docs/decisions/decision-log.md`, `docs/delivery/backlog.md` |
| **ADR-0010** | not defined in this repository | 2 | `CHANGELOG.md`, `docs/delivery/backlog.md` |
| **MS-01** | `.agent/CONTEXT.md` | 15 | `.agent/CONTEXT.md`, `.agent/MASTER_PROMPT.fa.md`, `.agent/playbooks/prototype-9-days.md`, `.agent/templates/current-state.md`, `AGENTS.md`, `CHANGELOG.md`, `docs/README.md`, `docs/agent-guide/knowledge-graph.md`, `docs/architecture/decisions/0001-fastapi-sqlite-prototype.md`, `docs/decisions/decision-log.md`, `docs/delivery/backlog.md`, `docs/delivery/demo-script.md`, `docs/delivery/execution-plan.md`, `docs/handoffs/current-state.md`, `docs/handoffs/handover.md` |
| **MS-02** | `.agent/CONTEXT.md` | 9 | `.agent/CONTEXT.md`, `.agent/playbooks/prototype-9-days.md`, `.agent/templates/current-state.md`, `docs/architecture/decisions/0001-fastapi-sqlite-prototype.md`, `docs/architecture/solution-architecture.md`, `docs/delivery/backlog.md`, `docs/delivery/execution-plan.md`, `docs/handoffs/current-state.md`, `docs/handoffs/handover.md` |
| **MS-03** | `.agent/CONTEXT.md` | 6 | `.agent/CONTEXT.md`, `docs/decisions/decision-log.md`, `docs/decisions/open-decisions.md`, `docs/delivery/backlog.md`, `docs/delivery/execution-plan.md`, `docs/handoffs/handover.md` |
| **MS-04** | `.agent/CONTEXT.md` | 4 | `.agent/CONTEXT.md`, `docs/delivery/backlog.md`, `docs/delivery/execution-plan.md`, `docs/handoffs/handover.md` |
| **MS-05** | `.agent/CONTEXT.md` | 3 | `.agent/CONTEXT.md`, `docs/delivery/execution-plan.md`, `docs/handoffs/handover.md` |

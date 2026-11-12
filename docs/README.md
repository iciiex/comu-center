# مستندات پروژه Kiloos Club

> ترتیب مطالعه: `../AGENTS.md` → `../.agent/CONTEXT.md` → `handoffs/current-state.md` → این فایل.
> تحویل‌گیرنده پروژه: `handoffs/handover.md` · ایجنت یا توسعه‌دهنده: `agent-guide/README.md`.

## شروع، ادامه و تحویل (راهنمای ایجنت)

| موضوع | مسیر | وضعیت |
|---|---|---|
| سند تحویل پروژه | `handoffs/handover.md` | عکس تاریخ‌دار (۲۰ آبان ۱۴۰۵) |
| وضعیت زنده | `handoffs/current-state.md` | به‌روز |
| فهرست راهنمای ایجنت و جدول «کجا پیدا کنم» | `agent-guide/README.md` | به‌روز |
| شروع: نصب، ساختار، جریان درخواست، قواعد ثابت | `agent-guide/01-start.md` | به‌روز |
| ادامه: الگوهای کد و دستور پخت تغییرها | `agent-guide/02-continue.md` | به‌روز |
| تحویل: دروازه‌ها، اسناد، commit و PR | `agent-guide/03-deliver.md` | به‌روز |
| نقشه کد: مسیرها، تابع‌ها، جدول‌ها، تست‌ها | `agent-guide/code-map.md` | تولیدشده (`make docs`) |
| ماتریس ردیابی نیازمندی ↔ کد ↔ تست | `agent-guide/traceability.md` | تولیدشده (`make docs`) |
| گراف دانش و روش پرس‌وجو | `agent-guide/knowledge-graph.md` و `../graphify-out/GRAPH_REPORT.md` | تولیدشده (`make graph`) |
| عیب‌یابی | `agent-guide/troubleshooting.md` | به‌روز |
| تاریخچه تغییرات | `../CHANGELOG.md` | به‌روز |

## اسناد محصول و مهندسی

| # | موضوع | مسیر | وضعیت |
|---|---|---|---|
| 01 | Product Strategy & Scope | `product/strategy-and-scope.md` | خلاصه + ارجاع به منبع |
| 02 | Product Requirements | `product/prd.md` | جزئی (delta) |
| 03 | Solution Architecture | `architecture/solution-architecture.md` | جزئی / پیشنهادی |
| 04 | Technical Design & DB | `architecture/technical-design.md` | جزئی |
| 05 | Database ERD & SQL | `architecture/database-erd.md` | پیاده‌سازی‌شده |
| 06 | Scoring Engine | `engineering/scoring-engine.md` | پیاده‌سازی‌شده |
| 06-A | Scoring Rule Matrix | `engineering/scoring-rule-matrix.md` | نمونه (SAMPLE) |
| 07 | API Specification | `engineering/api-spec.md` | پیاده‌سازی‌شده (زیرمجموعه) |
| 07-A | Sales Import (EP-07) | `engineering/sales-import.md` | پیاده‌سازی‌شده (XLSX، SAMPLE) |
| 07-B | Sales Quest Arena BFF alignment | `engineering/game-bff-alignment.md` | BFF prototype پیاده‌سازی شد؛ اتصال فرانت‌اند باز |
| 07-C | Tribal Gamification API contract | `engineering/tribal-api-contract.md` | پیشنهادی؛ برای بازبینی، هیچ endpoint پیاده‌سازی نشده |
| 03-A | Tribal Gamification architecture and two-agent plan | `architecture/tribal-gamification-plan.md` | طراحی برای بازبینی؛ بدون تغییر runtime |
| 08 | UX/UI Specification | `product/ux-ui-spec.md` | جزئی |
| 09 | Admin Panel Specification | `product/admin-panel-spec.md` | جزئی |
| 10 | QA & Test Strategy | `quality/qa-test-strategy.md` | جزئی (۷۱ تست) |
| 11 | DevOps & Deployment | `architecture/deployment-architecture.md` | فقط prototype |
| 12 | Execution Plan | `delivery/execution-plan.md` | جزئی |
| 12-A | Backlog و نقشه ادامه توسعه | `delivery/backlog.md` | PROPOSED (۲۰ آبان ۱۴۰۵) |
| 12-B | سناریوی دمو MS-01 | `delivery/demo-script.md` | PROPOSED (بازپخش خودکار ۲۱ آبان؛ تمرین با مرورگر انجام نشده) |
| 13 | Open Decisions | `decisions/open-decisions.md` | seed شده (OD-01..12) |
| — | Decision Log | `decisions/decision-log.md` | D-001 تا D-005 (همه PROPOSED) |
| — | Runbook | `operations/runbook.md` | prototype |
| — | ADRها | `architecture/decisions/` | ADR-0001 |

## قواعد

- مستندات باید واقعیت فعلی را نشان دهند؛ اختلاف با کد پنهان نمی‌شود.
- تنها راه «مصوب» کردن یک تصمیم، ثبت `APPROVED` در `decisions/decision-log.md` است.
- هر تغییر کد، سند متأثر خود را در همان تغییر به‌روز می‌کند (جدول در `AGENTS.md` §12).
- اعداد و سیاست‌های تأییدنشده با `PROPOSED` / `SAMPLE` علامت می‌خورند.
- `agent-guide/code-map.md` و `agent-guide/traceability.md` دستی ویرایش نمی‌شوند؛ پس از هر تغییر کد، تست یا سند
  `make docs` اجرا می‌شود (تست `tests/test_docs.py` کهنگی را می‌گیرد).

## منبع اصلی

Google Drive → «Kiloos Club — Product Strategy & Scope» نسخه ۰.۱ (شامل اسناد ۰۱ تا ۱۲).
این پوشه واقعیت پیاده‌سازی و تصمیم‌های جاری را نگه می‌دارد، نه بازنویسی سند اصلی.

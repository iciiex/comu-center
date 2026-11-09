# مستندات پروژه Kiloos Club

> ترتیب مطالعه: `../AGENTS.md` → `../.agent/CONTEXT.md` → `handoffs/current-state.md` → این فایل.

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
| 08 | UX/UI Specification | `product/ux-ui-spec.md` | جزئی |
| 09 | Admin Panel Specification | `product/admin-panel-spec.md` | جزئی |
| 10 | QA & Test Strategy | `quality/qa-test-strategy.md` | جزئی (۱۸ تست) |
| 11 | DevOps & Deployment | `architecture/deployment-architecture.md` | فقط prototype |
| 12 | Execution Plan | `delivery/execution-plan.md` | جزئی |
| 13 | Open Decisions | `decisions/open-decisions.md` | seed شده (OD-01..12) |
| — | Decision Log | `decisions/decision-log.md` | D-001 (PROPOSED) |
| — | Current State | `handoffs/current-state.md` | به‌روز |
| — | Runbook | `operations/runbook.md` | prototype |
| — | ADRها | `architecture/decisions/` | ADR-0001 |

## قواعد

- مستندات باید واقعیت فعلی را نشان دهند؛ اختلاف با کد پنهان نمی‌شود.
- تنها راه «مصوب» کردن یک تصمیم، ثبت `APPROVED` در `decisions/decision-log.md` است.
- هر تغییر کد، سند متأثر خود را در همان تغییر به‌روز می‌کند (جدول در `AGENTS.md` §12).
- اعداد و سیاست‌های تأییدنشده با `PROPOSED` / `SAMPLE` علامت می‌خورند.

## منبع اصلی

Google Drive → «Kiloos Club — Product Strategy & Scope» نسخه ۰.۱ (شامل اسناد ۰۱ تا ۱۲).
این پوشه واقعیت پیاده‌سازی و تصمیم‌های جاری را نگه می‌دارد، نه بازنویسی سند اصلی.

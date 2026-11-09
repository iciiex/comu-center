# Decision Log

> فقط تصمیم‌های ثبت‌شده اینجا می‌توانند `APPROVED` باشند.
> قالب هر ورودی: `## D-XXX — عنوان` با `Status`, `Date`, `Approved by`, `Related`.

## قالب

```markdown
## D-001 — عنوان تصمیم

- Status: APPROVED | PROPOSED | SUPERSEDED
- Date: YYYY-MM-DD
- Approved by:
- Owners:
- Related: OD-xx / ADR-xxx / EP-xx

**Decision:** …
**Rationale:** …
**Consequences:** …
**Affected docs:**
```

## تصمیم‌های ثبت‌شده

<!-- از اینجا شروع کن -->

## D-001 — استفاده از FastAPI + SQLite برای Prototype

- Status: PROPOSED
- Date: 2026-11-09
- Approved by: —
- Owners: Architecture / Backend
- Related: OD-12 / ADR-0001 / EP-12

**Decision:** برای MODE: P، پیاده‌سازی با FastAPI + Jinja + SQLite انجام می‌شود؛ انتخاب stack نهایی
پلتفرم و موبایل همچنان `OPEN` است و نیاز به ADR-0002 دارد.

**Rationale:** تحویل مسیر end-to-end تا MS-01 (۲۰۲۶-۱۱-۱۸) و اجتناب از تعهد ناخواسته به یک stack
تأییدنشده. قواعد امتیاز و اسکیما به‌صورت قابل‌انتقال طراحی شده‌اند.

**Consequences:** SQLite و UI سرور-رندرشده برای production مناسب نیستند؛ پیش از کاربر واقعی باید
PostgreSQL/OTP/CSRF/storage تصمیم‌گیری شود.

**Affected docs:** `docs/architecture/decisions/0001-fastapi-sqlite-prototype.md`،
`docs/architecture/database-erd.md`، `docs/engineering/api-spec.md`

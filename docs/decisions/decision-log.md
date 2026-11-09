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

---

## D-002 — حمل سشن با توکن امضاشده در URL (فقط دمو)

- Status: PROPOSED
- Date: 2026-11-09
- Approved by: —
- Owners: Engineering / Security
- Related: OD-01 / MS-01 / ADR-0001

**Problem:** پیش‌نمایش مشترک داخل iframe اجرا می‌شود و مرورگر کوکی سشن را به‌عنوان third-party بلاک
می‌کند؛ نتیجه: هر ورود بلافاصله به `/login` برمی‌گشت (۳۰۳).

**Decision (موقت):** همان توکن امضاشده‌ی سشن (`HMAC-SHA256`، TTL پیش‌فرض ۱۲ ساعت) علاوه بر کوکی
`kiloos_session`، به‌صورت `?s=` در URL هم پذیرفته و در لینک‌ها/فرم‌ها/ریدایرکت‌ها منتقل می‌شود.
در حالت کوکی، URL تمیز می‌ماند.

**Rationale:** بدون آن، دموی MS-01 در محیط ارائه کار نمی‌کند؛ هیچ راه دیگری (کوکی first-party،
SameSite=None، ذخیره‌سازی محلی) در iframe قابل اتکا نبود.

**Consequences / ریسک‌ها:** توکن در history، لاگ سرور و Referer دیده می‌شود؛ `Referrer-Policy: no-referrer`
و TTL کوتاه ریسک را کم می‌کند ولی حذف نمی‌کند. ورود و خروج، کوکی را هم ست/پاک می‌کند تا مسیر
معمولی سالم بماند.

**Exit condition:** پیش از کاربر واقعی، یکی از این دو: (۱) میزبانی first-party بدون iframe، یا
(۲) OTP واقعی + سشن سمت سرور (OD-01). در آن نقطه `?s=` حذف می‌شود و تست‌های fallback هم برداشته می‌شوند.

**Affected docs:** `docs/engineering/api-spec.md` (Session transport)، `docs/handoffs/current-state.md`،
`app/security.py`، `app/main.py`

---

## D-003 — سیاست نگهداری شاهد تصویری (پیش‌فرض نمونه)

- Status: PROPOSED
- Date: 2026-11-09
- Approved by: —
- Owners: Operations / Legal
- Related: OD-03 / evidence retention (open architecture decision)

**Decision (موقت):** شاهدهای تصویری قدیمی‌تر از `KILOOS_EVIDENCE_RETENTION_DAYS` (پیش‌فرض ۹۰ روز)
با دستور دستی `python -m app.maintenance purge-evidence` حذف می‌شوند: فایل پاک، ردیف
`submission_evidences` حذف، و یک رکورد `audit_logs` با `action='evidence.purged'` شامل
`submission_id`، `sha256` و `storage_path` باقی می‌ماند.

**Rationale:** جلوگیری از رشد بی‌پایان فایل‌ها هم‌زمان با حفظ قابلیت ردیابی تصمیم‌ها.

**Consequences:** ۹۰ روز یک عدد نمونه است و باید توسط کارفرما تأیید شود؛ تا آن زمان هیچ حذف خودکار
زمان‌بندی‌شده‌ای وجود ندارد (دستور دستی + `--dry-run`).

**Affected docs:** `docs/operations/runbook.md`، `app/maintenance.py`

---

## D-004 — اصلاح امتیاز با رخداد منفی (بدون ویرایش تاریخچه)

- Status: PROPOSED
- Date: 2026-11-09
- Approved by: —
- Owners: Product / Engineering / Finance (کیف امتیاز)
- Related: OD-08 / OD-06 / BR-009 / MS-03

**Decision (موقت):** اصلاح یک امتیاز با **رخداد جدید منفی** انجام می‌شود:

- `points = -original.points`، `corrects_event_id` به رخداد اصلی، `idempotency_key = score.reversed:<id>`
- `rule_code` و `rule_version_id` از رخداد اصلی کپی می‌شوند (منشأ امتیاز تغییر نمی‌کند)
- دلیل متنی الزامی است و در `reason` و `explain_json` می‌نشیند
- در یک تراکنش: رخداد + لجر منفی + کیف + `outbox_events('score.reversed')` + `audit_logs`
- فقط نقش `admin`؛ محدود به سازمان خودش
- ایندکس یکتای جزئی `ux_score_events_corrects` اصلاح دوم را در سطح دیتابیس غیرممکن می‌کند
- وضعیت `submission` تغییر نمی‌کند (همچنان `approved`) و رویداد اصلاحی خودش قابل اصلاح نیست

**Rationale:** تاریخچه‌ی امتیاز باید قابل حسابرسی بماند؛ حذف یا ویرایش رخداد، هم اعتماد کاربر و هم
قابلیت تطبیق با گزارش فروش را از بین می‌برد. جمع جبری رخدادها باعث می‌شود کیف و لیدربورد بدون
کد اضافی درست شوند.

**Consequences / موارد باز:**
- کیف می‌تواند منفی شود (امتیاز غیرقابل‌مصرف است، OD-08)؛ UI هشدار می‌دهد ولی مسدود نمی‌کند.
- «اصلاح جزئی» (بخشی از یک امتیاز) پشتیبانی نمی‌شود؛ در صورت نیاز، رخداد معکوس جزئی + سیاست جدید لازم است.
- سیاست «چه کسی درخواست اصلاح می‌دهد و چه کسی تأیید می‌کند» در MVP یک‌مرحله‌ای است (ادمین)؛ گردش‌کار
  دو‌مرحله‌ای برای بعد از MVP باز است.
- دوره‌ی رقابت بسته‌شده: اصلاح، مجموع دوره را عوض می‌کند (بر اساس `occurred_at` رخداد اصلاحی)؛ اگر
  سیاست «قفل دوره» تأیید شود، باید در همین نقطه اعمال شود.

**Affected docs:** `docs/engineering/scoring-engine.md`، `docs/engineering/api-spec.md`،
`docs/architecture/database-erd.md`، `docs/quality/qa-test-strategy.md`، `docs/handoffs/current-state.md`

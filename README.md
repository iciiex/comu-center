# Kiloos Club — Prototype

پلتفرم گیمیفیکیشن و انگیزش تیم فروش مویرگی گروه گلرنگ.
این مخزن در **MODE: P (Prototype)** است: یک مسیر end-to-end واقعی و قابل اجرا، با داده نمونه‌ی برچسب‌خورده.

> هدف نزدیک: نمایش چرخه **مأموریت → ثبت شاهد → تأیید → امتیاز → کیف امتیاز → رتبه‌بندی → تنظیم مأموریت**
> بدون دخالت توسعه‌دهنده. هر عدد و سیاستی که تأیید نشده، `PROPOSED`/`SAMPLE` است.

---

## اجرا

```bash
make setup     # venv + dependencies
make run       # http://0.0.0.0:8000
make check     # ruff + pytest
make seed      # بازسازی دیتابیس دمو
```

بدون Make:

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
.venv/bin/pytest && .venv/bin/ruff check app tests
```

اولین اجرا، دیتابیس `var/kiloos.db` را می‌سازد و داده نمونه را seed می‌کند (`var/` در git نیست).

### حساب‌های نمایشی

ورود واقعی (OTP / شناسه پرسنلی) هنوز تأیید نشده است — **OD-01**. صفحه ورود، کاربران نمونه را نشان می‌دهد:

| کاربر | نقش | کار |
|---|---|---|
| سارا محمدی | ویزیتور | مأموریت، ثبت شاهد، امتیاز |
| امیر رضایی | ویزیتور | دارای یک امتیاز نمونه (۱۵) |
| مریم کاظمی | ویزیتور | — |
| حسین کریمی | اپراتور | صف بررسی، تأیید/رد |
| نگار تهرانی | مدیر سیستم | مأموریت‌ها، نسخه قانون امتیاز |

---

## چه چیزی واقعی است (نه mock)

- **مأموریت طبق BR-001:** فقط `active` + داخل بازه + سازمان کاربر. مأموریت منقضی یا پیش‌نویس نمایش داده نمی‌شود.
- **ثبت شاهد:** آپلود تصویر با اعتبارسنجی نوع/حجم، ذخیره خصوصی، رکورد sha256.
- **بررسی:** گذارفاز `submitted → approved | rejected`، دلیل رد الزامی، ثبت در audit.
- **امتیاز:** `ScoreEvent` اپند-اونلی با `idempotency_key` + unique constraint؛ تأیید دوباره امتیاز جدید نمی‌سازد (409).
- **تراکنش:** رخداد + `point_transactions` + projection کیف + `outbox_events` با هم commit می‌شوند.
- **قابل توضیح:** هر امتیاز `explain_json` دارد (قانون، نسخه، شرط، ورودی، خروجی) و در UI دیده می‌شود.
- **نسخه‌بندی قانون:** تغییر امتیاز مأموریت، نسخه جدید منتشر می‌کند و نسخه قبلی را retire؛ امتیاز گذشته دست‌نخورده می‌ماند.
- **دسترسی:** `permission × organization scope` سمت سرور؛ تست منفی دارد (403).
- **کیف و رتبه‌بندی:** موجودی از ledger، رتبه از مجموع امتیاز دوره با tie-break موقت (BR-009 تأییدنشده).

## چه چیزی هنوز نیست (عمداً)

- OTP/پیامک واقعی، ارسال اعلان (EP-11)
- ورود داده فروش (EP-07) — پلی‌بوک آماده است، پیاده‌سازی نشده
- گزارش‌های مدیریتی و خروجی فایل (EP-10)
- PostgreSQL، صف/worker واقعی، object storage ابری
- سیاست نگهداری شواهد، rate limiting، CSRF token اختصاصی
- تقویم کامل شمسی در فرم‌های مدیریت (ورودی میلادی، نمایش شمسی)

این‌ها در `docs/handoffs/current-state.md` و backlog ثبت شده‌اند.

---

## ساختار

```text
AGENTS.md              قرارداد اجرایی ایجنت‌ها (حالت‌ها، قواعد، DoD)
.agent/                نقش‌ها، پلی‌بوک‌ها، قالب‌ها، ابزارها، context محصول
app/                   FastAPI app (routes, scoring, repo, seed, templates, static)
db/migrations/         اسکیمای SQLite (نسخه‌دار)
tests/                 تست‌های دامنه/جریان/دسترسی/تقویم
docs/                  مستندات محصول، معماری، API، تصمیم‌ها، handoff
```

نقاط ورود مهم: `app/main.py` (مسیرها)، `app/scoring.py` (موتور امتیاز)، `app/repo.py` (داده و دسترسی)،
`db/migrations/0001_init.sql` (اسکیما).

---

## تصمیم‌های کلیدی

| موضوع | وضعیت |
|---|---|
| FastAPI + SQLite برای Prototype | `PROPOSED` — ADR-0001 |
| یک tenant (گلرنگ) با فیلد سازمان | `ASSUMPTION` (OD-02) |
| ورود شبیه‌سازی‌شده | `ASSUMPTION` (OD-01) |
| امتیاز مأموریت ثابت، مقادیر نمونه | `SAMPLE` (OD-04/05) |
| کیف امتیاز غیرقابل مصرف | `ASSUMPTION` (OD-08) |
| tie-break: امتیاز سپس زمان | `PROPOSED` (BR-009) |

جزئیات: `docs/decisions/decision-log.md` و `docs/decisions/open-decisions.md`.

## ایمنی داده

- تمام داده‌های seed با برچسب **نمونه/Demo** در UI.
- هیچ secret واقعی در repo؛ `.env` در git نیست. `KILOOS_SECRET` در محیط‌های غیر dev الزامی است.
- شواهد تصویری در مسیر خصوصی و فقط برای مالک/اپراتور همان سازمان قابل دریافت است.
- تاریخچه امتیاز حذف/ویرایش نمی‌شود؛ اصلاح = رخداد جدید (پیاده‌سازی اصلاح در فاز Harden).

## مستندات

`docs/README.md` نقشه کامل است. شروع سریع: `docs/handoffs/current-state.md`،
`docs/engineering/api-spec.md`، `docs/engineering/scoring-engine.md`، `docs/architecture/database-erd.md`.

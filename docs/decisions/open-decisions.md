# Open Decisions & Business Questions

> وضعیت‌های مجاز: `APPROVED` · `PROPOSED` · `ASSUMPTION` · `OPEN` · `IMPLEMENTED` · `DEPRECATED`.
> تصمیم کسب‌وکار را به‌جای کارفرما نهایی نکن. هر فرض موقت باید کم‌ریسک و قابل بازگشت باشد.

منبع seed: `Kiloos Club — Product Strategy & Scope v0.1 (docs 01–12)` — تولید: 2026-11-09

## OD-01 — روش ورود

- Status: OPEN
- Owner: کارفرما
- Needed by: MS-03
- Impact: Access, UX, Deadline

**سؤال:** ورود با موبایل + OTP، شناسه پرسنلی، یا ترکیبی؟

**فرض موقت فعلی (ASSUMPTION):** OTP شبیه‌سازی‌شده در محیط Demo؛ لایه احراز هویت جدا تا سوئیچ به provider واقعی

**تصمیم نهایی:** —

---

## OD-02 — ساختار سازمانی

- Status: OPEN
- Owner: کارفرما
- Needed by: MS-03
- Impact: Access, Reporting, Leaderboard

**سؤال:** شرکت، شعبه، شهر و تیم چگونه تعریف می‌شوند؟

**فرض موقت فعلی (ASSUMPTION):** یک tenant با فیلد organization_id و سلسله‌مراتب ساده در مدل داده

**تصمیم نهایی:** —

---

## OD-03 — نمونه فایل فروش

- Status: OPEN
- Owner: کارفرما
- Needed by: Phase 3
- Impact: Sales data, Points

**سؤال:** فایل نمونه و فرهنگ داده فروش چیست؟

**فرض موقت فعلی (ASSUMPTION):** قرارداد اولیه در playbooks/sales-import.md با فایل نمونه برچسب‌دار

**تصمیم نهایی:** —

---

## OD-04 — فرمول امتیاز فروش

- Status: OPEN
- Owner: کارفرما
- Needed by: Phase 3
- Impact: Points, Money, Fairness

**سؤال:** امتیاز بر اساس حجم، تعداد مشتری، یا ترکیب شاخص‌ها؟

**فرض موقت فعلی (ASSUMPTION):** قانون Per-Unit نمونه با مقدار SAMPLE؛ موتور configurable

**تصمیم نهایی:** —

---

## OD-05 — SKUهای هدف

- Status: OPEN
- Owner: کارفرما
- Needed by: Phase 3
- Impact: Points, Business

**سؤال:** کدام محصولات و با چه ضرایبی امتیاز ویژه دارند؟

**فرض موقت فعلی (ASSUMPTION):** بدون ضریب ویژه در MVP؛ فیلد sku_code ذخیره می‌شود

**تصمیم نهایی:** —

---

## OD-06 — اعتبارسنجی مأموریت

- Status: OPEN
- Owner: مشترک (کارفرما + محصول)
- Needed by: Phase 2
- Impact: Points, Operations

**سؤال:** کدام مأموریت‌ها خودکار و کدام دستی تأیید شوند؟

**فرض موقت فعلی (ASSUMPTION):** تأیید دستی اپراتور؛ auto-approve خاموش و configurable

**تصمیم نهایی:** —

---

## OD-07 — معیار رقابت

- Status: OPEN
- Owner: مشترک
- Needed by: Phase 4
- Impact: Points, Fairness

**سؤال:** معیار رتبه‌بندی فردی و گروهی چیست؟

**فرض موقت فعلی (ASSUMPTION):** مجموع امتیاز دوره؛ tie-breaker موقت: امتیاز سپس زمان

**تصمیم نهایی:** —

---

## OD-08 — کیف امتیاز

- Status: OPEN
- Owner: کارفرما
- Needed by: Phase 2
- Impact: Money, Points, Legal

**سؤال:** امتیاز صرفاً نمایشی است یا قابلیت مصرف دارد؟

**فرض موقت فعلی (ASSUMPTION):** غیرقابل مصرف و غیرمالی؛ هیچ تعهد برداشت ایجاد نمی‌شود

**تصمیم نهایی:** —

---

## OD-09 — مشارکت خانواده

- Status: OPEN
- Owner: مشترک
- Needed by: post-MVP
- Impact: Scope, UX, Privacy

**سؤال:** خانواده در چه فعالیت‌هایی مشارکت می‌کند؟

**فرض موقت فعلی (ASSUMPTION):** خارج از MVP؛ هیچ داده خانوادگی جمع‌آوری نمی‌شود

**تصمیم نهایی:** —

---

## OD-10 — سرپرست فروش

- Status: OPEN
- Owner: کارفرما
- Needed by: Phase 2
- Impact: Access, Scope

**سؤال:** آیا سرپرست فروش در MVP دسترسی مستقل دارد؟

**فرض موقت فعلی (ASSUMPTION):** نقش تعریف می‌شود اما داشبورد تیمی به بعد از MVP موکول است

**تصمیم نهایی:** —

---

## OD-11 — یکپارچگی

- Status: OPEN
- Owner: کارفرما
- Needed by: Phase 3
- Impact: Scope, Sales data, Deadline

**سؤال:** کدام ERP یا سامانه فروش در اولویت است؟

**فرض موقت فعلی (ASSUMPTION):** فقط ورود فایل در MVP؛ بدون اتصال زنده

**تصمیم نهایی:** —

---

## OD-12 — ظرفیت

- Status: OPEN
- Owner: مشترک
- Needed by: before Scale
- Impact: Architecture, Cost, Performance

**سؤال:** تعداد کاربران هم‌زمان و الگوی مصرف مورد انتظار چیست؟

**فرض موقت فعلی (ASSUMPTION):** طراحی برای ۱٬۵۰۰ کاربر؛ بدون ادعای ظرفیت بالاتر تا آزمون بار

**تصمیم نهایی:** —

---

## تصمیم‌های باز معماری

- [ ] Backend framework
- [ ] Mobile technology
- [ ] Database engine
- [ ] Sales data contract and record unique key
- [ ] Authentication method
- [ ] Hosting location
- [ ] Evidence retention policy
- [ ] Queue / async processing tool
- [ ] SLA, RPO, RTO
- [ ] Company/org access levels
- [ ] Scoring rule versioning and correction policy
- [ ] Reporting and analytics requirements

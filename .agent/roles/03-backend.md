# نقش ۰۳ — Backend

> مرجع: `AGENTS.md` §6 · `CONTEXT.md` §5–§8 · `playbooks/scoring-and-rules.md`

## مأموریت
پیاده‌سازی دامنه، API و داده به‌گونه‌ای که **امتیاز قابل توضیح**، **بدون تکرار** و **قابل audit** باشد.

## قبل از شروع بخوان
کد موجود حوزه · migrationهای قبلی · `docs/engineering/api-spec.md` · `docs/architecture/database-erd.md` · قوانین BR مرتبط

## مالکیت فایل
`backend/**` (یا معادل repo) · `db/migrations/**` · تست‌های دامنه/API

## قرارداد خروجی هر برش
- endpoint + schema ورودی/خروجی + کدهای خطا (`409` تکراری، `422` اعتبارسنجی، `403` محدوده)
- مهاجرت نسخه‌بندی‌شده (در صورت تغییر داده)
- تست: unit دامنه + integration با DB + API
- ثبت تصمیم/فرض در handoff

## قواعد سخت دامنه

### امتیاز
- `ScoreEvent(append-only)`: `id`, `user_id`, `source_type`, `source_id`, `rule_code`, `rule_version_id`, `points`, `occurred_at`, `idempotency_key`, `created_at`.
- مسیر تولید امتیاز: **validate → idempotency → یافتن نسخه قانون فعال → ارزیابی شرایط → محاسبه → تراکنش (event + projection + transaction) → outbox**.
- Unique constraint روی `idempotency_key` **و** روی `(source_type, source_id, rule_code, rule_version_id)`.
- اصلاح/برگشت: رویداد جدید با `corrects_event_id` و دلیل؛ حذف/UPDATE ممنوع.
- محاسبه باید **قابل توضیح** باشد: خروجی شامل `explain` (قانون، شرایط، ورودی‌ها، نسخه).
- اعداد پولی/امتیازی: `NUMERIC`؛ مبلغ اعشاری با float ممنوع.

### مأموریت و submission
- نمایش و ثبت طبق BR-001/BR-002؛ سقف تعداد و شرایط در سرور اعمال شود.
- وضعیت‌ها: `draft → submitted → in_review → approved | rejected` (گذارفازها صریح، بدون پرش).
- رد = دلیل الزامی؛ تأیید = فقط با مجوز نقش/محدوده.

### داده فروش
- Import با وضعیت (`created → uploaded → validated → processing → completed | failed`)، شمارش رکورد/خطا، fingerprint فایل.
- dedupe در سطح رکورد با شناسه خارجی؛ نتیجه قابل گزارش.

### امنیت و دسترسی
- `permission` + `organization_scope` در لایه سرویس اجباری است.
- شواهد: bucket خصوصی، URL امضاشده کوتاه‌عمر، نوع/حجم فایل اعتبارسنجی شود.
- عملیات مدیریتی (تأیید، تغییر قانون، اصلاح امتیاز، import) → audit log.

## همکاری
- با **Architect**: قرارداد و ADR.
- با **Frontend**: schema واقعی + خطاهای واقعی، نه mock نهایی.
- با **QA**: داده طلایی امتیاز و سناریوی idempotency.

## Definition of Done نقش
- [ ] تست‌های دامنه و API اجرا و سبز.
- [ ] مهاجرت روی DB خالی و DB دارای داده تست شده.
- [ ] idempotency و کنترل تکراری تست دارد.
- [ ] دسترسی/محدوده سازمانی تست منفی دارد (403).
- [ ] audit و explain در مسیر امتیاز موجود است.
- [ ] API spec به‌روز است.

## اشتباهات رایج
- نگه‌داشتن موجودی به‌عنوان منبع حقیقت.
- `UPDATE` روی تاریخچه امتیاز.
- اعتبارسنجی فقط در کلاینت.
- محاسبه امتیاز در serializer/کنترلر بدون دامنه قابل تست.

## پرامپت نقش (کپی)
```text
نقش تو Backend است. برش را از دامنه شروع کن: قواعد BR مرتبط، مدل داده، سرویس، سپس API.
امتیاز فقط به شکل ScoreEvent append-only با idempotency_key و unique constraint تولید می‌شود؛
موجودی projection است؛ اصلاح = رویداد اصلاحی. تراکنش event+projection+transaction و outbox.
دسترسی و محدوده سازمانی سمت سرور. تست unit + integration + API را واقعاً اجرا کن و خروجی بده.
```

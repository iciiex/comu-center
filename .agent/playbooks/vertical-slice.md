# پلی‌بوک — برش عمودی (Vertical Slice)

هدف: تحویل **یک قابلیت کامل و قابل اثبات** در هر چرخه، نه چند لایه نیمه‌کاره.

---

## ۱. برش را تعریف کن

یک برش خوب:

- از **یک اقدام کاربر** شروع می‌شود («اپراتور submission را تأیید می‌کند»).
- تا **اثر قابل مشاهده** می‌رود («امتیاز در کیف کاربر و رتبه‌بندی دیده می‌شود»).
- شامل **همه لایه‌ها** است: UI → API → دامنه → DB → تست.
- در **یک نشست** قابل اتمام است (حداکثر ۱–۲ روز).
- یک **معیار پذیرش** روشن دارد.

برش بد: «همه جدول‌ها را بسازیم»، «همه endpointها را بزنیم»، «فرانت را کامل کنیم».

---

## ۲. قرارداد اول (Contract-first)

قبل از کد، این‌ها را در پلن بنویس (و در `docs/engineering/api-spec.md` ثبت کن):

```text
ACTION: اپراتور submission را تأیید می‌کند
METHOD/PATH: POST /api/v1/admin/submissions/{id}/approve
AUTH: role=operator|admin, scope=organization
INPUT: { decision: "approve", note?: string }
SUCCESS: 200 { success:true, data:{ submission_id, status:"approved", score_event_id, points } }
ERRORS:
  403 خارج از محدوده/نقش
  404 submission ناموجود
  409 قبلاً تأیید/رد شده (idempotent → همان نتیجه)
  422 وضعیت نامعتبر برای تأیید
SIDE EFFECTS: submission_reviews, score_event, point_transaction, wallet projection, audit_log, outbox
TEST: approve → +10؛ approve دوباره → بدون امتیاز جدید؛ reject → 0؛ کاربر غیرمجاز → 403
```

---

## ۳. ترتیب ساخت

1. **تست پذیرش** (حتی ساده/اسکلت) — رفتار مورد انتظار را قفل کن.
2. **دامنه**: موجودیت/سرویس/قاعده. بدون HTTP.
3. **مهاجرت**: جدول/ستون/index لازم.
4. **API**: validation، auth، خطاها.
5. **UI**: حالت‌ها + اتصال واقعی.
6. **تست‌های تکمیلی**: منفی، مرز، idempotency.
7. **مستند + handoff**.

---

## ۴. معیار «تمام» برش

- [ ] اقدام کاربر از UI تا DB کار می‌کند.
- [ ] خطاهای اصلی پیام و کد درست دارند.
- [ ] نقش و محدوده سازمانی سمت سرور اعمال شده.
- [ ] اثر جانبی (امتیاز/audit/outbox) کامل است.
- [ ] تست‌ها اجرا شده‌اند.
- [ ] سند و `current-state` به‌روز است.
- [ ] اگر چیزی mock است، برچسب و شرط خروج دارد.

---

## ۵. ضدالگوها

| ضدالگو | چرا بد است | جایگزین |
|---|---|---|
| ساخت همه جدول‌ها قبل از یک صفحه | بازخورد دیر می‌رسد | جدول فقط برای برش فعلی |
| mock دائمی در مسیر اصلی | ادعای کاذب قابلیت | mock با برچسب + تسک خروج |
| «بعداً تست می‌نویسم» | بدهی امنیتی/امتیازی | تست پذیرش قبل از پیاده‌سازی |
| برش غول‌آسا | ریسک و ادغام سخت | برش‌های ۱–۲ روزه |
| جدا کردن فرانت/بک‌اند در زمان | قرارداد drift | قرارداد اول، سپس موازی |

---

## ۶. الگوی پیام commit / PR

```
feat(scoring): score mission approval with idempotent score event

Slice: operator approves photo mission → score event → wallet projection
IDs: MVP-06, MVP-07, BR-003, BR-004, EP-05, EP-06
Contract: POST /admin/submissions/{id}/approve (approve|reject)
Verified: pytest tests/test_scoring.py -q → 12 passed; ruff → clean
Docs: api-spec, scoring-engine, current-state updated
```

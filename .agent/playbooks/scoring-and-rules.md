# پلی‌بوک — موتور امتیاز و قوانین

> این حوزه **پرمخاطره‌ترین** بخش محصول است. هر تغییر اینجا نیاز به تست طلایی، تصمیم ثبت‌شده و بازبینی دارد.

---

## ۱. مدل ذهنی

```
Event (چی اتفاق افتاد) → Rule Version (با چه قانونی) → Score Event (append-only)
        → Point Transaction (ledger) → Wallet Projection (فقط نمایش) → Leaderboard
```

- **منبع حقیقت:** `score_events`. موجودی کیف، جمع محاسبه‌شده است.
- **بدون منبع، امتیاز وجود ندارد:** هر Score Event باید `source_type` + `source_id` داشته باشد.
- **بدون نسخه قانون، امتیاز وجود ندارد:** `rule_code` + `rule_version_id`.
- **بدون idempotency، امتیاز خطرناک است.**

---

## ۲. قرارداد داده پیشنهادی

```text
scoring_rules        : id, code, event_type, status, created_by, created_at
scoring_rule_versions: id, rule_id, version, conditions(jsonb), calculation_type,
                       calculation_config(jsonb), effective_from, effective_to,
                       priority, status(draft|published|retired), published_at
score_events         : id, user_id, source_type, source_id, rule_code, rule_version_id,
                       points(numeric), occurred_at, idempotency_key(unique),
                       corrects_event_id(nullable), reason, created_at
point_transactions   : id, user_id, score_event_id, amount(numeric), direction,
                       balance_after(nullable), created_at
```

Unique constraints پیشنهادی:

```sql
CREATE UNIQUE INDEX ux_score_events_idem ON score_events (idempotency_key);
CREATE UNIQUE INDEX ux_score_events_source
  ON score_events (source_type, source_id, rule_code, rule_version_id)
  WHERE corrects_event_id IS NULL;
```

---

## ۳. الگوریتم (اجباری)

```text
1. validate(event)                         # نوع، مالک، زمان، داده الزامی
2. key = idempotency_key(event)            # ثابت و قابل بازتولید
3. if exists(score_event by key): return existing    # نه خطا، نه امتیاز جدید
4. rule = find_applicable_rule(event.type, event.occurred_at)
   if none: record_unmatched(event); return
5. if not conditions_match(rule, event): record_no_match(event, rule); return
6. points = calculate(rule, event)          # NUMERIC، نه float
7. BEGIN
     insert score_event(...)
     upsert wallet_projection(+points)
     insert point_transaction(...)
     insert outbox_event(score.posted, ...)
     insert audit_log(...)                  # اگر اقدام مدیریتی است
   COMMIT
8. return { score_event, points, explain }
```

`explain` حداقل شامل: `rule_code`, `rule_version`, شرط‌های ارزیابی‌شده، ورودی محاسبه، خروجی.

---

## ۴. انواع محاسبه

| نوع | کاربرد | وضعیت MVP |
|---|---|---|
| `fixed` | امتیاز ثابت مأموریت | پیشنهادی برای P |
| `per_unit` | امتیاز به ازای واحد فروش | `PROPOSED` (وابسته OD-04) |
| `percentage` | درصدی از مقدار | `OPEN` |
| `target_achievement` | تحقق تارگت | `OPEN` |
| `tiered` | پلکانی | `OPEN` |
| `multiplier` | ضریب تشویقی | `OPEN` |

هر نوع فعال، نیاز به تست طلایی مستقل دارد.

---

## ۵. idempotency — سه لایه

1. **کلید منطقی:** مثلاً `mission.approved:{submission_id}` یا `sales.imported:{import_id}:{external_id}`.
2. **Unique constraint** در DB (ضامن نهایی).
3. **کنترل منبع:** یک منبع تأییدشده نمی‌تواند دو بار امتیاز بدهد، حتی با کلید متفاوت.

نتیجه تکراری: پاسخ موفق/تعارض با همان نتیجه قبلی — **نه** امتیاز دوم.

---

## ۶. اصلاح، برگشت، محاسبه مجدد

| عمل | روش | ممنوع |
|---|---|---|
| اصلاح اشتباه محاسبه | رویداد اصلاحی با `corrects_event_id` + دلیل | UPDATE/DELETE رویداد |
| برگشت تأیید | رویداد معکوس + بازگشت وضعیت submission | حذف امتیاز از تاریخچه |
| تغییر قانون | نسخه جدید با `effective_from` | بازنویسی امتیاز گذشته |
| محاسبه مجدد دوره | job با شناسه و گزارش، رویدادهای اصلاحی | پاک‌کردن و بازسازی خاموش |

هر اصلاح، audit + دلیل + مالک دارد.

---

## ۷. تست طلایی (Golden Tests)

برای هر قانون، یک فایل داده ثابت:

```json
{
  "rule_code": "MISSION_PHOTO_FIXED",
  "status": "PROPOSED",
  "cases": [
    {"name": "approve_once", "input": {"event": "mission.approved", "mission_type": "photo_submission", "submission_id": "S1"},
     "expect": {"points": "10", "events_created": 1}},
    {"name": "approve_twice_idempotent", "input": {"event": "mission.approved", "submission_id": "S1"},
     "expect": {"points": "10", "events_created": 0, "same_event": true}},
    {"name": "reject_no_points", "input": {"event": "mission.rejected", "submission_id": "S2"},
     "expect": {"points": "0", "events_created": 0}},
    {"name": "inactive_user_blocked", "input": {"event": "mission.approved", "user_active": false},
     "expect": {"error": "USER_INACTIVE"}}
  ]
}
```

> عدد ۱۰ `SAMPLE` است. تست باید مقدار را از قانون بخواند، نه hard-code؛ اما برای قانون نمونه، assertion ثابت معتبر است.

---

## ۸. تغییر قانون — چک‌لیست

- [ ] تصمیم کسب‌وکار `APPROVED` در decision-log (یا `ASSUMPTION` با تایم‌لاین).
- [ ] نسخه جدید ساخته شد؛ نسخه قبلی `retired` با `effective_to`.
- [ ] سناریوی «امتیاز گذشته تغییر نکرد» تست شد.
- [ ] تست طلایی نسخه جدید اضافه شد.
- [ ] مستندات: scoring-engine، rule matrix، API، handoff.
- [ ] اعلام اثر روی leaderboard و گزارش‌ها.

---

## ۹. ضدالگوها

- محاسبه امتیاز در UI یا در serializer.
- ذخیره موجودی به‌عنوان عدد مستقل و قابل ویرایش.
- `float` برای امتیاز/مبلغ.
- idempotency با `if not exists` بدون unique constraint.
- قانون hard-code بدون نسخه.
- حذف رویداد برای «تمیزکاری».

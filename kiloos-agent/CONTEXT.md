# CONTEXT.md — دانسته‌های تثبیت‌شده پروژه Kiloos Club

> این فایل **فشرده‌ی قابل‌اتکا**ی اسناد محصول است، نه جایگزین آن‌ها.
> **منبع اصلی:** Google Drive → «Kiloos Club — Product Strategy & Scope» (نسخه ۰.۱، آبان ۱۴۰۵) که شامل اسناد ۰۱ تا ۱۲ است.
> **قاعده:** هرچه در این فایل با `PROPOSED` یا `⚠` علامت خورده، مصوبه نیست. تنها `docs/decisions/decision-log.md` می‌تواند چیزی را `APPROVED` کند.
> **آخرین تطبیق:** ۱۸ آبان ۱۴۰۵

---

## ۱. محصول در یک نگاه

| مورد | مقدار |
|---|---|
| نام محصول | Kiloos Club (کیلوس کلاب) — پلتفرم گیمیفیکیشن و انگیزش تیم فروش گروه گلرنگ |
| مسئله | نبود بستر یکپارچه و مستمر برای انگیزه و مدیریت عملکرد شبکه فروش؛ ارتباط عمدتاً مبتنی بر قیمت/بونس/تخفیف مقطعی |
| چرخه اصلی | فعالیت → ثبت و تأیید → امتیاز → پیشرفت → رقابت → پاداش |
| جامعه فاز اول | ~۱٬۵۰۰ نفر از تیم فروش مویرگی (`PROPOSED` — توزیع سازمانی تأیید نشده) |
| افق مقیاس | ۱۳۰–۱۴۰ هزار کاربر (هدف معماری، **نه** ظرفیت اثبات‌شده) |
| اصل راهبردی | گیمیفیکیشن ابزار مدیریت عملکرد و انگیزش است، نه هدف مستقل محصول |

**اهداف کسب‌وکار:** G-01 افزایش عملکرد فروش · G-02 مشارکت · G-03 فروش محصولات هدف · G-04 وفاداری · G-05 یکپارچگی اطلاعات · G-06 توسعه‌پذیری.

**اصل معماری پیشنهادی:** Modular Monolith برای MVP؛ microservice فقط با شواهد بار/مالکیت/مرز دامنه.

---

## ۲. کاربران و نقش‌ها

| نقش | توضیح | وضعیت MVP |
|---|---|---|
| ویزیتور (Visitor) | کاربر اصلی؛ انجام مأموریت | ضروری |
| مدیر سیستم (Admin) | کاربران، مأموریت‌ها، تنظیمات | ضروری |
| اپراتور (Operator) | بررسی/تأیید فعالیت‌ها | `PROPOSED` |
| سرپرست فروش (Sales Supervisor) | مشاهده/مدیریت عملکرد تیم | `OPEN` (OD-10) |
| مدیر کسب‌وکار (Business Manager) | گزارش‌ها و شاخص‌ها | `PROPOSED` |

نقش‌های پنل مدیریت (پیشنهادی، قابل پیکربندی): Super Admin · Admin · Operator · Sales Manager · Business Manager · Analyst.
**مدل دسترسی:** `Permission × Organization Scope` — نه فقط نقش.

---

## ۳. محدوده MVP

### داخل محدوده

| ID | قابلیت | اولویت |
|---|---|---|
| MVP-01 | احراز هویت | ضروری |
| MVP-02 | پروفایل کاربر | ضروری |
| MVP-03 | داشبورد کاربر (امتیاز، مأموریت، پیشرفت) | ضروری |
| MVP-04 | مدیریت مأموریت (تعریف/انتشار) | ضروری |
| MVP-05 | ثبت فعالیت + شواهد | ضروری |
| MVP-06 | تأیید/رد فعالیت | ضروری |
| MVP-07 | موتور امتیازدهی | ضروری |
| MVP-08 | ورود داده فروش از فایل | ضروری |
| MVP-09 | رتبه‌بندی | ضروری |
| MVP-10 | رقابت گروهی | مهم |
| MVP-11 | پنل مدیریت | ضروری |
| MVP-12 | گزارش عملکرد پایه | مهم |
| MVP-13 | تاریخچه امتیازات | مهم |

### خارج از محدوده (در MVP نه)

کیف پول مالی واقعی · خرید آنلاین با توکن · تسویه/تبدیل توکن به پول · اتصال کامل و لحظه‌ای به تمام ERPها · توسعه به تمام شرکت‌های گروه · ورود مشتری/مصرف‌کننده نهایی · اپلیکیشن مستقل خانواده · بازی پیچیده با گرافیک اختصاصی · تحلیل‌های پیشرفته هوشمند.

### MoSCoW

- **Must:** ورود، مدیریت کاربران، داشبورد پایه، مأموریت، ثبت، تأیید، امتیازدهی، ورود فایل فروش، رتبه‌بندی پایه.
- **Should:** تاریخچه امتیاز، گزارش مدیریتی، رقابت گروهی، پیشرفت تارگت، گزارش خطای فایل.
- **Could:** مشارکت خانواده، دستاورد/نشان، بازی جانبی، اعلان پیشرفته.
- **Won't (MVP):** موارد جدول «خارج از محدوده».

---

## ۴. ماژول‌ها

`MOD-01` Auth & User Management · `MOD-02` User Profile · `MOD-03` Mission Management · `MOD-04` Mission Execution · `MOD-05` Verification · `MOD-06` Scoring Engine · `MOD-07` Sales Data Integration · `MOD-08` Leaderboard & Competition · `MOD-09` Rewards & Point Wallet · `MOD-10` Admin Dashboard · `MOD-11` Reporting.

نیازمندی‌های عملکردی با شناسه `FR-xxx` در سند PRD تعریف شده‌اند (از `FR-001` شروع می‌شوند). در کد و تست، شناسه `FR` را در نام تست/کامیت ذکر کن.

---

## ۵. قوانین کسب‌وکار (BR) — خلاصه اجرایی

| ID | قانون |
|---|---|
| BR-001 | نمایش مأموریت فقط با: وضعیت Active + داخل بازه زمانی + عضویت در جامعه هدف + عدم نقض محدودیت دسترسی |
| BR-002 | ثبت فعالیت فقط با: مأموریت فعال + کاربر واجد شرایط + عدم عبور از سقف تعداد + تکمیل اطلاعات الزامی |
| BR-003 | امتیاز فقط پس از تحقق شرایط معتبر؛ برای مأموریت نیازمند بررسی، پس از تأیید |
| BR-004 | هر فعالیت شناسه یکتا دارد؛ برای یک فعالیت تأییدشده بیش از یک بار امتیاز ایجاد نمی‌شود |
| BR-005 | همه تغییرات امتیاز رویداد مستقل و append-only هستند؛ حذف/بازنویسی ممنوع، اصلاح با رویداد اصلاحی |
| BR-006 | رد فعالیت: وضعیت Rejected + ثبت دلیل + بدون امتیاز |
| BR-007 | امتیاز فروش با قوانین قابل تنظیم؛ فرمول دقیق `OPEN` (OD-04) |
| BR-008 | رتبه‌بندی بر امتیازهای معتبر در بازه مشخص؛ امتیاز لغوشده/اصلاح‌شده درست محاسبه شود |
| BR-009 | تساوی امتیاز: tie-breaker — ترتیب پیشنهادی: امتیاز مأموریت‌های کلیدی ← زمان زودتر رسیدن ← معیار مصوب. **تأییدنشده** |
| BR-010 | فایل فروش: شناسه پردازش، گزارش رکورد نامعتبر، بدون امتیاز تکراری، قابل پیگیری، اصلاح با تاریخچه |
| BR-011 | قوانین امتیاز تاریخ اعتبار دارند؛ تغییر قانون امتیاز گذشته را بازنویسی نمی‌کند؛ هر نسخه شناسه دارد |
| BR-012 | کاربر غیرفعال نمی‌تواند مأموریت جدید ثبت کند؛ سوابق و امتیاز حفظ می‌شود |
| BR-013 | هر رقابت: جامعه هدف + بازه زمانی + معیار رتبه‌بندی مشخص |
| BR-014 | موجودی کیف = مجموع رویدادهای معتبر؛ امتیاز داخلی پول/اعتبار قابل برداشت نیست |

---

## ۶. مدل داده

**موجودیت‌های مفهومی:** User · Role · Organization · Team · Mission · Mission Audience · Mission Submission · Submission Evidence · Scoring Rule · Score Event · Point Wallet · Sales Import · Sales Record · Competition · Leaderboard · Audit Log.

**دامنه‌های جدول‌ها (پیشنهادی):**

| دامنه | جداول |
|---|---|
| Identity & Access | users, roles, permissions, user_roles, role_permissions |
| Organization | organizations, user_organization_assignments |
| Mission | missions, mission_audiences, mission_rules |
| Submission | mission_submissions, submission_evidences, submission_reviews |
| Scoring | scoring_rules, scoring_rule_versions, score_events |
| Wallet | point_wallets, point_transactions |
| Sales | sales_sources, sales_imports, sales_records, sales_import_errors |
| Competition | competitions, competition_participants, leaderboard_snapshots |
| Audit | audit_logs, idempotency_records |

**قواعد داده:** UUID برای جداول اصلی · `NUMERIC` برای مقادیر مالی/امتیازی (نه float) · تاریخ‌ها با timezone · soft delete در موجودیت‌های منتخب · رخداد امتیاز append-only · قوانین versioned · فایل‌ها در Object Storage · تنظیمات JSONB.

---

## ۷. موتور امتیازدهی

**ورودی‌های رویداد:** `Mission Approved` · `Sales Record Imported` · `Target Achieved` · `Team Performance Event` (دو مورد آخر: `PROPOSED` برای MVP).
**خروجی:** `Score Event` · `Point Transaction` · `Leaderboard Update Event`.

**Rule schema (الزامی):** `rule_code` · `event_type` · `conditions` · `calculation.type` · `calculation.config` · `effective_from/effective_to` · `priority` · `version` · `status`.

**انواع محاسبه پیشنهادی:** Fixed Points · Per Unit · Percentage · Target Achievement · Tiered · Multiplier. (فعال‌بودن هرکدام در MVP: `OPEN`)

**جریان محاسبه:** Validate → Idempotency Key → بررسی تکراری → یافتن نسخه قانون فعال → ارزیابی شرایط → محاسبه → (تراکنش) Score Event + projection + transaction → انتشار رویداد (Outbox) → به‌روزرسانی Leaderboard.

**اصلاح:** رویداد قبلی حذف نمی‌شود؛ رویداد اصلاحی + دلیل ثبت می‌شود.

**نمونه قانون (SAMPLE — نه مصوبه):** `context/scoring-rule.sample.json` (مأموریت عکس، ۱۰ امتیاز ثابت، `status: PROPOSED`).

**وزن‌های پیشنهادی منابع (PROPOSED، ۰۶-A):** مأموریت ۲۰٪ · فروش ۵۰٪ · تحقق تارگت ۲۰٪ · پاداش ویژه ۱۰٪. این‌ها وزن طراحی مدل‌اند، نه ضریب مستقیم هر رویداد.

---

## ۸. API (پیشنهادی، `/api/v1`)

| گروه | endpointها |
|---|---|
| Auth | `POST /auth/login` · `POST /auth/logout` · `POST /auth/refresh` · `GET /me` |
| Mission | `GET /missions` · `GET /missions/{id}` · `POST /admin/missions` · `PUT /admin/missions/{id}` · `POST /admin/missions/{id}/publish` · `POST /missions/{id}/submissions` · `GET /submissions/{id}` |
| Verification | `GET /admin/submissions` · `GET /admin/submissions/{id}` · `POST /admin/submissions/{id}/approve` · `POST /admin/submissions/{id}/reject` |
| Scoring | `GET /scores/me` · `GET /scores/me/history` · `GET /admin/scoring-rules` · `POST /admin/scoring-rules` · `POST /admin/scoring-rules/{id}/versions` · `POST /admin/scoring-rules/{id}/publish` |
| Sales Import | `POST /admin/sales-imports` · `POST /admin/sales-imports/{id}/file` · `POST .../validate` · `POST .../process` · `GET .../{id}` · `GET .../{id}/errors` |
| Leaderboard | `GET /leaderboards` · `GET /leaderboards/{id}` · `GET /leaderboards/{id}/me` |

**قرارداد پاسخ:** `{success, data, meta}` / `{success:false, error:{code,message,details}}`.
**HTTP:** 200/201/202/400/401/403/404/409/422. عملیات حساس: `Idempotency-Key`.
**قاعده:** ثبت Score Event از API عمومی کاربر عادی در دسترس نیست؛ فقط فرآیندهای داخلی معتبر.

---

## ۹. UX و پنل مدیریت

**اپ لیست (Bottom Navigation):** خانه · مأموریت‌ها · رقابت · امتیازهای من · پروفایل.
**مسیر ورود:** موبایل → OTP → بررسی هویت → خانه (روش ورود `OPEN`: OD-01).
**مسیر مأموریت:** انتخاب → توضیحات/شرایط → ثبت مستندات → بازبینی → ارسال → نمایش وضعیت.
**بازخوردهای الزامی:** ثبت شد · در انتظار تأیید · «X امتیاز اضافه شد» · تغییر رتبه · رسیدن به هدف روزانه.

**منوی پنل مدیریت:** داشبورد · کاربران · ساختار سازمانی · مأموریت‌ها · بررسی مأموریت‌ها · امتیازدهی · اطلاعات فروش · رقابت‌ها · گزارش‌ها · مدیریت دسترسی · تنظیمات. هر بخش بر اساس Permission نمایش داده می‌شود.

**اصول UX:** Mobile First · Simplicity · Motivation & Feedback · Transparency («چرا این امتیاز را گرفتم؟») · Consistency (Design System مشترک).

---

## ۱۰. تحویل و فازها

| فاز | محتوا | خروجی |
|---|---|---|
| Phase 0 | Foundation: repo، branching، محیط، اسکلت backend/frontend، DB، CI، design system | توسعه موازی ممکن |
| Phase 1 | Prototype | دموی جریان اصلی |
| Phase 2 | MVP Core | مأموریت → امتیاز عملیاتی |
| Phase 3 | Sales Integration | ورود داده فروش + امتیاز عملکرد + reconciliation |
| Phase 4 | Competition & Reporting | رتبه‌بندی فردی/تیمی + گزارش + اعلان |
| Phase 5 | Stabilization & RC | regression/performance/security/UAT + production |

**اپیک‌ها:** EP-01 Auth & User Mgmt · EP-02 Organization · EP-03 Mission Management · EP-04 Mission Execution · EP-05 Verification · EP-06 Scoring · EP-07 Sales Integration · EP-08 Competition & Leaderboard · EP-09 Admin Panel · EP-10 Reports · EP-11 Notification · EP-12 Infra & DevOps · EP-13 QA.

**Milestoneها:**

| ID | تاریخ | خروجی |
|---|---|---|
| MS-01 Prototype | چهارشنبه ۲۷ آبان ۱۴۰۵ = **2026-11-18** | ارائه Prototype |
| MS-02 Feedback | شنبه ۳۰ آبان ۱۴۰۵ = 2026-11-21 | بازخورد |
| MS-03 MVP Dev | پس از تأیید مسیر | قابلیت‌های اصلی |
| MS-04 RC | پیش از شب یلدا ۱۴۰۵ = 2026-12-21 | نسخه پایدار |
| MS-05 Acceptance | پس از UAT | تحویل |

> **واقعیت امروز:** ۱۸ آبان ۱۴۰۵ / 2026-11-09 → تا MS-01 حدود **۹ روز**. اولویت مطلق: مسیر دموی end-to-end، نه breadth.

---

## ۱۱. KPI (همه پیشنهادی — نه تعهد)

Activation Rate ≥۸۰٪ · WAU ≥۶۰٪ · Mission Completion ≥۷۰٪ · موفقیت ورود داده فروش ≥۹۸٪ · دقت امتیاز ۱۰۰٪ در سناریوهای تست · صفر خطای بحرانی شناخته‌شده در تحویل.
KPIهای کسب‌وکار: Sales Target Achievement · Sales Growth · Product Coverage · Active Customer Growth · Strategic SKU Sales · Visit Productivity.
KPIهای کیفیت: Mission Approval Time · Data Import Success Rate · Scoring Accuracy · Availability · Error Rate · Support Requests.

---

## ۱۲. NFR

- **مقیاس:** طراحی برای ۱٬۵۰۰ کاربر، مسیر رشد تا ۱۳۰–۱۴۰ هزار (بدون ادعای ظرفیت بدون تست بار).
- **امنیت:** احراز هویت امن، RBAC + سازمان، حفاظت داده، محدودسازی اطلاعات شرکت/تیم، audit عملیات حساس.
- **صحت داده:** بدون رویداد تکراری، تاریخچه امتیاز حفظ شود، اعتبارسنجی ورودی، ردیابی منبع هر امتیاز.
- **کارایی:** تجربه موبایل روزمره؛ اهداف عددی در تست بار تعیین شود.
- **دسترس‌پذیری/توسعه‌پذیری:** خطاهای قابل ردیابی؛ افزودن شرکت/نقش/نوع مأموریت/قانون/روش ورود داده/مدل رقابت.

---

## ۱۳. گزینه‌های فناوری (تأییدنشده — `OPEN`)

Mobile: Flutter یا React Native · Admin: React یا Vue · Backend: Laravel یا Java Spring Boot · DB: PostgreSQL · Cache: Redis · Queue: RabbitMQ یا Redis Queue · Storage: S3-compatible · API Docs: OpenAPI · Monitoring: Prometheus + Grafana · Error: Sentry.

> انتخاب نهایی باید ADR داشته باشد. اگر repo موجود، انتخاب تیم را حفظ کن و دوباره‌کاوی نکن.

---

## ۱۴. تصمیم‌های باز (خلاصه — جزئیات در `context/open-decisions.seed.json`)

| ID | موضوع |
|---|---|
| OD-01 | روش ورود: موبایل+OTP یا شناسه پرسنلی |
| OD-02 | ساختار سازمانی (شرکت/شعبه/شهر/تیم) |
| OD-03 | نمونه فایل و فرهنگ داده فروش |
| OD-04 | فرمول امتیاز فروش |
| OD-05 | SKUهای هدف و ضرایب |
| OD-06 | کدام مأموریت خودکار و کدام دستی تأیید شود |
| OD-07 | معیار رتبه‌بندی فردی/گروهی |
| OD-08 | امتیاز نمایشی است یا قابل مصرف |
| OD-09 | مشارکت خانواده |
| OD-10 | دسترسی مستقل سرپرست فروش در MVP |
| OD-11 | اولویت ERP/سامانه فروش |
| OD-12 | ظرفیت و کاربران هم‌زمان |

تصمیم‌های باز معماری: Backend framework · فناوری موبایل · DB · قرارداد داده فروش و شناسه یکتا · روش احراز هویت · محل استقرار · سیاست نگهداری تصاویر · ابزار queue · SLA/RPO/RTO · سطح دسترسی شرکت‌ها · نسخه‌بندی قوانین · نیاز گزارش‌گیری.

---

## ۱۵. واژه‌نامه

| واژه | معنا |
|---|---|
| Mission | مأموریت عملیاتی قابل اجرا با شرایط، شواهد و امتیاز |
| Submission | ثبت انجام مأموریت توسط کاربر |
| Evidence | مدرک (عمدتاً تصویر) پیوست submission |
| Review | بررسی و تأیید/رد submission |
| Score Event | رخداد append-only تولید امتیاز با منبع و نسخه قانون |
| Point Transaction | حرکت ledger کیف امتیاز |
| Projection | موجودی محاسبه‌شده از رویدادها (نه منبع حقیقت) |
| Rule Version | نسخه دارای تاریخ اعتبار از یک قانون امتیاز |
| Import Batch | یک فایل ورودی فروش با شناسه و وضعیت قابل پیگیری |
| Leaderboard Snapshot | رتبه‌بندی محاسبه‌شده برای یک دوره/رقابت |

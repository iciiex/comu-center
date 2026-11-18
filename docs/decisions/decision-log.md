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

---

## D-005 — ورود داده فروش با XLSX، نگاشت صریح و قاعده‌ی مبلغی SAMPLE

- Status: PROPOSED
- Date: 2026-11-09
- Approved by: کارفرما (قالب XLSX در گفتگو انتخاب شد)
- Owners: Product / Data / Engineering
- Related: OD-03 / OD-04 / OD-05 / OD-11 / EP-07

**Decision (موقت):**

1. **قالب ورودی XLSX** است (نه CSV)؛ خواندن با `openpyxl`، حداکثر ۵ مگابایت و ۵٬۰۰۰ ردیف.
2. **فقط `admin`** آپلود و پردازش می‌کند؛ اپراتور و ویزیتور ۴۰۳.
3. **نگاشت ویزیتور صریح** است: `sales_user_map(organization_id, user_external_id) → user_id`.
   حدس زدن از روی شماره موبایل یا نام ممنوع است.
4. **فرمول امتیاز SAMPLE**: `floor(amount / unit_size) * points` با `unit_size=1,000,000` و
   `points=1`. هر دو عدد در `scoring_rule_versions` ذخیره می‌شوند، نه در کد.
5. **آپلود هرگز امتیاز نمی‌سازد**؛ پردازش یک مرحله‌ی صریح و idempotent است.
6. **قاعده بر اساس زمان پردازش** انتخاب می‌شود، نه تاریخ فروش.

**Rationale:** بدون نسخه‌ی اجرایی، موتور امتیاز فقط مأموریت‌محور می‌ماند و ارزش اصلی محصول (عملکرد
فروش) دیده نمی‌شود. جدا کردن validate از score و نگاشت صریح، جلوی امتیاز غلط را می‌گیرد.

**Consequences / موارد باز:**
- ۱٬۰۰۰٬۰۰۰ و «۱ امتیاز» اعداد تجاری نیستند و باید با OD-04 جایگزین شوند؛ تا آن زمان همه‌ی
  رخدادها `is_sample=true` دارند.
- اگر وارد کردن فایل‌های گذشته‌نگر معمول شود، انتخاب قاعده بر اساس `sale_date` باید بازبینی شود.
- ضریب SKU، سقف دوره‌ای و اتصال زنده به ERP (OD-05/OD-11) پیاده نشده است.
- سیاست حذف/نگهداری فایل خام import هنوز تصمیم‌گیری نشده (فقط fingerprint و داده‌ی نرمال‌شده ذخیره می‌شود).

**Affected docs:** `docs/engineering/sales-import.md`، `docs/engineering/api-spec.md`،
`docs/architecture/database-erd.md`، `docs/engineering/scoring-engine.md`،
`docs/quality/qa-test-strategy.md`، `docs/handoffs/current-state.md`

**Exit condition:** Replace the SAMPLE contract and scoring parameters when OD-03 and OD-04 are approved; revisit access, mapping and rule timing with the production import design.

## D-006 — ورود نمایشی بازی در محیط hosted با `KILOOS_ENV=demo` (فقط ویزیتور)

- Status: PROPOSED
- Date: 2026-11-18
- Owners: Engineering / DevOps
- Related: D-002 / OD-01 / C9

**Decision (موقت، ASSUMPTION):** مسیرهای JSON `GET /api/v1/game/demo-users` و `POST /api/v1/game/demo-login`
علاوه بر `dev`/`test` در `KILOOS_ENV=demo` هم فعال‌اند؛ هر محیط دیگر ۴۰۴ می‌دهد. فهرست و ورود فقط
برای نقش `visitor` است (admin/operator همچنان ۴۰۴). در هر محیطی غیر از dev/test کوکی جلسه `Secure` است.

**Rationale:** دمو عمومی باید از ظاهر شدن حساب‌های مدیریتی در انتخابگر جلوگیری کند و کوکی روی HTTPS امن باشد.

**Affected docs:** `docs/engineering/game-bff-alignment.md`، `docs/operations/deploy-render.md`

**Exit condition:** جایگزینی با احراز هویت واقعی (OD-01) یا غیرفعال‌سازی ورود نمایشی پیش از هر کاربر واقعی.

## D-007 — میزبانی دمو: Render (Docker + دیسک پایدار) با SQLite و Vercel rewrite برای فرانت

- Status: PROPOSED
- Date: 2026-11-18
- Owners: DevOps / Engineering
- Related: D-001 / backlog D1, D3

**Decision (موقت):** بک‌اند FastAPI + SQLite روی Render با دیسک پایدار (`/var/data`) و یک worker اجرا می‌شود
(`Dockerfile`، `render.yaml`). فرانت Sales Quest Arena با rewrite همان‌مبدأ روی Vercel به `/api/v1/game/*` وصل می‌شود.
مهاجرت به PostgreSQL (Neon) از محدوده‌ی این sprint خارج و به فاز Harden موکول شد.

**Rationale:** Vercel/Workers فایل‌سیستم پایدار برای SQLite و شواهد ندارند؛ تغییر پایگاه‌داده بدون شواهد ممنوع است (AGENTS §6.12).

**Exit condition:** تصمیم میزبان نهایی (hosting در تصمیم‌های معماری باز) و PostgreSQL/object storage پیش از کاربر واقعی.

## D-008 — ورود کارکنان (operator/admin) در دموی hosted با کد دسترسی

- Status: PROPOSED
- Date: 2026-11-18
- Owners: Engineering
- Related: D-002 / OD-01 / C9

**Decision (موقت، ASSUMPTION):** در هر محیط غیر dev/test، فرم HTML `POST /demo-login` برای حساب غیر visitor فقط
با `access_code` برابر `KILOOS_DEMO_STAFF_CODE` (مقایسه ثابت‌زمان) کار می‌کند؛ نبودن مقدار یعنی ورود کارکنان غیرفعال.
شکست ۴۰۳ است، audit می‌شود و رده‌بندی نرخ ورود اعمال می‌شود. انتخابگر اصلی فقط ویزیتورها را نشان می‌دهد.

**Rationale:** حساب admin نباید از طریق انتخابگر عمومی قابل انتخاب باشد. این احراز هویت واقعی نیست.

**Exit condition:** OD-01 (روش ورود واقعی).

## D-009 — پایگاه‌داده منبع واحد مأموریت‌ها برای بازی؛ دو اقتصاد پاداش جدا

- Status: PROPOSED
- Date: 2026-11-18
- Owners: Engineering
- Related: MVP-04/05/06/07, BR-001, B6-1, B6-2, OD-04/05

**Decision (موقت، ASSUMPTION):**
1. جدول `missions` تنها منبع مأموریت‌هاست؛ مدیر در پنل مأموریت می‌سازد/منتشر می‌کند و بازی (حالت server) همان را از
   BFF می‌خواند. شش مأموریت `game_catalog.json` دیگر فهرست بازیکن در حالت server نیست؛ حالت device-only بدون تغییر است.
2. «منتشر شده» = `status='active'`. مأموریت پیش‌نویس/بایگانی یا هنوز شروع‌نشده دیده نمی‌شود؛ مأموریت منقضی ۳۰ روز با وضعیت
   «منقضی شده» دیده می‌شود و قابل شروع نیست.
3. امتیاز سازمانی فقط در `score_events` (قانون و نسخه قانون فعلی، لحظه تأیید). XP و سکه فقط در `game_reward_events` و
   پروجکشن بازی؛ هرگز به امتیاز سازمانی اضافه نمی‌شوند.
4. XP/سکه هنگام ثبت درخواست روی همان درخواست ثابت می‌شود (snapshot)؛ تغییر بعدی مدیر درخواست‌های قبلی را عوض نمی‌کند.
   پرداخت فقط پس از تأیید (یا هنگام ثبت اگر تأیید لازم نیست)، یک‌بار، در همان تراکنش تأیید.
5. هم‌زمان یک درخواست در انتظار بررسی برای هر کاربر/مأموریت؛ سقف انجام سمت سرور و شامل درخواست‌های ردشده (B6-1 باز).
6. API بازی نسخه‌گذاری شد: v1 پیش‌فرض (سازگاری هنگام deploy) و v2 با هدر `X-Game-Api: 2`.
7. چالش روزانه و دستاوردهای `daily_hero` / `trailblazer` در حالت server/v2 غیرفعال و پنهان‌اند.

**Rationale:** حذف منبع دوم مأموریت، حفظ صحت امتیاز و ردیابی، و جلوگیری از اختلاط دو اقتصاد.

**Exit condition:** تأیید کارفرما روی مقادیر XP/سکه، سقف/بازه، سیاست مأموریت منقضی و جایگزین چالش روزانه (OD-13).

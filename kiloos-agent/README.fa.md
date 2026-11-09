# Kiloos Agent — کیت اپراتور مهندسی محصول

یک «ایجنت خفن» برای ساخت **Kiloos Club** (پلتفرم گیمیفیکیشن و انگیزش تیم فروش گروه گلرنگ)، ساخته‌شده بر پایه‌ی:

- سند «Kiloos Club — Product Strategy & Scope» (نسخه ۰.۱ — شامل اسناد ۰۱ تا ۱۲) در Google Drive
- راهنمای `AGENT_GUIDE_Golrang_Gamification.md`

این کیت، راهنمای عمومی را به یک **سیستم عملیاتی قابل اجرا** تبدیل می‌کند: قرارداد کاری، دانش فشرده محصول، نقش‌های تخصصی، پلی‌بوک‌های اجرایی، قالب‌های سند، و دو ابزار که وضعیت repo را می‌سنجند.

> این پوشه مستقل است. برای استفاده در repo واقعی محصول، محتوای آن را در **ریشه همان repo** کپی کن (یا `tools/bootstrap.py` را اجرا کن).

---

## چرا این کیت با یک «پرامپت خوب» فرق دارد

| پرامپت معمولی | این کیت |
|---|---|
| می‌گوید «خوب کد بزن» | می‌گوید چه چیزی **تأیید نشده** و چه چیزی مصوبه است |
| اعداد نمونه را جدی می‌گیرد | هر عدد را `PROPOSED` می‌داند تا در decision-log تأیید شود |
| مستندات را فراموش می‌کند | جدول «تغییر ↔ سند الزامی» و handoff اجباری دارد |
| در ابهام متوقف یا اختراع می‌کند | پروتکل `ASSUMPTION` / `OPEN` / `BLOCKED` دارد |
| برای همه نقش‌ها یک متن است | ۷ نقش با مالکیت فایل و قرارداد تحویل جدا |

---

## شروع سریع (۳ قدم)

### ۱. نصب در repo محصول

```bash
python3 kiloos-agent/tools/bootstrap.py --target ../kiloos-club
```

این کار در repo مقصد می‌سازد: `AGENTS.md`، `.agent/` (نقش‌ها، پلی‌بوک‌ها، قالب‌ها، context) و `docs/` با اسکلت استاندارد و `current-state` و `open-decisions` seed‌شده.

### ۲. سلامت وضعیت را بسنج

```bash
python3 kiloos-agent/tools/doctor.py --root ../kiloos-club
```

### ۳. شروع کار

- ابزار کدنویسی (Claude Code / Codex / Cursor / Gemini CLI): فقط تسک را بده؛ `AGENTS.md` خودش خوانده می‌شود.
- چت (ChatGPT/Claude): `MASTER_PROMPT.fa.md` را کپی کن، `AGENTS.md` + `CONTEXT.md` را ضمیمه کن.
- تسک نمونه: «برش عمودی مأموریت تصویری تا تأیید و امتیاز را در حالت P بساز.»

---

## نقشه فایل‌ها

| فایل | چه می‌کند |
|---|---|
| `AGENTS.md` | **قرارداد اصلی**: حالت‌های کاری، حلقه ۷ مرحله‌ای، قواعد سخت، DoD، خط قرمزها |
| `CONTEXT.md` | دانش فشرده محصول: محدوده، نقش‌ها، BRها، داده، امتیازدهی، API، فازها، تاریخ‌ها، تصمیم‌های باز |
| `MASTER_PROMPT.fa.md` | پرامپت آماده (فارسی/انگلیسی) برای هر ابزار |
| `roles/*.md` | ۷ نقش تخصصی با مالکیت فایل و Definition of Done |
| `playbooks/prototype-9-days.md` | برنامه روزشمار تا MS-01 + سناریوی دمو + fallback |
| `playbooks/vertical-slice.md` | روش برش end-to-end و قرارداد-اول |
| `playbooks/scoring-and-rules.md` | قرارداد موتور امتیاز، idempotency، تست طلایی، تغییر قانون |
| `playbooks/sales-import.md` | چرخه ورود داده فروش، اعتبارسنجی، dedupe، reconciliation |
| `playbooks/review-and-handoff.md` | بازبینی PR، همکاری چندایجنتی، handoff |
| `templates/*.md` | قالب آماده: current-state، handoff، ADR، open-decision، slice-plan، PR |
| `context/open-decisions.seed.json` | ۱۲ تصمیم باز + فرض‌های پیش‌فرض قابل بازگشت |
| `context/scoring-rule.sample.json` | نمونه قانون امتیاز با برچسب SAMPLE/PROPOSED |
| `tools/bootstrap.py` | نصب کیت + ساخت اسکلت مستندات در repo مقصد |
| `tools/doctor.py` | بررسی سلامت: ساختار، شناسه‌ها، وضعیت تصمیم‌ها، لینک‌ها، الگوهای secret |

---

## سه حالت کاری (خلاصه)

| حالت | کِی | هدف |
|---|---|---|
| **P — Prototype** (پیش‌فرض) | تا MS-01 و تأیید مسیر | دموی end-to-end قابل اجرا، با داده نمونه برچسب‌خورده |
| **H — Harden** | پس از تأیید مسیر | هسته قابل اتکا: امنیت، idempotency، تست، پایش |
| **S — Scale** | پس از baseline و آزمون بار | بهینه‌سازی مبتنی بر اندازه‌گیری |

---

## چند قاعده که بیشترین درد را کم می‌کند

1. **امتیاز = رویداد، نه عدد.** موجودی، projection است؛ ویرایش تاریخچه ممنوع.
2. **هیچ عددی مصوبه نیست** تا در decision-log با `APPROVED` ثبت شود.
3. **Demo از واقعی جدا** است و در UI برچسب دارد.
4. **تست اجرانشده = تست موفق نیست.**
5. **بدون اندازه‌گیری، معماری را عوض نکن.**

---

## نگهداری کیت

- `CONTEXT.md` را بعد از هر تغییر scope/قانون به‌روز کن.
- `context/open-decisions.seed.json` فقط برای مقدار اولیه است؛ نسخه زنده در `docs/decisions/open-decisions.md` و `decision-log.md` repo محصول است.
- پس از هر تغییر بزرگ، `doctor.py` را اجرا کن.

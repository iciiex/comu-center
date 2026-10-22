# راهنمای راه‌اندازی: خواندن چت‌های اینستاگرام + پاسخ‌گویی AI (رایگان)

این راهنما محصول را برای **اکانت اینستاگرام خودتان** فعال می‌کند؛ فقط با API
رسمی متا (بدون اسکرپینگ و ابزار غیررسمی). هزینه‌ها: API متا رایگان است؛ برای AI
از پلن رایگان Gemini یا Groq (یا Ollama روی کامپیوتر خودتان = کاملاً رایگان و
آفلاین) استفاده می‌کنیم. تنها چیزی که شاید هزینه داشته باشد، جایی است که سرور
را اجرا می‌کنید (برای تست، تونل رایگان کافی است — قدم ۵).

> ⚠️ دو قانون متا را از اول بدانید: (۱) فقط می‌توانید به کسی پیام بدهید که
> **اول او به شما پیام داده** و فقط تا **۲۴ ساعت** بعد از آخرین پیامش.
> (۲) اکانت باید **Professional** (بیزینس یا کریتور) باشد؛ اکانت شخصی API ندارد.

---

## قدم ۱ — ساخت اپ متا و گرفتن توکن (۱۰–۱۵ دقیقه، سمت شما)

1. اکانت اینستاگرامتان را Professional کنید (تنظیمات اینستاگرام ← نوع حساب).
2. در [developers.facebook.com](https://developers.facebook.com) یک **App** بسازید
   و محصول **Instagram** را به آن اضافه کنید (مسیر *Instagram API with Instagram
   Login* — نیازی به پیج فیس‌بوک نیست). نام منوها ممکن است کمی عوض شده باشد؛
   مرجع نهایی، مستندات رسمی متا در انتهای همین فایل است.
3. در بخش تنظیم API اینستاگرام، اکانت خود را وصل و یک **Access Token** تولید کنید.
   مجوزهای لازم: `instagram_business_basic` و `instagram_business_manage_messages`.
   برای اکانت خودتان (نقش در اپ) نیازی به App Review نیست؛ App Review وقتی لازم
   می‌شود که بخواهید برای اکانت دیگران سرویس بدهید.
4. این‌ها را یادداشت کنید (در چت/گیت‌هاب نفرستید!):
   **App Secret**، **Access Token**، و **شناسه عددی اکانت اینستاگرام (IG ID)**
   (از همان پنل یا پاسخ `/me` مشخص می‌شود). توکن‌ها معمولاً ~۶۰ روزه‌اند؛
   قبل از انقضا باید تمدید شوند (یادآور تقویمی بگذارید).

## قدم ۲ — کلید AI رایگان (۵ دقیقه، یکی کافی است)

| سرویس | آدرس (`INVAR_AI_API_BASE_URL`) | مدل نمونه (`INVAR_AI_MODEL`) | نکته |
|---|---|---|---|
| Gemini (گوگل) | `https://generativelanguage.googleapis.com/v1beta/openai` | یک مدل Flash روز را از AI Studio انتخاب کنید | کلید از aistudio.google.com؛ شرایط پلن رایگان را بخوانید (ممکن است داده برای بهبود سرویس استفاده شود) |
| Groq | `https://api.groq.com/openai/v1` | یک مدل Llama روز از کنسول Groq | سریع؛ سقف مصرف رایگان دارد |
| Ollama (لوکال) | `http://localhost:11434/v1` | مدل دانلودشده خودتان | بدون کلید و آفلاین؛ نیازمند سخت‌افزار مناسب و کیفیت فارسی مدل انتخابی را خودتان بسنجید |

نام دقیق مدل‌ها و سقف‌های رایگان تغییر می‌کنند؛ از داشبورد همان سرویس بردارید.

## قدم ۳ — تنظیم `.env`

```bash
cp .env.example .env
```

مقادیر زیر را پر کنید (بقیه پیش‌فرض بمانند):

```ini
INVAR_AI_SEND_ENABLED=false
INVAR_META_LIVE_SEND_ENABLED=false

INVAR_META_APP_SECRET=<از قدم ۱>
INVAR_META_ACCESS_TOKEN=<از قدم ۱>
INVAR_META_IG_ACCOUNT_ID=<شناسه عددی اکانت>
INVAR_META_ACCOUNT_MAP=<شناسه عددی اکانت>=damiish
INVAR_META_WEBHOOK_VERIFY_TOKEN=<یک رشته تصادفی دلخواه خودتان>

INVAR_AI_PROVIDER_NAME=openai_compat
INVAR_AI_API_BASE_URL=<از قدم ۲>
INVAR_AI_MODEL=<از قدم ۲>
INVAR_AI_PROVIDER_API_KEY=<از قدم ۲، برای Ollama خالی>

INVAR_OPERATOR_TOKEN=<یک پسورد قوی برای دیدن اینباکس>
```

## قدم ۴ — دانش محصول (FAQ) را وارد کنید

سیستم **فقط** از روی اسنادی که شما تأیید کرده‌اید جواب می‌دهد؛ بقیه به انسان
ارجاع می‌شود. فایل نمونه را ویرایش یا فایل خودتان را با همان قالب بسازید:

```bash
.venv/bin/python -m invar_comms db-init
.venv/bin/python -m invar_comms kb-import examples/kb/sample-faq.fa.json damiish <اسم شما به‌عنوان تأییدکننده>
```

## قدم ۵ — اجرا و وصل‌کردن وب‌هوک

```bash
# ترمینال ۱: سرور وب‌هوک
.venv/bin/python -m invar_comms serve
# ترمینال ۲: پردازش صف پیام‌ها (حلقه ساده برای پایلوت)
while true; do .venv/bin/python -m invar_comms worker; sleep 2; done
```

متا باید سرور شما را از اینترنت ببیند. برای تست از تونل رایگان استفاده کنید،
مثلاً Cloudflare Quick Tunnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

آدرسی شبیه `https://xxxx.trycloudflare.com` می‌گیرید (هر بار تغییر می‌کند؛ برای
استفاده دائمی یک سرور ارزان یا تونل نام‌دار با دامنه خودتان لازم است).
در پنل اپ متا ← **Webhooks** ← شیء **Instagram** :

- Callback URL: `https://<آدرس شما>/webhooks/meta`
- Verify Token: همان `INVAR_META_WEBHOOK_VERIFY_TOKEN`
- فیلد `messages` را Subscribe کنید.

## قدم ۶ — اول «فقط خواندن»، بعد پاسخ‌گویی

1. با تنظیم قدم ۳ (`INVAR_AI_SEND_ENABLED=false`) سیستم در حالت **فقط خواندن**
   است: پیام‌ها ذخیره می‌شوند، هیچ پاسخی ارسال نمی‌شود. از یک اکانت دیگر به
   خودتان پیام بدهید و ببینید:

   ```bash
   curl -H "X-Operator-Token: <توکن اپراتور>" http://127.0.0.1:8000/api/conversations
   curl -H "X-Operator-Token: <توکن اپراتور>" http://127.0.0.1:8000/api/conversations/<conversation_id>
   ```

2. وقتی FAQ و رفتار را پسندیدید، در `.env` هر دو را `true` کنید و سرور/ورکر را
   ری‌استارت کنید:

   ```ini
   INVAR_AI_SEND_ENABLED=true
   INVAR_META_LIVE_SEND_ENABLED=true
   ```

   حالا سؤال‌هایی که در FAQ تأییدشده جواب دارند خودکار پاسخ می‌گیرند؛ بقیه
   (قیمت، قرارداد، شکایت…) بی‌پاسخ می‌مانند، در Audit ثبت می‌شوند و مکالمه
   در وضعیت ارجاع به انسان قرار می‌گیرد تا خودتان در اینستاگرام جواب بدهید.

## عیب‌یابی سریع

| علامت | علت محتمل |
|---|---|
| تأیید وب‌هوک در پنل متا خطا می‌دهد | آدرس تونل اشتباه/منقضی، یا Verify Token با `.env` یکی نیست، یا `serve` در حال اجرا نیست |
| پیام می‌رسد ولی در اینباکس نیست | ورکر در حال اجرا نیست، یا `INVAR_META_ACCOUNT_MAP` شناسه درست اکانت را ندارد |
| پیام ذخیره می‌شود ولی پاسخ نمی‌رود | یکی از دو کلید قدم ۶ خاموش است، یا سند FAQ منطبق ندارید (عمدی است: سیستم حدس نمی‌زند) — Audit همان مکالمه را در اینباکس ببینید |
| خطای AI در لاگ ورکر | نام مدل/آدرس اشتباه یا تمام‌شدن سهمیه رایگان سرویس AI |
| چند روز بعد همه‌چیز قطع شد | انقضای توکن متا — از پنل تمدید و `.env` را به‌روز کنید |

## مراجع رسمی
- ارسال پیام (Instagram Login): https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api/
- نمای کلی پلتفرم: https://developers.facebook.com/docs/instagram-platform/overview/
- راهنمای انگلیسی معماری همین ریپو: `docs/integrations/meta-instagram.md`

"use strict";
/* Browser simulation of the real domain rules (src/invar_comms/domain +
   application/conversation_service.py). Demo only — nothing is sent anywhere. */
const $ = (s) => document.querySelector(s);
const chat = $("#chat"), auditEl = $("#audit");
let state, version, seenEvents, msgCounter;

function reset() {
  state = "ai_active"; version = 0; seenEvents = new Set(); msgCounter = 0;
  chat.innerHTML = ""; auditEl.innerHTML = "";
  render(); audit("conversation_created", "actor=system");
  sys("مکالمه ساخته شد — AI فعال است (منتظر پیام مشتری)");
}
function render() {
  const label = $("#stateLabel");
  label.textContent = state;
  label.className = "state " + (state === "ai_active" ? "ai" : state === "human_active" ? "human" : "handover");
  $("#versionLabel").textContent = version;
}
function audit(type, detail) {
  const li = document.createElement("li");
  li.textContent = `${type}  v=${version}  ${detail || ""}`;
  auditEl.prepend(li);
}
function bubble(kind, who, text) {
  const d = document.createElement("div");
  d.className = "msg " + kind;
  d.innerHTML = `<small></small><span></span>`;
  d.querySelector("small").textContent = who;
  d.querySelector("span").textContent = text;
  chat.appendChild(d); d.scrollIntoView({ block: "nearest" });
}
const sys = (t) => bubble("system", "سیستم", t);
const blocked = (t) => bubble("blocked", "⛔ ارسال AI مسدود شد", t);
const aiMaySend = () => state === "ai_active" && $("#killSwitch").checked;

function tryAiSend(text, capturedVersion) {
  if (!$("#killSwitch").checked) { audit("ai_send_blocked", "reason=kill_switch_off"); return blocked("کلید ارسال AI خاموش است — هیچ پیامی ارسال نشد."); }
  if (state !== "ai_active") { audit("ai_send_blocked", "reason=" + state); return blocked("کنترل دست انسان است (" + state + ") — ارسال AI قفل است."); }
  if (capturedVersion !== version) { audit("ai_send_blocked", "reason=stale_control_version"); return blocked("کنترل حین تولید پاسخ عوض شده — پاسخ کهنه ارسال نشد."); }
  audit("ai_send_allowed", "actor=ai-damiish");
  bubble("ai", "🤖 AI (پاسخ مبتنی بر دانش تأییدشده)", text);
}
function escalate(reason) {
  if (state === "ai_active") { state = "handover_requested"; version++; audit("handover_requested", "actor=ai-damiish"); render(); }
  sys("ارجاع به اپراتور انسانی: " + reason + " — از همین لحظه ارسال AI متوقف است.");
}
function inbound(kind) {
  const eventId = "evt-" + (++msgCounter);
  if (seenEvents.has(eventId)) return;
  seenEvents.add(eventId);
  const captured = version;
  if (kind === "faq") {
    bubble("customer", "مشتری (اینستاگرام)", "سلام، چطور دام جدید ثبت کنم؟");
    tryAiSend("برای ثبت دام جدید: صفحه‌ی گله → «افزودن دام». (منبع: سند تأییدشده‌ی faq-animal-registration نسخه ۱)", captured);
  } else {
    bubble("customer", "مشتری (اینستاگرام)", "قیمت اشتراک سالانه چنده؟ تخفیف هم می‌دید؟");
    escalate("سؤال تجاری/قیمت — دانش تأییدشده‌ای برای پاسخ خودکار نیست، حدس ممنوع");
  }
}
const actions = {
  faq: () => inbound("faq"),
  pricing: () => inbound("pricing"),
  duplicate: () => {
    if (msgCounter === 0) return sys("هنوز پیامی نیامده که تکراری‌اش برسد.");
    audit("duplicate_ignored", "external_event_id=evt-" + msgCounter);
    sys("وب‌هوک تکراری رسید — با کلید یکتای رویداد (idempotency) نادیده گرفته شد؛ پاسخ دوم ارسال نشد. ✔");
  },
  takeover: () => {
    if (state === "human_active") return sys("از قبل دست اپراتور است.");
    state = "human_active"; version++; audit("human_took_over", "actor=op-1"); render();
    sys("اپراتور مکالمه را تحویل گرفت — ارسال AI تا ازسرگیریِ صریح قفل است. 🔒");
  },
  humanReply: () => {
    if (state !== "human_active") return sys("اول باید تحویل به اپراتور انجام شود.");
    audit("human_sent", "actor=op-1");
    bubble("human", "🧑‍💼 اپراتور انسانی", "سلام! من اپراتور دامی‌ش هستم، شخصاً پیگیر سؤالتون هستم. 🙏");
  },
  aiTry: () => tryAiSend("(تلاش برای ارسال خودکار…)", version),
  resume: () => {
    if (state !== "human_active") return sys("ازسرگیری فقط از وضعیت human_active و فقط توسط اپراتور مجاز ممکن است.");
    state = "ai_active"; version++; audit("ai_resumed", "actor=op-1"); render();
    sys("اپراتور به‌صورت صریح AI را فعال کرد. ▶️ (خودِ AI هرگز نمی‌تواند این کار را بکند)");
  },
  reset,
};
document.querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", () => actions[b.dataset.act]()));
$("#killSwitch").addEventListener("change", (e) => sys(e.target.checked ? "کلید ارسال AI روشن شد." : "کلید ارسال AI خاموش شد — Kill Switch سراسری."));

fetch("/api/health").then((r) => r.json()).then((j) => {
  $("#apiBadge").textContent = "API: سالم ✅" + (j.core_version ? " · core v" + j.core_version : "");
}).catch(() => { $("#apiBadge").textContent = "API: در این پیش‌نمایش محلی در دسترس نیست (روی Vercel فعال می‌شود)"; });

reset();

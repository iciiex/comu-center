"""OpenAI-compatible AI provider adapter (stdlib urllib).

One adapter covers every OpenAI-compatible chat endpoint, which in practice
means the owner can start for free and switch later by config only:
- Google Gemini AI Studio free tier (base: generativelanguage.../v1beta/openai)
- Groq free tier (base: api.groq.com/openai/v1)
- OpenRouter free models (base: openrouter.ai/api/v1)
- Ollama locally (base: http://localhost:11434/v1, no key, fully offline)

Grounding contract: the model is instructed to answer ONLY from the supplied
approved-knowledge excerpts and to reply with JSON {"answer", "confidence"}.
Anything unparsable becomes a zero-confidence suggestion, which the
application layer escalates to a human instead of sending. Transport errors
raise AIProviderError so the outbox can retry with its bounded attempts.
Quotas/terms of free tiers change and some use data for product improvement —
treat them as pilots, not privacy guarantees (see the setup guide).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..domain.errors import DomainError
from ..ports.ai_provider import ReplyRequest, ReplySuggestion

_SYSTEM_PROMPT = (
    "You are a customer-support assistant. Answer ONLY using the approved "
    "knowledge excerpts provided. Never invent features, prices, "
    "availability, deadlines or account data. Reply in the customer's "
    "language. If the excerpts do not clearly answer the question, use a "
    "low confidence value. Output ONLY a JSON object like "
    '{"answer": "...", "confidence": 0.0} with confidence between 0 and 1.'
)


class AIProviderError(DomainError):
    """AI provider unreachable or returned an error (retryable by the outbox)."""


class OpenAICompatibleProvider:
    name = "openai_compat"

    def __init__(
        self, *, base_url: str, model: str, api_key: str = "",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout_seconds

    def suggest_reply(self, request: ReplyRequest) -> ReplySuggestion:
        if not self._base_url or not self._model:
            raise AIProviderError(
                "AI provider not configured (INVAR_AI_API_BASE_URL / INVAR_AI_MODEL)")
        excerpts = "\n---\n".join(request.knowledge_excerpts)
        payload = {
            "model": self._model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Approved knowledge excerpts:\n{excerpts}\n\n"
                    f"Customer message:\n{request.inbound.text}")},
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        http_request = urllib.request.Request(  # noqa: S310 - operator-configured AI host
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"), method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(  # noqa: S310
                    http_request, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300] if exc.fp else ""
            raise AIProviderError(f"AI provider HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise AIProviderError(f"AI provider unreachable: {exc.reason}") from exc

        try:
            content = (
                json.loads(raw)["choices"][0]["message"]["content"] or ""
            ).strip()
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            return ReplySuggestion(text="(unparsable provider response)",
                                   confidence=0.0)
        return _parse_suggestion(content)


def _parse_suggestion(content: str) -> ReplySuggestion:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(cleaned)
        answer = str(data["answer"]).strip()
        confidence = float(data["confidence"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return ReplySuggestion(text="(unparsable provider output)", confidence=0.0)
    if not answer:
        return ReplySuggestion(text="(empty provider answer)", confidence=0.0)
    return ReplySuggestion(text=answer, confidence=min(1.0, max(0.0, confidence)))

"""OpenAI-compatible provider tests against a local stub chat endpoint."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from helpers import make_message

from invar_comms.adapters.openai_compat import (
    AIProviderError,
    OpenAICompatibleProvider,
)
from invar_comms.ports.ai_provider import ReplyRequest

MODE = {"reply": "json", "fail": False}
SEEN: list[dict[str, object]] = []


class ChatStub(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length)
        SEEN.append({"path": self.path,
                     "auth": self.headers.get("Authorization"),
                     "body": json.loads(body.decode()) if body else {}})
        if MODE["fail"]:
            self.send_response(429)
            self.end_headers()
            self.wfile.write(b'{"error":"rate limited"}')
            return
        content = (
            '{"answer": "از صفحه گله، افزودن دام را بزنید.", "confidence": 0.92}'
            if MODE["reply"] == "json" else "متن آزاد بدون JSON"
        )
        payload = json.dumps(
            {"choices": [{"message": {"content": content}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture()
def ai_url():  # type: ignore[no-untyped-def]
    MODE.update(reply="json", fail=False)
    SEEN.clear()
    server = ThreadingHTTPServer(("127.0.0.1", 0), ChatStub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/v1"
    server.shutdown()
    server.server_close()


def request() -> ReplyRequest:
    return ReplyRequest(product_id="damiish", inbound=make_message(),
                        knowledge_excerpts=("To register: herd screen > Add animal.",))


def test_grounded_json_reply_is_parsed(ai_url: str) -> None:
    provider = OpenAICompatibleProvider(base_url=ai_url, model="test-model",
                                        api_key="key-1")
    suggestion = provider.suggest_reply(request())
    assert suggestion.confidence == 0.92
    assert "افزودن دام" in suggestion.text
    assert SEEN[0]["path"] == "/v1/chat/completions"
    assert SEEN[0]["auth"] == "Bearer key-1"
    sent_messages = SEEN[0]["body"]["messages"]  # type: ignore[index]
    assert "ONLY" in sent_messages[0]["content"]  # grounding instruction present
    assert "Add animal" in sent_messages[1]["content"]


def test_unparsable_output_becomes_zero_confidence(ai_url: str) -> None:
    MODE["reply"] = "free"
    provider = OpenAICompatibleProvider(base_url=ai_url, model="m")
    assert provider.suggest_reply(request()).confidence == 0.0


def test_http_error_raises_retryable_provider_error(ai_url: str) -> None:
    MODE["fail"] = True
    provider = OpenAICompatibleProvider(base_url=ai_url, model="m")
    with pytest.raises(AIProviderError):
        provider.suggest_reply(request())


def test_unconfigured_provider_fails_fast() -> None:
    provider = OpenAICompatibleProvider(base_url="", model="")
    with pytest.raises(AIProviderError):
        provider.suggest_reply(request())

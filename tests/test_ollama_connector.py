from __future__ import annotations

from types import SimpleNamespace

from llm.connectors.ollama import OllamaClient


class FakeChatBackend:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if not self.responses:
            raise RuntimeError("No response left.")
        return self.responses.pop(0)


def build_response(*, content: str, thinking: str | None = None, done_reason: str = "stop"):
    return SimpleNamespace(
        message=SimpleNamespace(content=content, thinking=thinking),
        done_reason=done_reason,
    )


def build_client(fake_backend: FakeChatBackend) -> OllamaClient:
    client = OllamaClient.__new__(OllamaClient)
    client.base_url = "http://localhost:11434"
    client.model = "nemotron-cascade-2:latest"
    client.reasoning_effort = "medium"
    client.temperature = 0.2
    client._client = fake_backend
    return client


def test_complete_text_retries_without_think_when_budget_spent_on_thinking() -> None:
    backend = FakeChatBackend(
        [
            build_response(content="", thinking="long reasoning", done_reason="length"),
            build_response(content='{"ok": true}', thinking=None, done_reason="stop"),
        ]
    )
    client = build_client(backend)

    text = client.complete_text(
        [{"role": "user", "content": 'Retourne {"ok": true}'}],
        temperature=0.0,
        max_tokens=200,
    )

    assert text == '{"ok": true}'
    assert len(backend.calls) == 2
    assert backend.calls[0]["think"] is True
    assert backend.calls[1]["think"] is False

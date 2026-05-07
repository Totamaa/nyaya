from __future__ import annotations

from typing import Any, Iterable

from app.core.config.logs import get_logger
from .base import Message
from .utils import parse_structured_output

logger = get_logger()
_TAG = "LLM:Ollama"


def _extract_message_content(response: Any) -> str:
    message = getattr(response, "message", None)
    if message is None and isinstance(response, dict):
        message = response.get("message")

    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")

    return (content or "").strip()


def _extract_done_reason(response: Any) -> str | None:
    value = getattr(response, "done_reason", None)
    if value is None and isinstance(response, dict):
        value = response.get("done_reason")
    return value


def _extract_thinking(response: Any) -> str:
    message = getattr(response, "message", None)
    if message is None and isinstance(response, dict):
        message = response.get("message")

    thinking = getattr(message, "thinking", None)
    if thinking is None and isinstance(message, dict):
        thinking = message.get("thinking")
    return (thinking or "").strip()


def _raise_ollama_unavailable(exc: Exception, *, base_url: str, model: str) -> None:
    raise RuntimeError(
        f"Ollama est indisponible sur {base_url} pour le modèle '{model}'. "
        "Vérifie que le serveur Ollama est démarré et accessible."
    ) from exc


class OllamaClient:
    def __init__(
        self,
        *,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        reasoning_effort: str | None = None,
        timeout_s: float = 120.0,
        temperature: float = 0.2,
    ):
        try:
            import ollama
        except ImportError as exc:
            raise RuntimeError("Missing optional dependency 'ollama'.") from exc

        self.base_url = base_url
        self._client = ollama.Client(host=base_url, timeout=timeout_s)
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.temperature = float(temperature)

    def _options(self, temperature: float | None) -> dict[str, float]:
        value = self.temperature if temperature is None else float(temperature)
        return {"temperature": value}

    def _think_value(self) -> bool | str | None:
        if self.reasoning_effort is None:
            return False
        if self.reasoning_effort == "none":
            return False

        if self.model.startswith("gpt-oss"):
            if self.reasoning_effort == "minimal":
                return "low"
            if self.reasoning_effort == "xhigh":
                return "high"
            return self.reasoning_effort

        return True

    def complete_text(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": self._options(temperature),
        }
        think = self._think_value()
        if think is not None:
            kwargs["think"] = think
        if max_tokens is not None:
            kwargs["options"]["num_predict"] = int(max_tokens)

        logger.debug(_TAG, "complete_text", extra=f"model={self.model}")
        try:
            response = self._client.chat(**kwargs)
        except ConnectionError as exc:
            logger.error(_TAG, f"Ollama unavailable at {self.base_url}", exc=exc)
            _raise_ollama_unavailable(exc, base_url=self.base_url, model=self.model)
        content = _extract_message_content(response)
        if content:
            logger.debug(_TAG, "complete_text done", extra=f"len={len(content)}")
            return content

        done_reason = _extract_done_reason(response)
        thinking = _extract_thinking(response)
        if think not in (None, False) and done_reason == "length" and thinking:
            logger.debug(_TAG, "Retrying without think (done_reason=length)", extra=f"model={self.model}")
            retry_kwargs = dict(kwargs)
            retry_kwargs["think"] = False
            try:
                retry_response = self._client.chat(**retry_kwargs)
            except ConnectionError as exc:
                logger.error(_TAG, f"Ollama unavailable on retry at {self.base_url}", exc=exc)
                _raise_ollama_unavailable(exc, base_url=self.base_url, model=self.model)
            retry_content = _extract_message_content(retry_response)
            if retry_content:
                return retry_content

        return content

    def stream_text(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterable[str]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": self._options(temperature),
        }
        think = self._think_value()
        if think is not None:
            kwargs["think"] = think
        if max_tokens is not None:
            kwargs["options"]["num_predict"] = int(max_tokens)

        logger.debug(_TAG, "stream_text", extra=f"model={self.model}")
        try:
            for chunk in self._client.chat(**kwargs):
                content = _extract_message_content(chunk)
                if content:
                    yield content
        except ConnectionError as exc:
            logger.error(_TAG, f"Ollama unavailable during stream at {self.base_url}", exc=exc)
            _raise_ollama_unavailable(exc, base_url=self.base_url, model=self.model)

    def complete_structured(
        self,
        messages: list[Message],
        output_type: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        text = self.complete_text(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return parse_structured_output(text, output_type)

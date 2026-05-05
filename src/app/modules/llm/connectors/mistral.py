from __future__ import annotations

import json
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config.settings import get_settings

from .base import Message
from .utils import parse_structured_output


def _extract_content(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                if text:
                    parts.append(str(text))
        return "".join(parts).strip()
    return str(content).strip()


class MistralClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str = "mistral-medium-latest",
        base_url: str = "https://api.mistral.ai",
        reasoning_effort: str | None = None,
        timeout_s: float = 120.0,
        temperature: float = 0.2,
    ) -> None:
        if not api_key:
            raise RuntimeError(
                "Aucune clé API Mistral fournie. Définis `mistral.api_key` "
                "ou la variable d'environnement `MISTRAL_API_KEY`."
            )
            
        self.settings = get_settings()

        self.api_key = self.settings.LLM_API_KEY
        self.model = self.settings.LLM_MODEL
        self.base_url = self.settings.LLM_BASE_URL.rstrip("/")
        self.reasoning_effort = reasoning_effort
        self.timeout_s = float(timeout_s)
        self.temperature = float(temperature)

    def _payload(
        self,
        messages: list[Message],
        *,
        temperature: float | None,
        max_tokens: int | None,
        stream: bool,
    ) -> bytes:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else float(temperature),
            "stream": stream,
        }
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        return json.dumps(payload).encode("utf-8")

    def _request(self, payload: bytes) -> Any:
        request = Request(
            url=f"{self.base_url}/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            return urlopen(request, timeout=self.timeout_s)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Erreur HTTP Mistral {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(
                f"Impossible de joindre Mistral sur {self.base_url}."
            ) from exc

    def complete_text(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        payload = self._payload(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        with self._request(payload) as response:
            data = json.load(response)

        choices = data.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return _extract_content(message)

    def stream_text(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterable[str]:
        payload = self._payload(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        request = Request(
            url=f"{self.base_url}/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    text = _extract_content(delta)
                    if text:
                        yield text
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Erreur HTTP Mistral {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(
                f"Impossible de joindre Mistral sur {self.base_url}."
            ) from exc

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

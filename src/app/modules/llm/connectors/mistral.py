from __future__ import annotations

import json
import socket
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config.logs import get_logger
from app.modules.llm.exceptions import (
    LLMAuthenticationException,
    LLMContextLengthException,
    LLMInvalidResponseException,
    LLMQuotaExceededException,
    LLMRateLimitException,
    LLMTimeoutException,
    LLMUnavailableException,
)
from .base import Message
from .utils import parse_structured_output

logger = get_logger()
_TAG = "LLM:Mistral"


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
            raise LLMAuthenticationException()

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
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

    def _raise_for_http(self, exc: HTTPError) -> None:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error(_TAG, f"HTTP {exc.code} from Mistral", extra=body[:200])
        body_lower = body.lower()

        if exc.code == 401:
            raise LLMAuthenticationException() from exc
        if exc.code == 402:
            raise LLMQuotaExceededException() from exc
        if exc.code == 422:
            if any(kw in body_lower for kw in ("context", "token", "length", "too long")):
                raise LLMContextLengthException() from exc
            raise LLMInvalidResponseException(body[:200]) from exc
        if exc.code == 429:
            if any(kw in body_lower for kw in ("quota", "credit", "billing")):
                raise LLMQuotaExceededException() from exc
            raise LLMRateLimitException() from exc
        if exc.code in (500, 502, 503, 504):
            raise LLMUnavailableException() from exc
        raise LLMUnavailableException() from exc

    def _raise_for_url_error(self, exc: URLError) -> None:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise LLMTimeoutException(self.timeout_s) from exc
        logger.error(_TAG, f"Cannot reach Mistral at {self.base_url}", exc=exc)
        raise LLMUnavailableException() from exc

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
        except TimeoutError as exc:
            raise LLMTimeoutException(self.timeout_s) from exc
        except HTTPError as exc:
            self._raise_for_http(exc)
        except URLError as exc:
            self._raise_for_url_error(exc)

    def complete_text(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        logger.debug(_TAG, "complete_text", extra=f"model={self.model}")
        payload = self._payload(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        with self._request(payload) as response:
            try:
                data = json.load(response)
            except json.JSONDecodeError as exc:
                raise LLMInvalidResponseException(str(exc)) from exc

        choices = data.get("choices", [])
        if not choices:
            logger.warning(_TAG, "No choices in Mistral response")
            return ""
        message = choices[0].get("message", {})
        result = _extract_content(message)
        logger.debug(_TAG, "complete_text done", extra=f"len={len(result)}")
        return result

    def stream_text(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterable[str]:
        logger.debug(_TAG, "stream_text", extra=f"model={self.model}")
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
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError as exc:
                        raise LLMInvalidResponseException(f"SSE chunk invalide: {data_str[:100]}") from exc
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    text = _extract_content(delta)
                    if text:
                        yield text
        except TimeoutError as exc:
            raise LLMTimeoutException(self.timeout_s) from exc
        except HTTPError as exc:
            self._raise_for_http(exc)
        except URLError as exc:
            self._raise_for_url_error(exc)

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

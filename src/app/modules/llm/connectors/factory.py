from __future__ import annotations

from .base import LLMClient
from .mistral import MistralClient
from .ollama import OllamaClient


def build_llm_client(
    *,
    base_url: str,
    model: str,
    api_key: str = "",
    timeout_s: float = 120.0,
    temperature: float = 0.0,
    reasoning_effort: str | None = None,
) -> LLMClient:
    """Instancie le bon client LLM en fonction de l'URL.

    URL locale (localhost / 127.0.0.1) → OllamaClient.
    Toute autre URL → MistralClient (compatible OpenAI /v1/chat/completions).
    """
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return OllamaClient(
            base_url=base_url,
            model=model,
            reasoning_effort=reasoning_effort,
            timeout_s=timeout_s,
            temperature=temperature,
        )
    return MistralClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        reasoning_effort=reasoning_effort,
        timeout_s=timeout_s,
        temperature=temperature,
    )

from __future__ import annotations

from app.core.config.logs import get_logger
from .base import LLMClient
from .mistral import MistralClient
from .ollama import OllamaClient

logger = get_logger()
_TAG = "LLM:Factory"


def build_llm_client(
    *,
    base_url: str,
    model: str,
    api_key: str = "",
    timeout_s: float = 120.0,
    temperature: float = 0.0,
    reasoning_effort: str | None = None,
    use_mock: bool,
) -> LLMClient:
    """Instancie le bon client LLM en fonction de l'URL.

    use_mock=True → MockLLMClient (scores aléatoires, aucun appel réseau).
    URL locale (localhost / 127.0.0.1) → OllamaClient.
    Toute autre URL → MistralClient (compatible OpenAI /v1/chat/completions).
    """
    if use_mock:
        logger.info(_TAG, "Using MockLLMClient")
        from .mock import MockLLMClient
        return MockLLMClient()
    if "localhost" in base_url or "127.0.0.1" in base_url:
        logger.info(_TAG, "Using OllamaClient", extra=f"model={model} url={base_url}")
        return OllamaClient(
            base_url=base_url,
            model=model,
            reasoning_effort=reasoning_effort,
            timeout_s=timeout_s,
            temperature=temperature,
        )
    logger.info(_TAG, "Using MistralClient", extra=f"model={model} url={base_url}")
    return MistralClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        reasoning_effort=reasoning_effort,
        timeout_s=timeout_s,
        temperature=temperature,
    )

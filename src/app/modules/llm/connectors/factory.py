from __future__ import annotations

from ..config import AppConfig

from .base import LLMClient
from .mistral import MistralClient
from .ollama import OllamaClient


def build_llm(cfg: AppConfig) -> LLMClient:
    if cfg.llm.backend == "ollama":
        return OllamaClient(
            base_url=cfg.ollama.base_url,
            model=cfg.ollama.model,
            reasoning_effort=cfg.llm.reasoning_effort,
            timeout_s=cfg.ollama.timeout_s,
            temperature=cfg.llm.temperature,
        )

    if cfg.llm.backend == "mistral":
        return MistralClient(
            api_key=cfg.mistral.api_key,
            base_url=cfg.mistral.base_url,
            model=cfg.mistral.model,
            reasoning_effort=cfg.llm.reasoning_effort,
            timeout_s=cfg.mistral.timeout_s,
            temperature=cfg.llm.temperature,
        )

    raise ValueError(
        f"Backend LLM inconnu: {cfg.llm.backend!r}. Utilise 'ollama' ou 'mistral'."
    )

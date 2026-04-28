from __future__ import annotations

from importlib import import_module
from typing import Any

from .base import LLMClient
from .factory import build_llm

__all__ = ["LLMClient", "build_llm", "OllamaClient", "MistralClient"]


def __getattr__(name: str) -> Any:
    if name == "OllamaClient":
        return import_module(".ollama", __name__).OllamaClient
    if name == "MistralClient":
        return import_module(".mistral", __name__).MistralClient
    raise AttributeError(f"module 'llm.connectors' has no attribute {name!r}")

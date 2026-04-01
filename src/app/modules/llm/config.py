from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class LLMSettings:
    backend: str = "ollama"
    system_prompt: str = "Tu es un assistant utile et concis."
    temperature: float = 0.2
    max_tokens: int | None = 512
    reasoning_effort: str | None = "medium"


@dataclass(slots=True)
class OllamaSettings:
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b"
    timeout_s: float = 120.0


@dataclass(slots=True)
class MistralSettings:
    api_key: str | None = None
    api_key_env: str = "MISTRAL_API_KEY"
    base_url: str = "https://api.mistral.ai"
    model: str = "mistral-medium-latest"
    timeout_s: float = 120.0


@dataclass(slots=True)
class AppConfig:
    llm: LLMSettings
    ollama: OllamaSettings
    mistral: MistralSettings


def _read_section(data: dict[str, object], name: str) -> dict[str, object]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"La section [{name}] du TOML doit être un objet.")
    return value


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path is not None else Path(__file__).with_name("config.toml")
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    llm_section = _read_section(raw, "llm")
    ollama_section = _read_section(raw, "ollama")
    mistral_section = _read_section(raw, "mistral")

    llm = LLMSettings(
        backend=str(llm_section.get("backend", "ollama")).strip().lower(),
        system_prompt=str(llm_section.get("system_prompt", LLMSettings.system_prompt)),
        temperature=float(llm_section.get("temperature", LLMSettings.temperature)),
        max_tokens=(
            None
            if llm_section.get("max_tokens") is None
            else int(llm_section["max_tokens"])
        ),
        reasoning_effort=(
            None
            if llm_section.get("reasoning_effort") is None
            else str(llm_section["reasoning_effort"]).strip()
        ),
    )

    ollama = OllamaSettings(
        base_url=str(ollama_section.get("base_url", OllamaSettings.base_url)),
        model=str(ollama_section.get("model", OllamaSettings.model)),
        timeout_s=float(ollama_section.get("timeout_s", OllamaSettings.timeout_s)),
    )

    api_key_env = str(mistral_section.get("api_key_env", MistralSettings.api_key_env))
    mistral = MistralSettings(
        api_key=(
            str(mistral_section["api_key"]).strip()
            if mistral_section.get("api_key")
            else os.getenv(api_key_env)
        ),
        api_key_env=api_key_env,
        base_url=str(mistral_section.get("base_url", MistralSettings.base_url)),
        model=str(mistral_section.get("model", MistralSettings.model)),
        timeout_s=float(mistral_section.get("timeout_s", MistralSettings.timeout_s)),
    )

    return AppConfig(llm=llm, ollama=ollama, mistral=mistral)

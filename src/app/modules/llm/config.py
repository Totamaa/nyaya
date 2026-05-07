from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

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


def _env_str(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value if value else None


def _env_float(name: str) -> float | None:
    value = _env_str(name)
    return None if value is None else float(value)


def _env_int(name: str) -> int | None:
    value = _env_str(name)
    return None if value is None else int(value)


def _read_section(data: dict[str, object], name: str) -> dict[str, object]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f"La section [{name}] du TOML doit être un objet.")
    return value


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path is not None else Path(__file__).with_name("config.toml")
    root_dir = config_path.parents[4]
    load_dotenv(root_dir / ".env", override=False)
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    llm_section = _read_section(raw, "llm")
    ollama_section = _read_section(raw, "ollama")
    mistral_section = _read_section(raw, "mistral")

    llm_backend = str(llm_section.get("backend", "ollama")).strip().lower()
    llm_system_prompt = str(llm_section.get("system_prompt", LLMSettings.system_prompt))
    llm_temperature = float(llm_section.get("temperature", LLMSettings.temperature))
    llm_max_tokens = (
        None
        if llm_section.get("max_tokens") is None
        else int(llm_section["max_tokens"])
    )
    llm_reasoning_effort = (
        None
        if llm_section.get("reasoning_effort") is None
        else str(llm_section["reasoning_effort"]).strip()
    )

    llm = LLMSettings(
        backend=(_env_str("LLM_BACKEND") or llm_backend).lower(),
        system_prompt=_env_str("LLM_SYSTEM_PROMPT") or llm_system_prompt,
        temperature=_env_float("LLM_TEMPERATURE") or llm_temperature,
        max_tokens=(
            _env_int("LLM_MAX_TOKENS")
            if _env_str("LLM_MAX_TOKENS") is not None
            else llm_max_tokens
        ),
        reasoning_effort=(
            _env_str("LLM_REASONING_EFFORT")
            if _env_str("LLM_REASONING_EFFORT") is not None
            else llm_reasoning_effort
        ),
    )

    ollama = OllamaSettings(
        base_url=_env_str("OLLAMA_BASE_URL")
        or str(ollama_section.get("base_url", OllamaSettings.base_url)),
        model=_env_str("OLLAMA_MODEL")
        or str(ollama_section.get("model", OllamaSettings.model)),
        timeout_s=_env_float("OLLAMA_TIMEOUT_S")
        or float(ollama_section.get("timeout_s", OllamaSettings.timeout_s)),
    )

    api_key_env = _env_str("MISTRAL_API_KEY_ENV") or str(
        mistral_section.get("api_key_env", MistralSettings.api_key_env)
    )
    direct_api_key = _env_str("MISTRAL_API_KEY")
    mistral = MistralSettings(
        api_key=direct_api_key
        or (
            str(mistral_section["api_key"]).strip()
            if mistral_section.get("api_key")
            else os.getenv(api_key_env)
        ),
        api_key_env=api_key_env,
        base_url=_env_str("MISTRAL_BASE_URL")
        or str(mistral_section.get("base_url", MistralSettings.base_url)),
        model=_env_str("MISTRAL_MODEL")
        or str(mistral_section.get("model", MistralSettings.model)),
        timeout_s=_env_float("MISTRAL_TIMEOUT_S")
        or float(mistral_section.get("timeout_s", MistralSettings.timeout_s)),
    )

    return AppConfig(llm=llm, ollama=ollama, mistral=mistral)

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class PardhaMode(str, Enum):
    DEVELOPMENT = "DEVELOPMENT"
    PRODUCTION = "PRODUCTION"


@dataclass(frozen=True)
class Settings:
    mode: PardhaMode
    ollama_enabled: bool
    default_reasoning_model: str
    advanced_reasoning_model: str
    max_concurrent_reasoning: int
    ollama_url: str
    ollama_timeout: float
    ollama_max_tokens: int
    ollama_context_size: int
    ollama_idle_timeout_seconds: int
    jira_enabled: bool
    jira_url: str
    jira_email: str
    jira_api_token: str
    jira_project_key: str


def _enabled(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() not in {"0", "false", "no"}


def get_settings() -> Settings:
    mode = PardhaMode(os.getenv("PARDHA_MODE", PardhaMode.DEVELOPMENT.value).upper())
    return Settings(
        mode=mode,
        ollama_enabled=_enabled("PARDHA_OLLAMA_ENABLED", "true"),
        default_reasoning_model=os.getenv("PARDHA_DEFAULT_REASONING_MODEL", "qwen3:8b"),
        advanced_reasoning_model=os.getenv("PARDHA_ADVANCED_REASONING_MODEL", "qwen3:8b"),
        max_concurrent_reasoning=max(1, int(os.getenv("MAX_CONCURRENT_REASONING", "1"))),
        ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
        ollama_timeout=float(os.getenv("PARDHA_OLLAMA_TIMEOUT", "60")),
        ollama_max_tokens=int(os.getenv("PARDHA_OLLAMA_MAX_TOKENS", "384")),
        ollama_context_size=int(os.getenv("PARDHA_OLLAMA_CONTEXT_SIZE", "4096")),
        ollama_idle_timeout_seconds=max(5, int(os.getenv("PARDHA_OLLAMA_IDLE_TIMEOUT_SECONDS", "90"))),
        jira_enabled=_enabled("PARDHA_JIRA_ENABLED", "true"),
        jira_url=os.getenv("JIRA_URL", "").rstrip("/"),
        jira_email=os.getenv("JIRA_EMAIL", ""),
        jira_api_token=os.getenv("JIRA_API_TOKEN", ""),
        jira_project_key=os.getenv("JIRA_PROJECT_KEY", ""),
    )

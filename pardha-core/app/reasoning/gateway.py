from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Protocol

from app.reasoning.client import OllamaUnavailable, generate_response
from app.settings import get_settings


class ReasoningProvider(Protocol):
    provider_id: str

    def health(self) -> dict[str, Any]:
        ...

    def generate(self, prompt: str, system_prompt: str | None = None, model: str | None = None, fallback: str | None = None) -> "ReasoningGatewayResult":
        ...

    def structured_generate(self, prompt: str, schema: dict[str, Any], system_prompt: str | None = None, model: str | None = None, fallback: dict[str, Any] | None = None) -> "ReasoningGatewayResult":
        ...


@dataclass(frozen=True)
class ReasoningGatewayResult:
    response: str
    provider: str
    model: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


class DeterministicReasoningProvider:
    provider_id = "deterministic"
    model = "pardha-deterministic-runtime"

    def health(self) -> dict[str, Any]:
        return {"provider": self.provider_id, "ready": True, "configured": True, "model": self.model}

    def generate(self, prompt: str, system_prompt: str | None = None, model: str | None = None, fallback: str | None = None) -> ReasoningGatewayResult:
        response = fallback or "Pardha used deterministic reasoning because no live reasoning provider was configured."
        return ReasoningGatewayResult(
            response=response,
            provider=self.provider_id,
            model=self.model,
            source="deterministic_fallback",
            metadata={
                "provider": self.provider_id,
                "fallback_used": True,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "prompt_chars": len(prompt),
                "system_prompt_chars": len(system_prompt or ""),
            },
        )

    def structured_generate(self, prompt: str, schema: dict[str, Any], system_prompt: str | None = None, model: str | None = None, fallback: dict[str, Any] | None = None) -> ReasoningGatewayResult:
        payload = fallback or {"result": self.generate(prompt, system_prompt, model).response}
        result = self.generate(prompt, system_prompt, model, json.dumps(payload, sort_keys=True))
        return ReasoningGatewayResult(response=result.response, provider=result.provider, model=result.model, source=result.source, metadata={**result.metadata, "structured": True, "schema_keys": sorted(schema.keys())})


class OllamaReasoningProvider:
    provider_id = "ollama"

    def health(self) -> dict[str, Any]:
        from app.reasoning.client import ollama_status

        status = ollama_status()
        return {"provider": self.provider_id, "ready": status.connected and status.model_available and status.reasoning_status != "disabled", "configured": True, "model": status.current_model, "message": status.message}

    def generate(self, prompt: str, system_prompt: str | None = None, model: str | None = None, fallback: str | None = None) -> ReasoningGatewayResult:
        settings = get_settings()
        selected_model = model or settings.default_reasoning_model
        response = generate_response(prompt, system_prompt, selected_model)
        return ReasoningGatewayResult(
            response=response,
            provider=self.provider_id,
            model=selected_model,
            source="ollama",
            metadata={
                "provider": self.provider_id,
                "fallback_used": False,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "prompt_chars": len(prompt),
                "system_prompt_chars": len(system_prompt or ""),
            },
        )

    def structured_generate(self, prompt: str, schema: dict[str, Any], system_prompt: str | None = None, model: str | None = None, fallback: dict[str, Any] | None = None) -> ReasoningGatewayResult:
        result = self.generate(f"{prompt}\n\nReturn JSON matching this schema:\n{json.dumps(schema, sort_keys=True)}", system_prompt, model)
        return ReasoningGatewayResult(response=result.response, provider=result.provider, model=result.model, source=result.source, metadata={**result.metadata, "structured": True, "schema_keys": sorted(schema.keys())})


class OpenAIReasoningProvider:
    provider_id = "openai"

    def health(self) -> dict[str, Any]:
        settings = get_settings()
        return {"provider": self.provider_id, "ready": bool(settings.openai_api_key), "configured": bool(settings.openai_api_key), "model": settings.openai_model}

    def generate(self, prompt: str, system_prompt: str | None = None, model: str | None = None, fallback: str | None = None) -> ReasoningGatewayResult:
        settings = get_settings()
        if not settings.openai_api_key:
            raise OllamaUnavailable("OpenAI provider is not configured. Set OPENAI_API_KEY.")
        raise OllamaUnavailable("OpenAI generation client is not enabled in this local build.")

    def structured_generate(self, prompt: str, schema: dict[str, Any], system_prompt: str | None = None, model: str | None = None, fallback: dict[str, Any] | None = None) -> ReasoningGatewayResult:
        raise OllamaUnavailable("OpenAI structured generation client is not enabled in this local build.")


class StubReasoningProvider:
    def __init__(self, provider_id: str):
        self.provider_id = provider_id

    def health(self) -> dict[str, Any]:
        return {"provider": self.provider_id, "ready": False, "configured": False, "model": None}

    def generate(self, prompt: str, system_prompt: str | None = None, model: str | None = None, fallback: str | None = None) -> ReasoningGatewayResult:
        raise OllamaUnavailable(f"{self.provider_id} provider is not configured in this build.")

    def structured_generate(self, prompt: str, schema: dict[str, Any], system_prompt: str | None = None, model: str | None = None, fallback: dict[str, Any] | None = None) -> ReasoningGatewayResult:
        raise OllamaUnavailable(f"{self.provider_id} provider is not configured in this build.")


class ReasoningGateway:
    def __init__(self) -> None:
        self.providers: dict[str, ReasoningProvider] = {
            "deterministic": DeterministicReasoningProvider(),
            "ollama": OllamaReasoningProvider(),
            "openai": OpenAIReasoningProvider(),
            "gemini": StubReasoningProvider("gemini"),
            "claude": StubReasoningProvider("claude"),
        }
        self._usage_lock = threading.Lock()
        self._usage_date = date.today().isoformat()
        self._daily_requests = 0
        self._provider_usage: dict[str, int] = {}
        self._fallback_count = 0
        self._failure_log: list[dict[str, Any]] = []

    def health(self) -> dict[str, Any]:
        settings = get_settings()
        usage = self.usage_snapshot()
        return {
            "selected_provider": settings.reasoning_provider,
            "fallback_provider": settings.reasoning_fallback,
            "daily_budget": usage,
            "providers": {provider_id: provider.health() for provider_id, provider in self.providers.items()},
        }

    def generate(self, prompt: str, system_prompt: str | None = None, model: str | None = None, fallback: str | None = None, provider: str | None = None) -> ReasoningGatewayResult:
        settings = get_settings()
        selected = (provider or settings.reasoning_provider or "deterministic").lower()
        fallback_provider = (settings.reasoning_fallback or "deterministic").lower()
        if self._budget_exceeded(settings.max_daily_reasoning_requests) and selected != "deterministic":
            result = self._provider(fallback_provider).generate(prompt, system_prompt, None, fallback)
            self._record_usage(result.provider, fallback_used=True)
            return ReasoningGatewayResult(
                response=result.response,
                provider=result.provider,
                model=result.model,
                source=result.source,
                metadata={**result.metadata, "requested_provider": selected, "fallback_provider": fallback_provider, "fallback_reason": "daily_reasoning_budget_exceeded", "daily_budget_exceeded": True},
            )
        try:
            result = self._provider(selected).generate(prompt, system_prompt, model, fallback)
            self._record_usage(result.provider, fallback_used=False)
            return result
        except OllamaUnavailable as exc:
            result = self._provider(fallback_provider).generate(prompt, system_prompt, None, fallback)
            self._record_failure(selected, str(exc))
            self._record_usage(result.provider, fallback_used=True)
            return ReasoningGatewayResult(
                response=result.response,
                provider=result.provider,
                model=result.model,
                source=result.source,
                metadata={**result.metadata, "requested_provider": selected, "fallback_provider": fallback_provider, "fallback_reason": str(exc)},
            )

    def structured_generate(self, prompt: str, schema: dict[str, Any], system_prompt: str | None = None, model: str | None = None, fallback: dict[str, Any] | None = None, provider: str | None = None) -> ReasoningGatewayResult:
        settings = get_settings()
        selected = (provider or settings.reasoning_provider or "deterministic").lower()
        fallback_provider = (settings.reasoning_fallback or "deterministic").lower()
        if self._budget_exceeded(settings.max_daily_reasoning_requests) and selected != "deterministic":
            result = self._provider(fallback_provider).structured_generate(prompt, schema, system_prompt, None, fallback)
            self._record_usage(result.provider, fallback_used=True)
            return ReasoningGatewayResult(response=result.response, provider=result.provider, model=result.model, source=result.source, metadata={**result.metadata, "requested_provider": selected, "fallback_provider": fallback_provider, "fallback_reason": "daily_reasoning_budget_exceeded", "daily_budget_exceeded": True})
        try:
            result = self._provider(selected).structured_generate(prompt, schema, system_prompt, model, fallback)
            self._record_usage(result.provider, fallback_used=False)
            return result
        except OllamaUnavailable as exc:
            result = self._provider(fallback_provider).structured_generate(prompt, schema, system_prompt, None, fallback)
            self._record_failure(selected, str(exc))
            self._record_usage(result.provider, fallback_used=True)
            return ReasoningGatewayResult(response=result.response, provider=result.provider, model=result.model, source=result.source, metadata={**result.metadata, "requested_provider": selected, "fallback_provider": fallback_provider, "fallback_reason": str(exc)})

    def _provider(self, provider_id: str) -> ReasoningProvider:
        return self.providers.get(provider_id) or self.providers["deterministic"]

    def usage_snapshot(self) -> dict[str, Any]:
        settings = get_settings()
        with self._usage_lock:
            self._reset_usage_if_needed()
            used = self._daily_requests
            limit = settings.max_daily_reasoning_requests
            return {
                "date": self._usage_date,
                "requests_used": used,
                "requests_limit": limit,
                "requests_remaining": max(0, limit - used),
                "budget_exceeded": used >= limit,
                "provider_usage": dict(self._provider_usage),
                "fallback_count": self._fallback_count,
                "recent_failures": list(self._failure_log[-10:]),
            }

    def reset_usage(self) -> None:
        with self._usage_lock:
            self._usage_date = date.today().isoformat()
            self._daily_requests = 0
            self._provider_usage = {}
            self._fallback_count = 0
            self._failure_log = []

    def _budget_exceeded(self, limit: int) -> bool:
        with self._usage_lock:
            self._reset_usage_if_needed()
            return self._daily_requests >= limit

    def _record_usage(self, provider: str, fallback_used: bool) -> None:
        with self._usage_lock:
            self._reset_usage_if_needed()
            self._daily_requests += 1
            self._provider_usage[provider] = self._provider_usage.get(provider, 0) + 1
            if fallback_used:
                self._fallback_count += 1

    def _record_failure(self, provider: str, reason: str) -> None:
        with self._usage_lock:
            self._reset_usage_if_needed()
            self._failure_log.append({"provider": provider, "reason": reason, "at": datetime.now(timezone.utc).isoformat()})
            self._failure_log = self._failure_log[-25:]

    def _reset_usage_if_needed(self) -> None:
        today = date.today().isoformat()
        if self._usage_date != today:
            self._usage_date = today
            self._daily_requests = 0
            self._provider_usage = {}
            self._fallback_count = 0
            self._failure_log = []


reasoning_gateway = ReasoningGateway()

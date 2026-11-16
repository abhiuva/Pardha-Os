from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel

from app.reasoning.client import (
    ModelManagerAction,
    OllamaUnavailable,
    generate_response,
    ollama_status,
    set_ollama_enabled,
    start_model,
    stop_model,
    switch_model,
)
from app.settings import get_settings


ProviderName = Literal["deterministic", "openai", "ollama", "claude", "gemini"]


class ProviderActionRequest(BaseModel):
    provider: ProviderName = "ollama"
    model: str | None = None
    prompt: str | None = None


class ProviderModelRequest(BaseModel):
    provider: ProviderName = "ollama"
    model: str


class ProviderStatus(BaseModel):
    provider: ProviderName
    display_name: str
    enabled: bool
    configured: bool
    connected: bool
    ready: bool
    priority: int
    state: str
    current_model: str | None = None
    default_model: str | None = None
    available_models: list[str] = []
    latency_ms: int | None = None
    tokens: int | None = None
    context_length: int | None = None
    memory_usage: str | None = None
    model_size: str | None = None
    last_health_check: datetime | None = None
    message: str
    future: bool = False


class ProviderManagerStatus(BaseModel):
    ready: bool
    execution_mode: str
    active_provider: ProviderName | None
    active_model: str | None
    provider_priority: list[ProviderName]
    timeout_seconds: dict[str, float | int]
    daily_budget: dict[str, Any]
    providers: list[ProviderStatus]


class ProviderActionResponse(BaseModel):
    status: str
    provider: ProviderName
    model: str | None = None
    message: str
    sample: str | None = None


_health_lock = threading.Lock()
_last_health_check: datetime | None = None
_last_verified_latency_ms: int | None = None
_last_sample: str | None = None
_monitor_lock = threading.Lock()
_monitor_stop = threading.Event()
_monitor_thread: threading.Thread | None = None


class ReasoningProviderManager:
    provider_priority: list[ProviderName] = ["openai", "deterministic", "ollama", "claude", "gemini"]

    def status(self, verify: bool = False) -> ProviderManagerStatus:
        settings = get_settings()
        providers_by_id = {
            "openai": self._openai_status(),
            "deterministic": self._deterministic_status(),
            "ollama": self._ollama_status(verify=verify),
            **{provider.provider: provider for provider in self._future_provider_statuses()},
        }
        selected = settings.reasoning_provider if settings.reasoning_provider in providers_by_id else "deterministic"
        ordered_ids = [selected, *[item for item in self.provider_priority if item != selected]]
        providers = [providers_by_id[item] for item in ordered_ids if item in providers_by_id]
        active = next((item for item in providers if item.ready), None)
        from app.reasoning.gateway import reasoning_gateway

        return ProviderManagerStatus(
            ready=active is not None,
            execution_mode="Cloud Assisted / Tool Driven",
            active_provider=active.provider if active else None,
            active_model=active.current_model if active else None,
            provider_priority=ordered_ids,
            timeout_seconds={
                "connection": settings.ollama_connection_timeout,
                "inference": settings.ollama_inference_timeout,
                "retry_limit": settings.ollama_retry_limit,
            },
            daily_budget=reasoning_gateway.usage_snapshot(),
            providers=providers,
        )

    def enable(self, provider: ProviderName = "ollama", model: str | None = None) -> ProviderActionResponse:
        self._require_ollama(provider)
        set_ollama_enabled(True)
        action = start_model(model) if model else ModelManagerAction(status="enabled", model=ollama_status().current_model, message="Ollama provider enabled.")
        return ProviderActionResponse(status=action.status, provider="ollama", model=action.model, message=action.message)

    def disable(self, provider: ProviderName = "ollama") -> ProviderActionResponse:
        self._require_ollama(provider)
        try:
            action = stop_model()
            message = action.message
            model = action.model
        except OllamaUnavailable as exc:
            message = str(exc)
            model = ollama_status().current_model
        set_ollama_enabled(False)
        return ProviderActionResponse(status="disabled", provider="ollama", model=model, message=message)

    def models(self, provider: ProviderName = "ollama") -> list[str]:
        if provider == "openai":
            return [get_settings().openai_model]
        if provider == "deterministic":
            return ["pardha-deterministic-runtime"]
        self._require_ollama(provider)
        return ollama_status().available_models

    def switch(self, request: ProviderModelRequest) -> ProviderActionResponse:
        self._require_ollama(request.provider)
        action = switch_model(request.model)
        return ProviderActionResponse(status=action.status, provider="ollama", model=action.model, message=action.message)

    def pull(self, request: ProviderModelRequest) -> ProviderActionResponse:
        self._require_ollama(request.provider)
        set_ollama_enabled(True)
        executable = shutil.which("ollama")
        if not executable:
            raise OllamaUnavailable("The local Ollama executable was not found.")
        try:
            subprocess.run([executable, "pull", request.model], check=True, capture_output=True, text=True, timeout=max(30, get_settings().ollama_inference_timeout))
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            raise OllamaUnavailable(f"Model pull failed: {exc}") from exc
        action = switch_model(request.model)
        return ProviderActionResponse(status="pulled", provider="ollama", model=action.model, message=f"{request.model} is installed and selected.")

    def test_connection(self, request: ProviderActionRequest) -> ProviderActionResponse:
        if request.provider == "deterministic":
            return ProviderActionResponse(status="ready", provider="deterministic", model="pardha-deterministic-runtime", message="Deterministic tool-driven reasoning is available without GPU or Ollama.", sample="Pardha can run command-center workflows through registered tools.")
        if request.provider == "openai":
            if not get_settings().openai_api_key:
                raise OllamaUnavailable("OpenAI provider is not configured. Set OPENAI_API_KEY to enable cloud reasoning.")
            return ProviderActionResponse(status="configured", provider="openai", model=get_settings().openai_model, message="OpenAI provider is configured for cloud-assisted reasoning.")
        self._require_ollama(request.provider)
        prompt = request.prompt or "Reply with one short sentence confirming Pardha reasoning is online."
        set_ollama_enabled(True)
        if request.model:
            switch_model(request.model)
        started = time.monotonic()
        sample = generate_response(prompt, "You are Pardha's local reasoning health check.", request.model)
        latency = int((time.monotonic() - started) * 1000)
        with _health_lock:
            global _last_health_check, _last_verified_latency_ms, _last_sample
            _last_health_check = datetime.now(timezone.utc)
            _last_verified_latency_ms = latency
            _last_sample = sample
        return ProviderActionResponse(status="ready", provider="ollama", model=ollama_status().current_model, message=f"Inference completed in {latency}ms.", sample=sample)

    def _deterministic_status(self) -> ProviderStatus:
        return ProviderStatus(
            provider="deterministic",
            display_name="Pardha Deterministic Runtime",
            enabled=True,
            configured=True,
            connected=True,
            ready=True,
            priority=2,
            state="Ready",
            current_model="pardha-deterministic-runtime",
            default_model="pardha-deterministic-runtime",
            available_models=["pardha-deterministic-runtime"],
            context_length=None,
            memory_usage="No GPU required",
            model_size="Tool-driven",
            last_health_check=datetime.now(timezone.utc),
            message="Default runtime for MVP: no Ollama, no local GPU, no external write without approval.",
        )

    def _openai_status(self) -> ProviderStatus:
        settings = get_settings()
        configured = bool(settings.openai_api_key)
        return ProviderStatus(
            provider="openai",
            display_name="OpenAI",
            enabled=configured,
            configured=configured,
            connected=configured,
            ready=configured,
            priority=1,
            state="Configured" if configured else "Missing credentials",
            current_model=settings.openai_model,
            default_model=settings.openai_model,
            available_models=[settings.openai_model] if configured else [],
            context_length=None,
            memory_usage="Cloud provider",
            model_size="Cloud",
            last_health_check=datetime.now(timezone.utc) if configured else None,
            message="Cloud reasoning provider configured." if configured else "Set OPENAI_API_KEY to enable cloud-assisted reasoning.",
        )

    def _ollama_status(self, verify: bool = False) -> ProviderStatus:
        status = ollama_status()
        with _health_lock:
            last_health_check = _last_health_check
            verified_latency = _last_verified_latency_ms
        if verify and status.connected and status.model_available:
            try:
                self.test_connection(ProviderActionRequest(provider="ollama", model=status.current_model))
                status = ollama_status()
                with _health_lock:
                    last_health_check = _last_health_check
                    verified_latency = _last_verified_latency_ms
            except OllamaUnavailable:
                pass
        running = self._ollama_daemon_running()
        latency = verified_latency if verified_latency is not None else status.latency_ms
        ready = status.connected and status.model_available and status.reasoning_status != "disabled"
        return ProviderStatus(
            provider="ollama",
            display_name="Ollama",
            enabled=status.reasoning_status != "disabled",
            configured=True,
            connected=status.connected,
            ready=ready,
            priority=1,
            state="Connected" if ready else ("Daemon Running" if running else ("Disabled" if status.reasoning_status == "disabled" else "Disconnected")),
            current_model=status.current_model,
            default_model=status.model,
            available_models=status.available_models,
            latency_ms=latency,
            tokens=status.tokens,
            context_length=status.context_size,
            memory_usage="Local daemon" if running else "Not running",
            model_size=self._model_size(status.current_model, status.available_models),
            last_health_check=last_health_check or status.last_used_at,
            message=status.message,
        )

    def _future_provider_statuses(self) -> list[ProviderStatus]:
        return [
            ProviderStatus(
                provider=name,
                display_name=display,
                enabled=False,
                configured=False,
                connected=False,
                ready=False,
                priority=index,
                state="Future provider",
                message="Disabled until configured.",
                future=True,
            )
            for index, (name, display) in enumerate((("claude", "Claude"), ("gemini", "Gemini")), start=4)
        ]

    def _ollama_daemon_running(self) -> bool:
        try:
            request = Request(f"{get_settings().ollama_url}/api/tags", method="GET")
            with urlopen(request, timeout=get_settings().ollama_connection_timeout) as response:
                json.loads(response.read().decode("utf-8"))
            return True
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
            return False

    def _model_size(self, current_model: str | None, available_models: list[str]) -> str | None:
        if not current_model:
            return None
        if current_model not in available_models:
            return "Not installed"
        if "3b" in current_model.lower():
            return "Small local model"
        if "8b" in current_model.lower():
            return "Medium local model"
        return "Installed"

    def _require_ollama(self, provider: ProviderName) -> None:
        if provider != "ollama":
            raise OllamaUnavailable(f"{provider} is not configured yet.")


provider_manager = ReasoningProviderManager()


def start_provider_health_monitor(interval_seconds: int = 30) -> None:
    global _monitor_thread
    with _monitor_lock:
        if _monitor_thread and _monitor_thread.is_alive():
            return
        _monitor_stop.clear()

        def monitor() -> None:
            while not _monitor_stop.wait(interval_seconds):
                try:
                    provider_manager.status(verify=False)
                    with _health_lock:
                        global _last_health_check
                        _last_health_check = datetime.now(timezone.utc)
                except Exception:
                    pass

        _monitor_thread = threading.Thread(target=monitor, name="pardha-provider-health", daemon=True)
        _monitor_thread.start()


def stop_provider_health_monitor() -> None:
    _monitor_stop.set()

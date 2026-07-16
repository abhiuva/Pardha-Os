from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel

from app.settings import get_settings


OLLAMA_MODEL = "qwen3:8b"
_reasoning_lock = threading.BoundedSemaphore(value=get_settings().max_concurrent_reasoning)
_state_lock = threading.Lock()
_startup_lock = threading.Lock()
_active_reasoning = 0
_ollama_process: subprocess.Popen | None = None
_selected_model = get_settings().default_reasoning_model
_last_latency_ms: int | None = None
_last_token_count: int | None = None
_last_used_at: datetime | None = None
_last_error: str | None = None
_idle_timer: threading.Timer | None = None


class OllamaUnavailable(RuntimeError):
    pass


class OllamaStatus(BaseModel):
    connected: bool
    model: str
    current_model: str
    model_available: bool
    available_models: list[str]
    state: str
    mode: str
    max_concurrent_reasoning: int
    latency_ms: int | None = None
    tokens: int | None = None
    context_size: int
    reasoning_status: str
    idle_timeout_seconds: int
    last_used_at: datetime | None = None
    message: str


class ModelSwitchRequest(BaseModel):
    model: str


class ModelManagerAction(BaseModel):
    status: str
    model: str
    message: str


def _enabled() -> bool:
    return get_settings().ollama_enabled


def _request(path: str, payload: Optional[dict] = None) -> dict:
    if not _enabled():
        raise OllamaUnavailable("Ollama reasoning is disabled.")

    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{get_settings().ollama_url}{path}",
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method="POST" if body else "GET",
    )
    try:
        with urlopen(request, timeout=get_settings().ollama_timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise OllamaUnavailable(f"Local Ollama request failed: {exc}") from exc


def ensure_ollama_running() -> None:
    global _ollama_process
    if not _enabled():
        raise OllamaUnavailable("Ollama reasoning is disabled.")
    try:
        _request("/api/tags")
        return
    except OllamaUnavailable:
        pass

    with _startup_lock:
        try:
            _request("/api/tags")
            return
        except OllamaUnavailable:
            executable = shutil.which("ollama")
            if not executable:
                raise OllamaUnavailable("The local Ollama executable was not found.")
            try:
                _ollama_process = subprocess.Popen(
                    [executable, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError as exc:
                raise OllamaUnavailable(f"The local Ollama server could not start: {exc}") from exc
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    _request("/api/tags")
                    return
                except OllamaUnavailable:
                    time.sleep(0.25)
            raise OllamaUnavailable("The local Ollama server did not start within 10 seconds.")


def _runtime_model(model: str | None = None) -> str:
    return model or _selected_model or get_settings().default_reasoning_model


def _mark_error(message: str | None) -> None:
    global _last_error
    with _state_lock:
        _last_error = message


def _schedule_idle_stop(model: str) -> None:
    global _idle_timer
    settings = get_settings()
    if _idle_timer:
        _idle_timer.cancel()

    def stop_when_idle() -> None:
        with _state_lock:
            active = _active_reasoning
            last_used = _last_used_at
        if active:
            _schedule_idle_stop(model)
            return
        if last_used and (datetime.now(timezone.utc) - last_used).total_seconds() < settings.ollama_idle_timeout_seconds:
            _schedule_idle_stop(model)
            return
        try:
            unload_model(model)
        except OllamaUnavailable:
            pass

    _idle_timer = threading.Timer(settings.ollama_idle_timeout_seconds, stop_when_idle)
    _idle_timer.daemon = True
    _idle_timer.start()


def unload_model(model: str | None = None) -> None:
    selected_model = _runtime_model(model)
    _request(
        "/api/generate",
        {"model": selected_model, "prompt": "", "stream": False, "keep_alive": 0},
    )


def start_model(model: str | None = None) -> ModelManagerAction:
    selected_model = switch_model(model or _runtime_model()).model
    ensure_ollama_running()
    _request(
        "/api/generate",
        {"model": selected_model, "prompt": "", "stream": False, "keep_alive": f"{get_settings().ollama_idle_timeout_seconds}s"},
    )
    _schedule_idle_stop(selected_model)
    _mark_error(None)
    return ModelManagerAction(status="started", model=selected_model, message="Model is loaded on demand.")


def stop_model(model: str | None = None) -> ModelManagerAction:
    selected_model = _runtime_model(model)
    unload_model(selected_model)
    _mark_error(None)
    return ModelManagerAction(status="stopped", model=selected_model, message="Model unloaded after idle timeout or user request.")


def switch_model(model: str) -> ModelManagerAction:
    global _selected_model
    if not model:
        raise OllamaUnavailable("Model name is required.")
    with _state_lock:
        _selected_model = model
    return ModelManagerAction(status="selected", model=model, message="Runtime model selection updated.")


def generate_response(prompt: str, system_prompt: str | None = None, model: str | None = None) -> str:
    global _active_reasoning, _last_latency_ms, _last_token_count, _last_used_at, _last_error
    settings = get_settings()
    selected_model = _runtime_model(model)
    payload = {
        "model": selected_model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "keep_alive": f"{settings.ollama_idle_timeout_seconds}s",
        "options": {
            "temperature": 0.2,
            "num_predict": settings.ollama_max_tokens,
            "num_ctx": settings.ollama_context_size,
        },
    }
    if system_prompt:
        payload["system"] = system_prompt
    with _reasoning_lock:
        ensure_ollama_running()
        with _state_lock:
            _active_reasoning += 1
        try:
            started = time.monotonic()
            result = _request("/api/generate", payload)
            response = result.get("response")
            with _state_lock:
                _last_latency_ms = int((time.monotonic() - started) * 1000)
                _last_token_count = int(result.get("eval_count") or result.get("prompt_eval_count") or 0)
                _last_used_at = datetime.now(timezone.utc)
                _last_error = None
            _schedule_idle_stop(selected_model)
        finally:
            with _state_lock:
                _active_reasoning -= 1
    if not isinstance(response, str) or not response.strip():
        raise OllamaUnavailable("Local Ollama returned an empty response.")
    return response.strip()


def summarize(content: str, model: str | None = None) -> str:
    return generate_response(
        f"Summarize the following business context concisely:\n\n{content}",
        "You are a concise business intelligence summarizer.",
        model,
    )


def analyze(content: str, model: str | None = None) -> str:
    return generate_response(
        f"Analyze the following context and provide recommendations, opportunities, and risks:\n\n{content}",
        "You are a rigorous local reasoning engine for Pardha.",
        model,
    )


def ollama_status() -> OllamaStatus:
    settings = get_settings()
    with _state_lock:
        selected_model = _selected_model or settings.default_reasoning_model
        latency = _last_latency_ms
        tokens = _last_token_count
        last_used = _last_used_at
        last_error = _last_error
    if not settings.ollama_enabled:
        return OllamaStatus(
            connected=False,
            model=selected_model,
            current_model=selected_model,
            model_available=False,
            available_models=[],
            state="Disabled",
            mode=settings.mode.value,
            max_concurrent_reasoning=settings.max_concurrent_reasoning,
            latency_ms=latency,
            tokens=tokens,
            context_size=settings.ollama_context_size,
            reasoning_status="disabled",
            idle_timeout_seconds=settings.ollama_idle_timeout_seconds,
            last_used_at=last_used,
            message="Manual Ollama reasoning is disabled.",
        )
    try:
        models = [
            item.get("name", "")
            for item in _request("/api/tags").get("models", [])
            if item.get("name")
        ]
        running_models = [
            item.get("name", "")
            for item in _request("/api/ps").get("models", [])
            if item.get("name")
        ]
        with _state_lock:
            active = _active_reasoning
        current_model = running_models[0] if running_models else selected_model
        state = "Running" if active or running_models else "Idle"
        return OllamaStatus(
            connected=True,
            model=selected_model,
            current_model=current_model,
            model_available=selected_model in models,
            available_models=models,
            state=state,
            mode=settings.mode.value,
            max_concurrent_reasoning=settings.max_concurrent_reasoning,
            latency_ms=latency,
            tokens=tokens,
            context_size=settings.ollama_context_size,
            reasoning_status="reasoning" if active else ("loaded" if running_models else "idle"),
            idle_timeout_seconds=settings.ollama_idle_timeout_seconds,
            last_used_at=last_used,
            message=last_error or state,
        )
    except OllamaUnavailable as exc:
        _mark_error(str(exc))
        return OllamaStatus(
            connected=False,
            model=selected_model,
            current_model=selected_model,
            model_available=False,
            available_models=[],
            state="Disabled",
            mode=settings.mode.value,
            max_concurrent_reasoning=settings.max_concurrent_reasoning,
            latency_ms=latency,
            tokens=tokens,
            context_size=settings.ollama_context_size,
            reasoning_status="offline",
            idle_timeout_seconds=settings.ollama_idle_timeout_seconds,
            last_used_at=last_used,
            message=str(exc),
        )

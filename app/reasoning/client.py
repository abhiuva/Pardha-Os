from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel

from app.settings import get_settings


OLLAMA_MODEL = "llama3.2:3b"
_reasoning_lock = threading.BoundedSemaphore(value=get_settings().max_concurrent_reasoning)
_state_lock = threading.Lock()
_startup_lock = threading.Lock()
_active_reasoning = 0
_ollama_process: subprocess.Popen | None = None


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


def generate_response(prompt: str, system_prompt: str | None = None, model: str | None = None) -> str:
    global _active_reasoning
    selected_model = model or get_settings().default_reasoning_model
    payload = {
        "model": selected_model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "keep_alive": 0,
        "options": {
            "temperature": 0.2,
            "num_predict": get_settings().ollama_max_tokens,
        },
    }
    if system_prompt:
        payload["system"] = system_prompt
    with _reasoning_lock:
        ensure_ollama_running()
        with _state_lock:
            _active_reasoning += 1
        try:
            response = _request("/api/generate", payload).get("response")
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
    if not settings.ollama_enabled:
        return OllamaStatus(
            connected=False,
            model=settings.default_reasoning_model,
            current_model=settings.default_reasoning_model,
            model_available=False,
            available_models=[],
            state="Disabled",
            mode=settings.mode.value,
            max_concurrent_reasoning=settings.max_concurrent_reasoning,
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
        current_model = running_models[0] if running_models else settings.default_reasoning_model
        state = "Running" if active or running_models else "Idle"
        return OllamaStatus(
            connected=True,
            model=settings.default_reasoning_model,
            current_model=current_model,
            model_available=settings.default_reasoning_model in models,
            available_models=models,
            state=state,
            mode=settings.mode.value,
            max_concurrent_reasoning=settings.max_concurrent_reasoning,
            message=state,
        )
    except OllamaUnavailable:
        return OllamaStatus(
            connected=False,
            model=settings.default_reasoning_model,
            current_model=settings.default_reasoning_model,
            model_available=False,
            available_models=[],
            state="Disabled",
            mode=settings.mode.value,
            max_concurrent_reasoning=settings.max_concurrent_reasoning,
            message="Disabled",
        )

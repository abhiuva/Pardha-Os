from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.ai.provider_manager import (
    ProviderActionRequest,
    ProviderActionResponse,
    ProviderManagerStatus,
    ProviderModelRequest,
    ProviderStatus,
    provider_manager,
)
from app.reasoning.client import OllamaUnavailable, OllamaStatus, ollama_status


router = APIRouter(tags=["ai-providers"])


def _provider_error(exc: OllamaUnavailable) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/ai/providers", response_model=ProviderManagerStatus)
def get_ai_providers():
    return provider_manager.status()


@router.get("/ai/providers/status", response_model=ProviderManagerStatus)
def get_ai_provider_status():
    return provider_manager.status(verify=False)


@router.post("/ai/providers/enable", response_model=ProviderActionResponse)
def enable_ai_provider(request: ProviderActionRequest = ProviderActionRequest()):
    try:
        return provider_manager.enable(request.provider, request.model)
    except OllamaUnavailable as exc:
        raise _provider_error(exc) from exc


@router.post("/ai/providers/disable", response_model=ProviderActionResponse)
def disable_ai_provider(request: ProviderActionRequest = ProviderActionRequest()):
    try:
        return provider_manager.disable(request.provider)
    except OllamaUnavailable as exc:
        raise _provider_error(exc) from exc


@router.get("/ai/providers/models", response_model=list[str])
def get_ai_provider_models(provider: str = "ollama"):
    try:
        return provider_manager.models(provider)  # type: ignore[arg-type]
    except OllamaUnavailable as exc:
        raise _provider_error(exc) from exc


@router.post("/ai/providers/models", response_model=ProviderActionResponse)
def switch_ai_provider_model(request: ProviderModelRequest):
    try:
        return provider_manager.switch(request)
    except OllamaUnavailable as exc:
        raise _provider_error(exc) from exc


@router.post("/ai/providers/pull", response_model=ProviderActionResponse)
def pull_ai_provider_model(request: ProviderModelRequest):
    try:
        return provider_manager.pull(request)
    except OllamaUnavailable as exc:
        raise _provider_error(exc) from exc


@router.post("/ai/providers/test", response_model=ProviderActionResponse)
def test_ai_provider(request: ProviderActionRequest = ProviderActionRequest()):
    try:
        return provider_manager.test_connection(request)
    except OllamaUnavailable as exc:
        raise _provider_error(exc) from exc


@router.get("/status/ollama", response_model=OllamaStatus)
def get_ollama_status_alias():
    return ollama_status()


@router.get("/status/models", response_model=list[str])
def get_model_status_alias():
    return ollama_status().available_models


@router.get("/status/providers", response_model=list[ProviderStatus])
def get_provider_status_alias():
    return provider_manager.status().providers

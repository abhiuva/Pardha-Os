from fastapi import APIRouter

from app.system.database import DatabaseStatus, database_status
from app.reasoning.client import (
    ModelManagerAction,
    ModelSwitchRequest,
    OllamaStatus,
    ollama_status,
    start_model,
    stop_model,
    switch_model,
)


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/database/status", response_model=DatabaseStatus)
def get_database_status():
    return database_status()


@router.get("/ollama/status", response_model=OllamaStatus)
def get_ollama_status():
    return ollama_status()


@router.post("/ollama/start", response_model=ModelManagerAction)
def start_ollama_model(request: ModelSwitchRequest | None = None):
    return start_model(request.model if request else None)


@router.post("/ollama/stop", response_model=ModelManagerAction)
def stop_ollama_model(request: ModelSwitchRequest | None = None):
    return stop_model(request.model if request else None)


@router.post("/ollama/switch", response_model=ModelManagerAction)
def switch_ollama_model(request: ModelSwitchRequest):
    return switch_model(request.model)

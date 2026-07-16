from fastapi import APIRouter

from app.system.database import DatabaseStatus, database_status
from app.reasoning.client import OllamaStatus, ollama_status


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/database/status", response_model=DatabaseStatus)
def get_database_status():
    return database_status()


@router.get("/ollama/status", response_model=OllamaStatus)
def get_ollama_status():
    return ollama_status()

from __future__ import annotations

from typing import Any

from app.capabilities.service import capability_health, list_capabilities
from app.commercial.service import connector_statuses
from app.db import SessionLocal
from app.db.models import (
    Business,
    ConversationMessage,
    FounderOperationalLearning,
    Knowledge,
    RuntimeExecution,
    RuntimeQueueItem,
)
from app.reasoning.client import ollama_status
from app.ai.provider_manager import provider_manager
from app.system.database import database_status


def inspect_runtime(message: str = "", context: dict[str, Any] | None = None) -> dict[str, Any]:
    db = database_status()
    caps = list_capabilities()
    health = capability_health()
    connectors = connector_statuses()
    ollama = ollama_status()
    providers = provider_manager.status()
    business_id = (context or {}).get("business_id")

    with SessionLocal() as session:
        business_query = session.query(Business)
        businesses = business_query.order_by(Business.business_name.asc()).all()
        knowledge_query = session.query(Knowledge)
        messages_query = session.query(ConversationMessage)
        learning_query = session.query(FounderOperationalLearning)
        if business_id:
            knowledge_query = knowledge_query.filter(Knowledge.business_id == business_id)
            messages_query = messages_query.filter(ConversationMessage.business_id == business_id)
            learning_query = learning_query.filter(FounderOperationalLearning.business_id == business_id)
        running = session.query(RuntimeExecution).filter(RuntimeExecution.status.in_(("running", "queued"))).count()
        queue = session.query(RuntimeQueueItem).filter(RuntimeQueueItem.status.in_(("queued", "running"))).count()
        learning = learning_query.order_by(FounderOperationalLearning.updated_at.desc()).limit(8).all()

    return {
        "query": message,
        "database": {
            "connected": db.connected,
            "database_name": db.database_name,
            "scheduler_status": db.scheduler_status,
            "table_count": len(db.tables_found),
            "record_counts": db.record_counts,
        },
        "businesses": [
            {"business_id": item.business_id, "business_name": item.business_name, "business_type": item.business_type, "status": item.status}
            for item in businesses
        ],
        "active_business_id": business_id,
        "knowledge": {"count": knowledge_query.count()},
        "conversation": {"messages": messages_query.count()},
        "capabilities": {
            "total": health.total,
            "healthy": health.healthy,
            "degraded": health.degraded,
            "unavailable": health.unavailable,
            "items": [
                {
                    "capability_id": item.capability_id,
                    "name": item.name,
                    "health": item.health,
                    "status": item.current_status,
                    "intents": item.supported_intents[:5],
                }
                for item in caps
            ],
        },
        "connectors": [item.model_dump(mode="json") for item in connectors],
        "ollama": ollama.model_dump(mode="json"),
        "ai_providers": providers.model_dump(mode="json"),
        "runtime": {"running_executions": running, "queued_items": queue},
        "learning": [
            {
                "signal_type": item.signal_type,
                "signal_key": item.signal_key,
                "signal_value": item.signal_value,
                "confidence": item.confidence,
            }
            for item in learning
        ],
    }


def relevant_connectors(runtime: dict[str, Any], text: str) -> list[dict[str, Any]]:
    lowered = text.lower()
    connectors = runtime.get("connectors", [])
    selected = [
        item
        for item in connectors
        if item.get("provider", "").lower() in lowered or item.get("name", "").lower() in lowered
    ]
    if not selected and any(term in lowered for term in ("email", "gmail")):
        selected = [item for item in connectors if item.get("provider") in {"gmail", "outlook"}]
    return selected

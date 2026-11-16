from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.db import SessionLocal
from app.db.models import Memory as MemoryModel


class MemoryBase(BaseModel):
    business_id: Optional[str] = None
    agent_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryCreate(MemoryBase):
    pass


class Memory(MemoryBase):
    model_config = ConfigDict(from_attributes=True)

    memory_id: UUID
    timestamp: datetime


def _model_to_dict(model: BaseModel) -> Dict[str, Any]:
    if isinstance(model, dict):
        return model
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _row_to_memory(memory: MemoryModel) -> Memory:
    return Memory(
        memory_id=memory.memory_id,
        business_id=memory.business_id,
        agent_id=memory.agent_id,
        content=memory.content,
        metadata=memory.metadata_json,
        timestamp=memory.timestamp,
    )


def save_memory(memory_data: MemoryCreate) -> Memory:
    memory_payload = _model_to_dict(memory_data)
    from app.business.service import resolve_business

    business = resolve_business(
        business_id=memory_payload.get("business_id"),
        business_name=memory_payload.get("metadata", {}).get("business_name"),
        text=f"{memory_payload.get('content', '')} {memory_payload.get('metadata', {})}",
    )
    memory_row = MemoryModel(
        memory_id=str(uuid4()),
        business_id=business.business_id,
        timestamp=datetime.now(timezone.utc),
        agent_id=memory_payload["agent_id"],
        content=memory_payload["content"],
        metadata_json=memory_payload["metadata"],
    )

    with SessionLocal() as session:
        session.add(memory_row)
        session.commit()
        session.refresh(memory_row)

    return _row_to_memory(memory_row)


def get_memories(business_id: Optional[str] = None) -> List[Memory]:
    from app.business.service import get_active_business

    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        memory_rows = session.query(MemoryModel).filter(MemoryModel.business_id == resolved_business_id).all()
    return [_row_to_memory(memory) for memory in memory_rows]


def get_memories_by_agent(agent_id: str, business_id: Optional[str] = None) -> List[Memory]:
    from app.business.service import get_active_business

    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        memory_rows = (
            session.query(MemoryModel)
            .filter(MemoryModel.business_id == resolved_business_id, MemoryModel.agent_id == agent_id)
            .all()
        )
    return [_row_to_memory(memory) for memory in memory_rows]


def search_memories(query: str, business_id: Optional[str] = None) -> List[Memory]:
    normalized_query = query.lower().strip()
    from app.business.service import get_active_business

    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        memory_rows = session.query(MemoryModel).filter(MemoryModel.business_id == resolved_business_id).all()

    if not normalized_query:
        return [_row_to_memory(memory) for memory in memory_rows]

    results: List[Memory] = []
    for memory in memory_rows:
        metadata_text = " ".join(
            str(value).lower()
            for value in memory.metadata_json.values()
            if value is not None
        )
        if (
            normalized_query in memory.content.lower()
            or normalized_query in memory.agent_id.lower()
            or normalized_query in metadata_text
        ):
            results.append(_row_to_memory(memory))

    return results


def clear_memories() -> None:
    with SessionLocal() as session:
        session.query(MemoryModel).delete()
        session.commit()

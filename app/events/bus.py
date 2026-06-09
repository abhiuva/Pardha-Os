from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventBase(BaseModel):
    source_agent: str = Field(..., min_length=1)
    target_agent: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


class EventCreate(EventBase):
    pass


class Event(EventBase):
    event_id: UUID
    timestamp: datetime

    class Config:
        orm_mode = True


EVENTS: List[Event] = []


def _model_to_dict(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def publish_event(event_data: EventCreate) -> Event:
    event_payload = _model_to_dict(event_data)
    event = Event(
        event_id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        **event_payload,
    )
    EVENTS.append(event)
    return event


def get_events() -> List[Event]:
    return list(EVENTS)


def get_events_by_agent(agent_id: str) -> List[Event]:
    return [
        event
        for event in EVENTS
        if event.source_agent == agent_id or event.target_agent == agent_id
    ]


def clear_events() -> None:
    EVENTS.clear()

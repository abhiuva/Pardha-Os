from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.db import SessionLocal
from app.db.models import Event as EventModel


class EventBase(BaseModel):
    business_id: Optional[str] = None
    source_agent: str = Field(..., min_length=1)
    target_agent: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


class EventCreate(EventBase):
    pass


class Event(EventBase):
    model_config = ConfigDict(from_attributes=True)

    event_id: UUID
    timestamp: datetime


def _model_to_dict(model: BaseModel) -> Dict[str, Any]:
    if isinstance(model, dict):
        return model
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _row_to_event(event: EventModel) -> Event:
    return Event(
        event_id=event.event_id,
        business_id=event.business_id,
        source_agent=event.source_agent,
        target_agent=event.target_agent,
        event_type=event.event_type,
        payload=event.payload,
        timestamp=event.timestamp,
    )


def publish_event(event_data: EventCreate) -> Event:
    event_payload = _model_to_dict(event_data)
    from app.business.service import resolve_business

    business = resolve_business(
        business_id=event_payload.get("business_id"),
        business_name=event_payload.get("payload", {}).get("business_name"),
        text=" ".join(str(value) for value in event_payload.get("payload", {}).values()),
    )
    event_row = EventModel(
        event_id=str(uuid4()),
        business_id=business.business_id,
        timestamp=datetime.now(timezone.utc),
        source_agent=event_payload["source_agent"],
        target_agent=event_payload["target_agent"],
        event_type=event_payload["event_type"],
        payload=event_payload["payload"],
    )

    with SessionLocal() as session:
        session.add(event_row)
        session.commit()
        session.refresh(event_row)

    return _row_to_event(event_row)


def get_events(business_id: Optional[str] = None) -> List[Event]:
    from app.business.service import get_active_business

    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        event_rows = session.query(EventModel).filter(EventModel.business_id == resolved_business_id).all()
    return [_row_to_event(event) for event in event_rows]


def get_events_by_agent(agent_id: str, business_id: Optional[str] = None) -> List[Event]:
    from app.business.service import get_active_business

    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        event_rows = (
            session.query(EventModel)
            .filter(
                EventModel.business_id == resolved_business_id,
                (EventModel.source_agent == agent_id)
                | (EventModel.target_agent == agent_id)
            )
            .all()
        )
    return [_row_to_event(event) for event in event_rows]


def clear_events() -> None:
    with SessionLocal() as session:
        session.query(EventModel).delete()
        session.commit()

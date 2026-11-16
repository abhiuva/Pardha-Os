from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from app.db import SessionLocal
from app.db.models import MCPEvent, MCPLog


def publish_event(server_id: str, event_type: str, payload: Dict[str, Any] | None = None) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.add(MCPEvent(event_id=str(uuid4()), server_id=server_id, event_type=event_type, payload=payload or {}, created_at=now))
        session.commit()


def write_log(server_id: str, level: str, message: str, context: Dict[str, Any] | None = None) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.add(MCPLog(log_id=str(uuid4()), server_id=server_id, level=level, message=message, context=context or {}, created_at=now))
        session.commit()

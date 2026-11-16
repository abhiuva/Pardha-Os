from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from app.db import SessionLocal
from app.db.models import AgentExecution as AgentExecutionModel


class AgentExecution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    execution_id: str
    business_id: Optional[str] = None
    cycle_id: str
    agent_name: str
    status: str
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


def _row_to_execution(row: AgentExecutionModel) -> AgentExecution:
    return AgentExecution.model_validate(row)


def start_execution(agent_name: str, cycle_id: str, business_id: Optional[str] = None) -> str:
    if business_id is None:
        from app.business.service import get_active_business

        business_id = get_active_business().business_id
    execution_id = str(uuid4())
    row = AgentExecutionModel(
        execution_id=execution_id,
        business_id=business_id,
        cycle_id=cycle_id,
        agent_name=agent_name.lower(),
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
    return execution_id


def complete_execution(
    execution_id: str,
    *,
    status: str,
    output: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> AgentExecution:
    completed_at = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = session.get(AgentExecutionModel, execution_id)
        if row is None:
            raise ValueError(f"Agent execution {execution_id} does not exist.")

        started_at = row.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        row.status = status
        row.output = output
        row.error = error
        row.completed_at = completed_at
        row.duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))
        session.commit()
        session.refresh(row)
        return _row_to_execution(row)


def get_executions(agent_name: Optional[str] = None, business_id: Optional[str] = None) -> List[AgentExecution]:
    if business_id is None:
        from app.business.service import get_active_business

        business_id = get_active_business().business_id
    with SessionLocal() as session:
        query = session.query(AgentExecutionModel)
        query = query.filter(AgentExecutionModel.business_id == business_id)
        if agent_name:
            query = query.filter(AgentExecutionModel.agent_name == agent_name.strip().lower())
        rows = query.order_by(
            AgentExecutionModel.started_at.desc(),
            AgentExecutionModel.execution_id.desc(),
        ).all()
        return [_row_to_execution(row) for row in rows]


def clear_executions() -> None:
    with SessionLocal() as session:
        session.query(AgentExecutionModel).delete()
        session.commit()

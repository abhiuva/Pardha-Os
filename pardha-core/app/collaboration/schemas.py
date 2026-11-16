from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


Priority = Literal["critical", "high", "medium", "low"]
ObjectiveStatus = Literal["NEW", "IN_PROGRESS", "COMPLETED", "BLOCKED"]


class ObjectiveCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    priority: Priority = "medium"


class Objective(ObjectiveCreate):
    model_config = ConfigDict(from_attributes=True)

    objective_id: str
    status: ObjectiveStatus
    created_at: datetime


class AgentCollaboration(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    collaboration_id: str
    business_id: Optional[str] = None
    objective_id: str
    source_agent: str
    target_agent: str
    action: str
    event_type: str
    step_order: int
    status: str
    payload: Dict[str, Any]
    created_at: datetime

    @computed_field
    @property
    def timestamp(self) -> datetime:
        return self.created_at


class Task(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    business_id: Optional[str] = None
    title: str
    description: str | None
    status: str
    assigned_agent: str | None
    payload: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ObjectiveWorkflowResult(BaseModel):
    objective: Objective
    epics: List[str]
    tasks: List[Task]
    collaborations: List[AgentCollaboration]


class ObjectiveDetail(ObjectiveWorkflowResult):
    pass

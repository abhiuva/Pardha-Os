from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RuntimeExecution(BaseModel):
    execution_id: str
    business_id: str
    goal_id: Optional[str]
    plan_id: Optional[str]
    execution_graph: Dict[str, Any]
    current_stage: str
    current_capability: Optional[str]
    logs: List[Dict[str, Any]]
    retries: int
    progress: int
    duration_ms: int
    dependencies: List[str]
    rollback: Dict[str, Any]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class DepartmentRuntime(BaseModel):
    department_id: str
    business_id: str
    name: str
    owner: str
    objectives: List[Dict[str, Any]]
    capabilities: List[str]
    current_work: List[Dict[str, Any]]
    queue: List[Dict[str, Any]]
    kpis: Dict[str, Any]
    health: str
    current_load: int
    dependencies: List[str]
    updated_at: datetime


class RuntimeQueueItem(BaseModel):
    queue_id: str
    business_id: str
    execution_id: Optional[str]
    plan_id: Optional[str]
    capability_id: Optional[str]
    priority: int
    dependencies: List[str]
    retry_count: int
    timeout_ms: int
    scheduled_for: Optional[datetime]
    recurring: bool
    delay_until: Optional[datetime]
    status: str
    payload: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ToolRuntimeInvocation(BaseModel):
    invocation_id: str
    business_id: str
    tool_name: str
    capability_id: Optional[str]
    execution_id: Optional[str]
    status: str
    input_payload: Dict[str, Any]
    output_payload: Optional[Any]
    error: Optional[str]
    duration_ms: int
    created_at: datetime


class RuntimeNotification(BaseModel):
    notification_id: str
    business_id: str
    priority: str
    category: str
    title: str
    message: str
    status: str
    payload: Dict[str, Any]
    created_at: datetime
    read_at: Optional[datetime]
    archived_at: Optional[datetime]


class AutomationRule(BaseModel):
    rule_id: str
    business_id: Optional[str]
    name: str
    trigger_event: str
    action: str
    enabled: bool
    priority: int
    payload: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BusinessTimelineEvent(BaseModel):
    timeline_event_id: str
    business_id: str
    event_type: str
    title: str
    detail: str
    source: str
    payload: Dict[str, Any]
    created_at: datetime


class QueueRequest(BaseModel):
    business_id: str
    plan_id: Optional[str] = None
    capability_id: Optional[str] = None
    priority: int = Field(default=50, ge=0, le=100)
    dependencies: List[str] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)


class RuntimeStartRequest(BaseModel):
    business_id: str
    plan_id: str
    priority: int = Field(default=70, ge=0, le=100)


class AutomationRuleCreate(BaseModel):
    business_id: Optional[str] = None
    name: str
    trigger_event: str
    action: str
    priority: int = Field(default=50, ge=0, le=100)
    payload: Dict[str, Any] = Field(default_factory=dict)


class RuntimeDashboard(BaseModel):
    departments: List[DepartmentRuntime]
    executions: List[RuntimeExecution]
    queue: List[RuntimeQueueItem]
    approvals: List[Dict[str, Any]]
    notifications: List[RuntimeNotification]
    business_timeline: List[BusinessTimelineEvent]
    observability: Dict[str, Any]

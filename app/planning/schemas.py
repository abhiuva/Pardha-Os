from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    business_id: str
    request: str = Field(..., min_length=1)
    owner: str = "Founder"
    priority: str = "high"
    approve: bool = False


class PlanningGoal(BaseModel):
    goal_id: str
    business_id: str
    title: str
    description: str
    priority: str
    owner: str
    department: str
    target_date: Optional[datetime]
    success_metrics: List[str]
    current_status: str
    risk_level: str
    progress: int
    dependencies: List[str]
    created_by: str
    created_at: datetime
    updated_at: datetime


class ExecutionPlanNode(BaseModel):
    node_id: str
    plan_id: str
    goal_id: str
    business_id: str
    node_type: str
    title: str
    description: str
    capability_id: Optional[str]
    status: str
    risk_level: str
    approval_required: bool
    dependencies: List[str]
    parallel_group: Optional[str]
    critical_path: bool
    estimated_runtime_ms: int
    output: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class ExecutionPlan(BaseModel):
    plan_id: str
    goal_id: str
    business_id: str
    title: str
    request: str
    plan_type: str
    status: str
    risk_level: str
    approval_required: bool
    progress: int
    estimated_completion: Optional[datetime]
    summary: str
    capability_ids: List[str]
    graph: Dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime
    nodes: List[ExecutionPlanNode] = Field(default_factory=list)


class PlanApproval(BaseModel):
    approval_id: str
    plan_id: str
    node_id: Optional[str]
    business_id: str
    approval_type: str
    risk_level: str
    title: str
    detail: str
    status: str
    requested_by: str
    decided_by: Optional[str]
    decision_comment: Optional[str]
    created_at: datetime
    decided_at: Optional[datetime]


class PlanExecution(BaseModel):
    execution_id: str
    plan_id: str
    goal_id: str
    business_id: str
    current_step: str
    current_capability: Optional[str]
    progress: int
    estimated_time_ms: int
    logs: List[Dict[str, Any]]
    retry_count: int
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class GoalKPI(BaseModel):
    kpi_id: str
    goal_id: str
    business_id: str
    name: str
    target_value: int
    current_value: int
    unit: str
    status: str
    updated_at: datetime


class PlanningTimelineEvent(BaseModel):
    timeline_event_id: str
    goal_id: str
    plan_id: Optional[str]
    business_id: str
    event_type: str
    title: str
    detail: str
    payload: Dict[str, Any]
    created_at: datetime


class PlanningResult(BaseModel):
    goal: PlanningGoal
    plan: ExecutionPlan
    approvals: List[PlanApproval]
    kpis: List[GoalKPI]
    timeline: List[PlanningTimelineEvent]


class ApprovalDecision(BaseModel):
    decided_by: str = "Founder"
    comment: str = ""


class DailyExecutivePlan(BaseModel):
    business_id: str
    ceo_priorities: List[str]
    marketing_priorities: List[str]
    sales_priorities: List[str]
    engineering_priorities: List[str]
    operations_priorities: List[str]
    qa_priorities: List[str]
    blocked_items: List[str]
    recommended_actions: List[str]

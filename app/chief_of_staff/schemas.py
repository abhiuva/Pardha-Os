from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConversationSummary(BaseModel):
    conversation_id: str
    business_id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_message: Optional[str] = None


class ChiefMessage(BaseModel):
    message_id: str
    conversation_id: str
    business_id: str
    role: str
    content: str
    intent: str
    rich_response: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    conversation_id: Optional[str] = None
    approve: bool = True


class ChatResponse(BaseModel):
    conversation: ConversationSummary
    user_message: ChiefMessage
    assistant_message: ChiefMessage
    suggested_prompts: List[str]


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1)
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    priority: str = "high"
    due_date: Optional[datetime] = None
    owner: str = "Founder"
    success_metrics: List[str] = Field(default_factory=list)


class FounderGoal(BaseModel):
    goal_id: str
    business_id: str
    title: str
    priority: str
    due_date: Optional[datetime]
    owner: str
    status: str
    success_metrics: List[str]
    objective_id: Optional[str]
    plans: Dict[str, Any]
    timeline: List[Dict[str, Any]]
    daily_followups: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class ExecutiveDepartment(BaseModel):
    name: str
    current_status: str
    risks: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    recent_activity: List[str] = Field(default_factory=list)
    kpis: Dict[str, Any] = Field(default_factory=dict)


class ExecutiveCommandCenter(BaseModel):
    business_id: str
    business_name: str
    departments: List[ExecutiveDepartment]
    notifications: List[str] = Field(default_factory=list)
    quick_actions: List[str] = Field(default_factory=list)


class HelpResponse(BaseModel):
    answer: str
    commands: List[str]
    related_actions: List[str]

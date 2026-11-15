from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConnectorStatus(BaseModel):
    name: str
    provider: str
    connected: bool
    health: str
    authentication_status: str
    environment_valid: bool
    required_environment: List[str] = Field(default_factory=list)
    missing_environment: List[str] = Field(default_factory=list)
    account_count: int = 0
    last_sync: Optional[datetime] = None
    message: str


class ConnectorTestResult(BaseModel):
    provider: str
    status: str
    connected: bool
    authentication_status: str
    environment_valid: bool
    message: str


class FounderDashboard(BaseModel):
    business_id: Optional[str]
    business_name: str
    todays_priorities: List[str]
    ceo_summary: str
    engineering_status: str
    sales_pipeline: List[str]
    marketing_summary: str
    open_risks: List[str]
    active_objectives: List[Dict[str, Any]]
    recent_agent_activity: List[Dict[str, Any]]
    recent_executions: List[Dict[str, Any]]
    unread_notifications: List[str]
    counts: Dict[str, int]


class SystemHealth(BaseModel):
    backend: Dict[str, Any]
    database: Dict[str, Any]
    scheduler: Dict[str, Any]
    knowledge_engine: Dict[str, Any]
    agent_engine: Dict[str, Any]
    communications: Dict[str, Any]
    vscode: Dict[str, Any]
    jira: Dict[str, Any]
    ollama: Dict[str, Any]
    resources: Dict[str, Any]
    runtime: Dict[str, Any]


class GuidedJourneyStep(BaseModel):
    step: int
    title: str
    status: str
    detail: str


class GuidedJourney(BaseModel):
    business_id: Optional[str]
    business_name: str
    steps: List[GuidedJourneyStep]
    ready: bool


class DemoLoadResult(BaseModel):
    business_id: str
    business_name: str
    counts: Dict[str, int]
    ceo_brief_generated: bool
    pm_roadmap_generated: bool
    cto_plan_generated: bool
    journey: GuidedJourney

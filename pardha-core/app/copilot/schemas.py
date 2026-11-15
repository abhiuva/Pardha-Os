from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FounderCopilotRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    priority: str = "high"


class FounderCopilotResult(BaseModel):
    business_id: str
    business_name: str
    prompt: str
    business_analysis: Dict[str, Any]
    current_risks: List[str]
    opportunities: List[str]
    recommended_strategy: List[str]
    execution_plan: List[Dict[str, Any]]
    kpis: List[str]
    success_metrics: List[str]
    workflow: Dict[str, Any]
    ceo_strategy: List[str] = Field(default_factory=list)
    pm_roadmap: List[str] = Field(default_factory=list)
    cto_tasks: List[str] = Field(default_factory=list)


class BusinessIntelligenceReport(BaseModel):
    business_id: str
    business_name: str
    swot_analysis: Dict[str, List[str]]
    business_health_score: int
    growth_opportunities: List[str]
    operational_risks: List[str]
    product_risks: List[str]
    customer_risks: List[str]
    ai_opportunities: List[str]
    executive_recommendations: List[str]


class CustomerSuccessWorkspace(BaseModel):
    business_id: str
    company_profile: Dict[str, Any]
    knowledge_base: List[Dict[str, Any]]
    objectives: List[Dict[str, Any]]
    projects: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    executive_briefs: Dict[str, Any]
    meeting_notes: List[Dict[str, Any]]
    communication_history: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]


class ExecutiveBriefBundle(BaseModel):
    daily: Dict[str, Any]
    weekly_executive_summary: Dict[str, Any]
    monthly_business_review: Dict[str, Any]


class BusinessHealthDashboard(BaseModel):
    revenue_goals: Dict[str, Any]
    sales_pipeline: Dict[str, Any]
    marketing_performance: Dict[str, Any]
    engineering_velocity: Dict[str, Any]
    project_status: Dict[str, Any]
    operational_health: Dict[str, Any]
    knowledge_growth: Dict[str, Any]
    risk_score: int
    customer_health: Dict[str, Any]
    ai_recommendations: List[str]


class ConsultantRequest(BaseModel):
    question: str = "What should we improve next?"
    business_id: Optional[str] = None
    business_name: Optional[str] = None


class ConsultantResponse(BaseModel):
    business_id: str
    business_name: str
    question: str
    context_analyzed: Dict[str, int]
    recommendations: List[str]
    rationale: List[str]
    next_actions: List[str]


class OnboardingRequest(BaseModel):
    company_name: str = Field(..., min_length=1)
    business_type: str = "company"
    description: str = ""
    revenue_goal: int = 250000
    knowledge_documents: List[Dict[str, Any]] = Field(default_factory=list)
    project_path: Optional[str] = None


class OnboardingResult(BaseModel):
    business_id: str
    company_name: str
    steps: List[Dict[str, Any]]
    dashboard_ready: bool
    estimated_minutes: int


class DemoWorkspaceRequest(BaseModel):
    template: str = Field(..., min_length=1)


class DemoWorkspaceResult(BaseModel):
    template: str
    business_id: str
    business_name: str
    created: bool
    counts: Dict[str, int]
    insights: List[str]


class DemoLibrary(BaseModel):
    templates: List[Dict[str, Any]]


class PresentationMode(BaseModel):
    business_id: str
    company_overview: Dict[str, Any]
    business_health: BusinessHealthDashboard
    executive_summary: Dict[str, Any]
    current_challenges: List[str]
    ai_recommendations: List[str]
    execution_plan: List[Dict[str, Any]]
    kpis: List[str]
    roadmap: Dict[str, Any]


class CommercialReadinessReport(BaseModel):
    generated_at: datetime
    overall_score: int
    engineering_score: int
    product_score: int
    commercial_score: int
    pilot_readiness_score: int
    checks: List[Dict[str, Any]]
    critical_bugs: List[str]
    high_priority_bugs: List[str]
    medium_priority_bugs: List[str]
    remaining_backlog: List[str]
    technical_debt: List[str]

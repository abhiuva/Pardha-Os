from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProspectRequest(BaseModel):
    query: str = Field(..., min_length=1)
    target_count: int = Field(default=50, ge=1, le=500)
    industries: List[str] = Field(default_factory=lambda: ["eCommerce"])


class ICPProfile(BaseModel):
    industry: str
    ideal_customer_profile: str
    pain_points: List[str] = Field(default_factory=list)
    buying_signals: List[str] = Field(default_factory=list)
    priority_ranking: List[Dict[str, Any]] = Field(default_factory=list)


class ProspectResearchResult(BaseModel):
    company: str
    industry: str
    website: str
    size: str
    country: str
    linkedin: Optional[str] = None
    decision_makers: List[Dict[str, Any]] = Field(default_factory=list)
    business_summary: str
    ai_opportunity_score: int
    sales_priority: str


class ProspectGenerationResult(BaseModel):
    query: str
    target_count: int
    industry: str
    generated_count: int
    prospects: List[ProspectResearchResult]
    icp: ICPProfile


class SalesSummary(BaseModel):
    prospects: int
    leads: int
    pipeline_value: int
    upcoming_demos: int
    warm_leads: int
    high_priority_opportunities: int
    revenue_forecast: int
    pipeline_health: str
    next_actions: List[str] = Field(default_factory=list)


class SalesLeadDetail(BaseModel):
    lead_id: str
    company: str
    industry: str
    website: Optional[str] = None
    contact_name: Optional[str] = None
    contact_role: Optional[str] = None
    contact_email: Optional[str] = None
    title: str
    status: str
    pipeline_stage: str
    ai_opportunity_score: int
    sales_priority: str
    outreach_email: Optional[str] = None
    outreach_linkedin: Optional[str] = None
    follow_up_email: Optional[str] = None
    meeting_request: Optional[str] = None
    proposal_request: Optional[str] = None
    demo_invitation: Optional[str] = None
    next_action: Optional[str] = None
    qualification_score: Optional[int] = None
    qualification_status: Optional[str] = None
    qualification_recommendation: Optional[str] = None
    created_at: Optional[str] = None


class SalesOutreachPackage(BaseModel):
    lead_id: str
    company: str
    contact_name: Optional[str] = None
    cold_email: str
    linkedin_message: str
    follow_up_email: str
    meeting_request: str
    proposal_request: str
    demo_invitation: str
    research_source: str
    decision_maker_source: str


class LeadQualificationRequest(BaseModel):
    business_type: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    stage: str = Field(..., min_length=1)
    budget: int = Field(default=0, ge=0)
    timeline: str = Field(..., min_length=1)
    requirement: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)


class LeadQualificationResult(BaseModel):
    qualification_id: str
    lead_id: str
    business_type: str
    location: str
    stage: str
    budget: int
    timeline: str
    requirement: str
    source: str
    score: int
    qualification_status: str
    missing_fields: List[str] = Field(default_factory=list)
    scoring_factors: Dict[str, Any] = Field(default_factory=dict)
    recommendation: str
    hubspot_event_payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DemoScheduleRequest(BaseModel):
    scheduled_at: Optional[datetime] = None
    meeting_url: Optional[str] = None
    owner: str = "Founder"


class DemoScheduleResult(BaseModel):
    lead_id: str
    company: str
    status: str
    pipeline_stage: str
    scheduled_at: Optional[datetime]
    calendar_invite_ics: str
    next_action: str


class StageUpdateRequest(BaseModel):
    status: str


class StageUpdateResult(BaseModel):
    lead_id: str
    company: str
    status: str
    pipeline_stage: str
    next_action: str


class SalesPipelineResponse(BaseModel):
    stages: List[Dict[str, Any]]
    total_value: int
    conversion_funnel: List[Dict[str, Any]] = Field(default_factory=list)


class DemoScheduleResponse(BaseModel):
    upcoming_demos: List[Dict[str, Any]]


class CalendarAvailabilityResponse(BaseModel):
    mode: str
    timezone: str
    slots: List[Dict[str, Any]]


class DemoBookingRequest(BaseModel):
    requested_slot: Optional[datetime] = None
    meeting_url: Optional[str] = None
    owner: str = "Founder"
    notes: str = ""


class DemoBookingStatusRequest(BaseModel):
    status: str
    scheduled_at: Optional[datetime] = None
    meeting_url: Optional[str] = None
    notes: str = ""


class DemoBookingRecord(BaseModel):
    booking_id: str
    business_id: str
    lead_id: str
    company: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    status: str
    requested_slot: Optional[datetime]
    scheduled_at: Optional[datetime]
    meeting_url: Optional[str]
    owner: str
    calendar_mode: str
    hubspot_event_payload: Dict[str, Any] = Field(default_factory=dict)
    notes: str
    created_at: datetime
    updated_at: datetime


class PostDemoDraftRequest(BaseModel):
    demo_summary: str = Field(..., min_length=1)
    pain_points: List[str] = Field(default_factory=list)
    decision_makers: List[str] = Field(default_factory=list)
    next_action: str = "Schedule proposal review"
    commercial_cta: str = "Approve the DP360 Commerce pilot proposal"
    created_by: str = "Sales Executive"


class PostDemoDraftRecord(BaseModel):
    draft_id: str
    business_id: str
    booking_id: str
    lead_id: str
    deal_id: Optional[str]
    company: str
    contact_name: Optional[str]
    contact_email: Optional[str]
    demo_summary: str
    pain_points: List[str]
    dp360_fit: str
    next_action: str
    commercial_cta: str
    follow_up_email: str
    proposal_draft: str
    approval_status: str
    external_send_blocked: bool
    hubspot_event_payload: Dict[str, Any] = Field(default_factory=dict)
    reasoning_provider: str
    reasoning_model: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class SalesDashboard(BaseModel):
    summary: SalesSummary
    leads: List[SalesLeadDetail]
    pipeline: SalesPipelineResponse
    demos: DemoScheduleResponse
    daily_activities: List[Dict[str, Any]]

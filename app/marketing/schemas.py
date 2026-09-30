from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CampaignRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    industry: str = "Cloud Kitchens"
    duration_days: int = Field(default=30, ge=7, le=120)
    budget: int = Field(default=25000, ge=0)
    channels: List[str] = Field(
        default_factory=lambda: ["LinkedIn", "Google Ads", "Email Campaigns", "Website Content", "SEO", "Webinars"]
    )


class CampaignDetail(BaseModel):
    campaign_id: str
    name: str
    objective: str
    audience: Dict[str, Any]
    channels: List[str]
    budget: int
    goals: List[str]
    kpis: List[str]
    status: str
    start_date: datetime
    end_date: datetime
    campaign_plan: Dict[str, Any]


class ContentAsset(BaseModel):
    content_id: str
    campaign_id: str
    content_type: str
    channel: str
    title: str
    body: str
    call_to_action: str
    status: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CalendarItem(BaseModel):
    calendar_item_id: str
    campaign_id: str
    title: str
    channel: str
    content_type: str
    scheduled_for: datetime
    status: str


class AnalyticsRow(BaseModel):
    campaign_id: str
    campaign_name: str
    channel: str
    impressions: int
    clicks: int
    ctr: float
    conversions: int
    leads: int
    spend: int
    cpl: float
    roas: float
    pipeline_contribution: int


class MarketingSummary(BaseModel):
    active_campaigns: int
    content_assets: int
    upcoming_campaigns: int
    impressions: int
    clicks: int
    ctr: float
    conversions: int
    leads: int
    spend: int
    cpl: float
    roas: float
    pipeline_contribution: int
    best_performing_content: List[str] = Field(default_factory=list)
    lead_sources: List[Dict[str, Any]] = Field(default_factory=list)
    budget_usage: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)


class CampaignGenerationResult(BaseModel):
    campaign: CampaignDetail
    content_calendar: List[CalendarItem]
    content_assets: List[ContentAsset]
    analytics: List[AnalyticsRow]
    summary: MarketingSummary


class MarketingDashboard(BaseModel):
    summary: MarketingSummary
    active_campaigns: List[CampaignDetail]
    performance: List[AnalyticsRow]
    lead_sources: List[Dict[str, Any]]
    content_pipeline: List[ContentAsset]
    upcoming_campaigns: List[CalendarItem]
    recommendations: List[str]


class MarketingKPIResponse(BaseModel):
    business_id: str
    mode: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    spend: int
    impressions: int
    clicks: int
    ctr: float
    cpc: float
    leads: int
    qualified_leads: int
    demos_booked: int
    proposals: int
    won_deals: int
    pipeline_value: int
    revenue_won: int
    cac: float
    roas: float
    funnel: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime


class CampaignRecommendation(BaseModel):
    campaign_id: Optional[str] = None
    campaign_name: str
    health: str
    action: str
    reason: str
    confidence: int
    approval_required: bool
    auto_execute: bool = False


class CampaignHealthRow(BaseModel):
    campaign_id: Optional[str] = None
    campaign_name: str
    source: str
    spend: int
    impressions: int
    clicks: int
    ctr: float
    cpc: float
    leads: int
    qualified_leads: int
    demos_booked: int
    lead_cost: float
    demo_conversion: float
    lead_quality: float
    health: str
    recommendation: CampaignRecommendation


class MarketingHealthResponse(BaseModel):
    business_id: str
    generated_at: datetime
    rows: List[CampaignHealthRow]
    recommendations: List[CampaignRecommendation]
    policy: Dict[str, Any] = Field(default_factory=dict)


class MetaConnectorConfigRequest(BaseModel):
    business_id: Optional[str] = None
    ad_account_id: Optional[str] = None
    instagram_account_id: Optional[str] = None
    page_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=lambda: ["ads_read", "read_insights", "pages_read_engagement", "instagram_basic"])
    configuration: Dict[str, Any] = Field(default_factory=dict)
    secret_reference: Optional[str] = None


class MetaConnectorStatus(BaseModel):
    business_id: str
    status: str
    authentication_status: str
    ad_account_id: Optional[str] = None
    instagram_account_id: Optional[str] = None
    page_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    environment_valid: bool
    missing_environment: List[str] = Field(default_factory=list)
    last_checked_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    message: str


class MetaCampaignInsightRow(BaseModel):
    insight_id: str
    business_id: str
    campaign_id: Optional[str] = None
    external_campaign_id: str
    campaign_name: str
    source: str
    channel: str
    spend: float
    impressions: int
    reach: int
    clicks: int
    ctr: float
    cpc: float
    leads: int
    sync_status: str
    error: Optional[str] = None
    captured_at: datetime
    updated_at: datetime


class MetaIngestionResult(BaseModel):
    business_id: str
    mode: str
    sync_status: str
    rows_ingested: int
    status: MetaConnectorStatus
    insights: List[MetaCampaignInsightRow]
    message: str


class MetaAdActionRequest(BaseModel):
    business_id: Optional[str] = None
    action: str = Field(default="campaign.create", min_length=3)
    campaign_name: str = Field(..., min_length=2)
    budget: int = Field(default=0, ge=0)
    audience: Dict[str, Any] = Field(default_factory=dict)
    creative: Dict[str, Any] = Field(default_factory=dict)
    expected_goal: str = Field(..., min_length=2)
    requested_by: str = "Marketing Executive"


class MetaApprovalDecisionRequest(BaseModel):
    decided_by: str = "Founder"
    comment: Optional[str] = None


class MetaAdApprovalRecord(BaseModel):
    approval_id: str
    business_id: str
    action: str
    campaign_name: str
    budget: int
    audience: Dict[str, Any]
    creative: Dict[str, Any]
    expected_goal: str
    status: str
    approval_required: bool
    external_write_blocked: bool
    external_write_attempted: bool
    requested_by: str
    decided_by: Optional[str]
    decision_comment: Optional[str]
    audit_event_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    decided_at: Optional[datetime]

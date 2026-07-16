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

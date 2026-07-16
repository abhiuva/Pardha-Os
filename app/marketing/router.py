from fastapi import APIRouter

from app.marketing.schemas import (
    AnalyticsRow,
    CampaignDetail,
    CampaignGenerationResult,
    CampaignRequest,
    ContentAsset,
    MarketingDashboard,
    MarketingSummary,
)
from app.marketing.service import build_campaign, get_analytics, get_dashboard, get_summary, list_campaigns, list_content

router = APIRouter(prefix="/marketing", tags=["marketing"])


@router.post("/campaign", response_model=CampaignGenerationResult)
def create_marketing_campaign(request: CampaignRequest):
    return build_campaign(request)


@router.get("/campaigns", response_model=list[CampaignDetail])
def get_marketing_campaigns():
    return list_campaigns()


@router.get("/analytics", response_model=list[AnalyticsRow])
def get_marketing_analytics():
    return get_analytics()


@router.get("/content", response_model=list[ContentAsset])
def get_marketing_content():
    return list_content()


@router.get("/summary", response_model=MarketingSummary)
def get_marketing_summary():
    return get_summary()


@router.get("/dashboard", response_model=MarketingDashboard)
def get_marketing_dashboard():
    return get_dashboard()

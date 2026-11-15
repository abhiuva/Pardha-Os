from fastapi import APIRouter

from app.marketing.schemas import (
    AnalyticsRow,
    CampaignDetail,
    CampaignGenerationResult,
    CampaignRequest,
    ContentAsset,
    MarketingHealthResponse,
    MarketingDashboard,
    MarketingKPIResponse,
    MarketingSummary,
    MetaAdActionRequest,
    MetaAdApprovalRecord,
    MetaApprovalDecisionRequest,
    MetaCampaignInsightRow,
    MetaConnectorConfigRequest,
    MetaConnectorStatus,
    MetaIngestionResult,
)
from app.marketing.service import (
    build_campaign,
    configure_meta,
    decide_meta_ad_approval,
    get_analytics,
    get_campaign_health,
    get_dashboard,
    get_kpis,
    get_summary,
    ingest_meta_campaign_insights,
    list_meta_ad_approvals,
    list_campaigns,
    list_content,
    list_meta_campaign_insights,
    meta_status,
    request_meta_ad_action,
)

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


@router.get("/kpis", response_model=MarketingKPIResponse)
def get_marketing_kpis(
    business_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    campaign: str | None = None,
    source: str | None = None,
):
    from datetime import datetime

    return get_kpis(
        business_id=business_id,
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        campaign=campaign,
        source=source,
    )


@router.get("/campaign-health", response_model=MarketingHealthResponse)
def get_marketing_campaign_health(business_id: str | None = None):
    return get_campaign_health(business_id=business_id)


@router.post("/meta/config", response_model=MetaConnectorStatus)
def configure_meta_connector(request: MetaConnectorConfigRequest):
    return configure_meta(request)


@router.get("/meta/status", response_model=MetaConnectorStatus)
def get_meta_connector_status(business_id: str | None = None):
    return meta_status(business_id=business_id)


@router.post("/meta/ingest", response_model=MetaIngestionResult)
def ingest_meta_insights(business_id: str | None = None):
    return ingest_meta_campaign_insights(business_id=business_id)


@router.get("/meta/insights", response_model=list[MetaCampaignInsightRow])
def get_meta_insights(business_id: str | None = None):
    return list_meta_campaign_insights(business_id=business_id)


@router.post("/meta/actions", response_model=MetaAdApprovalRecord)
def request_meta_action(request: MetaAdActionRequest):
    return request_meta_ad_action(request)


@router.get("/meta/approvals", response_model=list[MetaAdApprovalRecord])
def get_meta_approvals(business_id: str | None = None, status: str | None = None):
    return list_meta_ad_approvals(business_id=business_id, status=status)


@router.post("/meta/approvals/{approval_id}/approve", response_model=MetaAdApprovalRecord)
def approve_meta_action(approval_id: str, decision: MetaApprovalDecisionRequest):
    return decide_meta_ad_approval(approval_id, decision, "approved")


@router.post("/meta/approvals/{approval_id}/reject", response_model=MetaAdApprovalRecord)
def reject_meta_action(approval_id: str, decision: MetaApprovalDecisionRequest):
    return decide_meta_ad_approval(approval_id, decision, "rejected")

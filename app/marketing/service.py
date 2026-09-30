from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func

from app.business.context import BusinessContextManager
from app.business.service import get_business_by_name
from app.db import SessionLocal
from app.db.models import Event as EventModel
from app.db.models import MarketingAnalytics as MarketingAnalyticsModel
from app.db.models import MarketingCalendarItem as MarketingCalendarItemModel
from app.db.models import MarketingCampaign as MarketingCampaignModel
from app.db.models import MarketingContent as MarketingContentModel
from app.db.models import MetaAdApproval as MetaAdApprovalModel
from app.db.models import MetaCampaignInsight as MetaCampaignInsightModel
from app.db.models import MetaConnectorConfig as MetaConnectorConfigModel
from app.db.models import SalesDeal as SalesDealModel
from app.db.models import SalesDemoBooking as SalesDemoBookingModel
from app.db.models import SalesLead as SalesLeadModel
from app.db.models import SalesLeadQualification as SalesLeadQualificationModel
from app.enterprise.schemas import AuditEventCreate
from app.enterprise.service import record_audit
from app.marketing.schemas import (
    AnalyticsRow,
    CalendarItem,
    CampaignDetail,
    CampaignGenerationResult,
    CampaignRequest,
    ContentAsset,
    CampaignHealthRow,
    CampaignRecommendation,
    MarketingDashboard,
    MarketingHealthResponse,
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
from app.settings import get_settings


SUPPORTED_CHANNELS = ["LinkedIn", "Google Ads", "Meta Ads", "Email Campaigns", "Website Content", "SEO", "Webinars"]
META_REQUIRED_ENV = ["META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID"]
META_WRITE_ACTIONS = {"campaign.create", "campaign.update", "campaign.pause", "campaign.resume", "campaign.scale", "ad.publish", "ad.pause"}


def _dp360_business_id() -> str:
    business = get_business_by_name("DP360")
    return business.business_id if business is not None else BusinessContextManager.get_active_business().business_id


def _normalize_topic(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    if "cloud" in text and "kitchen" in text:
        return "Cloud Kitchens"
    if "ecommerce" in text or "e commerce" in text:
        return "eCommerce"
    if "restaurant" in text:
        return "Restaurant Chains"
    return value.strip().title() or "Cloud Kitchens"


def build_campaign(request: CampaignRequest) -> CampaignGenerationResult:
    business_id = _dp360_business_id()
    industry = _normalize_topic(request.industry or request.prompt)
    channels = [channel for channel in request.channels if channel in SUPPORTED_CHANNELS] or SUPPORTED_CHANNELS
    now = datetime.now(timezone.utc).replace(microsecond=0)
    end = now + timedelta(days=request.duration_days)
    campaign_name = f"DP360 {industry} Demand Generation"
    objective = f"Launch a {request.duration_days}-day campaign that positions DP360 as the AI operating system for {industry.lower()}."
    audience = {
        "segment": industry,
        "personas": ["Founder", "Head of Operations", "Growth Lead", "Revenue Leader"],
        "pain_points": _pain_points(industry),
        "buying_triggers": ["expansion", "delivery complexity", "manual reporting", "retention pressure"],
    }
    goals = ["Create inbound demand", "Book qualified demos", "Educate operators", "Convert engaged accounts into sales pipeline"]
    kpis = ["impressions", "clicks", "CTR", "conversions", "leads", "CPL", "ROAS", "pipeline contribution"]
    plan = {
        "positioning": f"DP360 gives {industry.lower()} leaders one command center for strategy, execution, and customer operations.",
        "offer": "AI Business Operating System demo",
        "funnel": ["awareness content", "problem education", "demo landing page", "email nurture", "webinar conversion"],
        "channels": channels,
        "budget_split": _budget_split(channels, request.budget),
    }

    with SessionLocal() as session:
        campaign = (
            session.query(MarketingCampaignModel)
            .filter(MarketingCampaignModel.business_id == business_id, func.lower(MarketingCampaignModel.name) == campaign_name.lower())
            .one_or_none()
        )
        if campaign is None:
            campaign = MarketingCampaignModel(
                campaign_id=str(uuid4()),
                business_id=business_id,
                name=campaign_name,
                objective=objective,
                audience=audience,
                channels=channels,
                budget=request.budget,
                goals=goals,
                kpis=kpis,
                status="active",
                start_date=now,
                end_date=end,
                campaign_plan=plan,
                created_at=now,
                updated_at=now,
            )
            session.add(campaign)
            session.flush()
        else:
            campaign.objective = objective
            campaign.audience = audience
            campaign.channels = channels
            campaign.budget = request.budget
            campaign.goals = goals
            campaign.kpis = kpis
            campaign.status = "active"
            campaign.start_date = now
            campaign.end_date = end
            campaign.campaign_plan = plan
            campaign.updated_at = now
            session.query(MarketingContentModel).filter(MarketingContentModel.campaign_id == campaign.campaign_id).delete()
            session.query(MarketingCalendarItemModel).filter(MarketingCalendarItemModel.campaign_id == campaign.campaign_id).delete()
            session.query(MarketingAnalyticsModel).filter(MarketingAnalyticsModel.campaign_id == campaign.campaign_id).delete()
            session.flush()

        for item in _content_assets(campaign.campaign_id, business_id, industry, now):
            session.add(item)
        for item in _calendar_items(campaign.campaign_id, business_id, industry, now, request.duration_days):
            session.add(item)
        for item in _analytics_rows(campaign.campaign_id, business_id, channels, request.budget, now):
            session.add(item)
        session.commit()

    return CampaignGenerationResult(
        campaign=get_campaign(campaign_name=campaign_name),
        content_calendar=list_calendar(campaign_name=campaign_name),
        content_assets=list_content(campaign_name=campaign_name),
        analytics=get_analytics(campaign_name=campaign_name),
        summary=get_summary(),
    )


def list_campaigns() -> list[CampaignDetail]:
    with SessionLocal() as session:
        campaigns = session.query(MarketingCampaignModel).order_by(MarketingCampaignModel.created_at.desc()).all()
        return [_campaign_detail(item) for item in campaigns]


def get_campaign(campaign_name: str | None = None) -> CampaignDetail:
    with SessionLocal() as session:
        query = session.query(MarketingCampaignModel)
        if campaign_name:
            query = query.filter(func.lower(MarketingCampaignModel.name) == campaign_name.lower())
        campaign = query.order_by(MarketingCampaignModel.created_at.desc()).first()
        if campaign is None:
            raise ValueError("Campaign not found.")
        return _campaign_detail(campaign)


def list_content(campaign_name: str | None = None) -> list[ContentAsset]:
    with SessionLocal() as session:
        query = session.query(MarketingContentModel, MarketingCampaignModel).join(
            MarketingCampaignModel, MarketingContentModel.campaign_id == MarketingCampaignModel.campaign_id
        )
        if campaign_name:
            query = query.filter(func.lower(MarketingCampaignModel.name) == campaign_name.lower())
        rows = query.order_by(MarketingContentModel.created_at.desc()).all()
        return [_content_detail(content) for content, _campaign in rows]


def list_calendar(campaign_name: str | None = None) -> list[CalendarItem]:
    with SessionLocal() as session:
        query = session.query(MarketingCalendarItemModel, MarketingCampaignModel).join(
            MarketingCampaignModel, MarketingCalendarItemModel.campaign_id == MarketingCampaignModel.campaign_id
        )
        if campaign_name:
            query = query.filter(func.lower(MarketingCampaignModel.name) == campaign_name.lower())
        rows = query.order_by(MarketingCalendarItemModel.scheduled_for.asc()).all()
        return [_calendar_detail(item) for item, _campaign in rows]


def get_analytics(campaign_name: str | None = None) -> list[AnalyticsRow]:
    with SessionLocal() as session:
        query = session.query(MarketingAnalyticsModel, MarketingCampaignModel).join(
            MarketingCampaignModel, MarketingAnalyticsModel.campaign_id == MarketingCampaignModel.campaign_id
        )
        if campaign_name:
            query = query.filter(func.lower(MarketingCampaignModel.name) == campaign_name.lower())
        rows = query.order_by(MarketingAnalyticsModel.captured_at.desc()).all()
        return [_analytics_detail(row, campaign) for row, campaign in rows]


def get_summary() -> MarketingSummary:
    campaigns = list_campaigns()
    content = list_content()
    calendar = list_calendar()
    analytics = get_analytics()
    impressions = sum(item.impressions for item in analytics)
    clicks = sum(item.clicks for item in analytics)
    conversions = sum(item.conversions for item in analytics)
    leads = sum(item.leads for item in analytics)
    spend = sum(item.spend for item in analytics)
    pipeline = sum(item.pipeline_contribution for item in analytics)
    active = [item for item in campaigns if item.status == "active"]
    lead_sources = [
        {"channel": item.channel, "leads": item.leads, "cpl": item.cpl}
        for item in sorted(analytics, key=lambda row: row.leads, reverse=True)[:5]
    ]
    return MarketingSummary(
        active_campaigns=len(active),
        content_assets=len(content),
        upcoming_campaigns=len([item for item in calendar if _as_aware(item.scheduled_for) >= datetime.now(timezone.utc)]),
        impressions=impressions,
        clicks=clicks,
        ctr=round(clicks / impressions * 100, 2) if impressions else 0,
        conversions=conversions,
        leads=leads,
        spend=spend,
        cpl=round(spend / leads, 2) if leads else 0,
        roas=round(pipeline / spend, 2) if spend else 0,
        pipeline_contribution=pipeline,
        best_performing_content=[item.title for item in content[:5]],
        lead_sources=lead_sources,
        budget_usage={"allocated": sum(item.budget for item in campaigns), "spent": spend, "remaining": max(0, sum(item.budget for item in campaigns) - spend)},
        recommendations=[
            "Prioritize LinkedIn founder/operator posts for proof-led awareness.",
            "Route Google Ads clicks to the cloud kitchen landing page.",
            "Use webinar registrations as high-intent sales handoffs.",
            "Refresh email sequence after the first seven days of engagement data.",
        ],
        next_actions=[
            "Publish week one LinkedIn posts",
            "Launch Google Ads problem-aware ad group",
            "Send email sequence to cloud kitchen operators",
            "Review CPL and conversion rate after 72 hours",
        ],
    )


def get_dashboard() -> MarketingDashboard:
    summary = get_summary()
    return MarketingDashboard(
        summary=summary,
        active_campaigns=[item for item in list_campaigns() if item.status == "active"][:10],
        performance=get_analytics()[:12],
        lead_sources=summary.lead_sources,
        content_pipeline=list_content()[:12],
        upcoming_campaigns=list_calendar()[:30],
        recommendations=summary.recommendations,
    )


def get_kpis(
    business_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    campaign: str | None = None,
    source: str | None = None,
) -> MarketingKPIResponse:
    resolved_id = business_id or _dp360_business_id()
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        analytics_query = (
            session.query(MarketingAnalyticsModel, MarketingCampaignModel)
            .join(MarketingCampaignModel, MarketingAnalyticsModel.campaign_id == MarketingCampaignModel.campaign_id)
            .filter(MarketingAnalyticsModel.business_id == resolved_id)
        )
        if start_date:
            analytics_query = analytics_query.filter(MarketingAnalyticsModel.captured_at >= _as_aware(start_date))
        if end_date:
            analytics_query = analytics_query.filter(MarketingAnalyticsModel.captured_at <= _as_aware(end_date))
        if campaign:
            analytics_query = analytics_query.filter(func.lower(MarketingCampaignModel.name).contains(campaign.lower()))
        if source:
            analytics_query = analytics_query.filter(func.lower(MarketingAnalyticsModel.channel) == source.lower())
        analytics_rows = analytics_query.all()
        if not analytics_rows and get_settings().connector_mode == "mock":
            analytics_rows = _mock_kpi_analytics(session, resolved_id, now)
        analytics_items = [
            {
                "campaign_id": campaign_row.campaign_id,
                "campaign_name": campaign_row.name,
                "channel": row.channel,
                "spend": row.spend,
                "impressions": row.impressions,
                "clicks": row.clicks,
                "leads": row.leads,
            }
            for row, campaign_row in analytics_rows
        ]
        if source:
            analytics_items = [row for row in analytics_items if row["channel"].lower() == source.lower()]

        leads_query = session.query(SalesLeadModel).filter(SalesLeadModel.business_id == resolved_id)
        leads = leads_query.all()
        lead_ids = [lead.lead_id for lead in leads]
        qualified = (
            session.query(SalesLeadQualificationModel)
            .filter(SalesLeadQualificationModel.lead_id.in_(lead_ids), SalesLeadQualificationModel.qualification_status == "qualified")
            .count()
            if lead_ids else 0
        )
        demos_booked = session.query(SalesDemoBookingModel).filter(SalesDemoBookingModel.business_id == resolved_id, SalesDemoBookingModel.status.in_(["booked", "attended", "completed"])).count()
        proposals = len([lead for lead in leads if lead.status in {"proposal_sent", "negotiation", "won"}])
        won_deals = len([lead for lead in leads if lead.status == "won"])
        deals = session.query(SalesDealModel).filter(SalesDealModel.business_id == resolved_id).all()

    spend = sum(row["spend"] for row in analytics_items)
    impressions = sum(row["impressions"] for row in analytics_items)
    clicks = sum(row["clicks"] for row in analytics_items)
    marketing_leads = sum(row["leads"] for row in analytics_items)
    leads_count = max(marketing_leads, len(leads))
    pipeline_value = sum(deal.amount for deal in deals)
    revenue_won = sum(deal.amount for deal in deals if deal.pipeline_stage == "won")
    sources = _source_rows(analytics_items)
    return MarketingKPIResponse(
        business_id=resolved_id,
        mode="mock_contract" if get_settings().connector_mode == "mock" else "live_or_local",
        filters={"start_date": start_date.isoformat() if start_date else None, "end_date": end_date.isoformat() if end_date else None, "campaign": campaign, "source": source},
        spend=spend,
        impressions=impressions,
        clicks=clicks,
        ctr=_pct(clicks, impressions),
        cpc=_ratio(spend, clicks),
        leads=leads_count,
        qualified_leads=qualified,
        demos_booked=demos_booked,
        proposals=proposals,
        won_deals=won_deals,
        pipeline_value=pipeline_value,
        revenue_won=revenue_won,
        cac=_ratio(spend, max(won_deals, 0)),
        roas=_ratio(revenue_won or pipeline_value, spend),
        funnel=[
            {"stage": "impressions", "count": impressions},
            {"stage": "clicks", "count": clicks},
            {"stage": "leads", "count": leads_count},
            {"stage": "qualified_leads", "count": qualified},
            {"stage": "demos_booked", "count": demos_booked},
            {"stage": "proposals", "count": proposals},
            {"stage": "won_deals", "count": won_deals},
        ],
        sources=sources,
        generated_at=now,
    )


def get_campaign_health(business_id: str | None = None) -> MarketingHealthResponse:
    resolved_id = business_id or _dp360_business_id()
    kpis = get_kpis(business_id=resolved_id)
    analytics = get_analytics()
    grouped: dict[str, dict[str, Any]] = {}
    for row in analytics:
        key = row.campaign_id or row.campaign_name
        item = grouped.setdefault(key, {"campaign_id": row.campaign_id, "campaign_name": row.campaign_name, "source": row.channel, "spend": 0, "impressions": 0, "clicks": 0, "leads": 0})
        item["spend"] += row.spend
        item["impressions"] += row.impressions
        item["clicks"] += row.clicks
        item["leads"] += row.leads
    if not grouped:
        grouped["mock_dp360_campaign"] = {"campaign_id": None, "campaign_name": "DP360 Mock Demand Campaign", "source": "mock", "spend": kpis.spend, "impressions": kpis.impressions, "clicks": kpis.clicks, "leads": kpis.leads}

    rows: list[CampaignHealthRow] = []
    for item in grouped.values():
        lead_cost = _ratio(item["spend"], item["leads"])
        demo_conversion = _pct(kpis.demos_booked, max(item["leads"], 1))
        lead_quality = _pct(kpis.qualified_leads, max(kpis.leads, 1))
        ctr = _pct(item["clicks"], item["impressions"])
        cpc = _ratio(item["spend"], item["clicks"])
        health, action, reason, confidence = _campaign_health_decision(ctr, cpc, lead_cost, demo_conversion, lead_quality, item["leads"])
        recommendation = CampaignRecommendation(
            campaign_id=item["campaign_id"],
            campaign_name=item["campaign_name"],
            health=health,
            action=action,
            reason=reason,
            confidence=confidence,
            approval_required=action in {"pause", "scale", "change_creative", "change_audience"},
            auto_execute=False,
        )
        rows.append(
            CampaignHealthRow(
                campaign_id=item["campaign_id"],
                campaign_name=item["campaign_name"],
                source=item["source"],
                spend=item["spend"],
                impressions=item["impressions"],
                clicks=item["clicks"],
                ctr=ctr,
                cpc=cpc,
                leads=item["leads"],
                qualified_leads=kpis.qualified_leads,
                demos_booked=kpis.demos_booked,
                lead_cost=lead_cost,
                demo_conversion=demo_conversion,
                lead_quality=lead_quality,
                health=health,
                recommendation=recommendation,
            )
        )
    return MarketingHealthResponse(
        business_id=resolved_id,
        generated_at=datetime.now(timezone.utc),
        rows=rows,
        recommendations=[row.recommendation for row in rows],
        policy={"external_writes": "blocked_without_founder_approval", "recommendations_auto_execute": False},
    )


def configure_meta(request: MetaConnectorConfigRequest) -> MetaConnectorStatus:
    business_id = request.business_id or _dp360_business_id()
    env_valid, missing = _meta_env_status()
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = (
            session.query(MetaConnectorConfigModel)
            .filter(MetaConnectorConfigModel.business_id == business_id)
            .one_or_none()
        )
        if row is None:
            row = MetaConnectorConfigModel(config_id=str(uuid4()), business_id=business_id, created_at=now, updated_at=now)
            session.add(row)
        row.ad_account_id = request.ad_account_id or row.ad_account_id
        row.instagram_account_id = request.instagram_account_id or row.instagram_account_id
        row.page_id = request.page_id or row.page_id
        row.status = "configured" if env_valid else "mock_available" if get_settings().connector_mode == "mock" else "missing_environment"
        row.authentication_status = "configured" if env_valid else "mock_contract" if get_settings().connector_mode == "mock" else "missing_credentials"
        row.scopes = request.scopes
        row.configuration = request.configuration
        row.secret_reference = request.secret_reference or row.secret_reference
        row.last_checked_at = now
        row.updated_at = now
        session.commit()
    return meta_status(business_id)


def meta_status(business_id: str | None = None) -> MetaConnectorStatus:
    resolved_id = business_id or _dp360_business_id()
    env_valid, missing = _meta_env_status()
    settings = get_settings()
    with SessionLocal() as session:
        row = (
            session.query(MetaConnectorConfigModel)
            .filter(MetaConnectorConfigModel.business_id == resolved_id)
            .one_or_none()
        )
    auth = "configured" if env_valid else "mock_contract" if settings.connector_mode == "mock" else "missing_credentials"
    status = "configured" if env_valid else "mock_available" if settings.connector_mode == "mock" else "missing_environment"
    return MetaConnectorStatus(
        business_id=resolved_id,
        status=row.status if row else status,
        authentication_status=row.authentication_status if row else auth,
        ad_account_id=(row.ad_account_id if row else None) or (get_settings().connector_mode == "live" and _env("META_AD_ACCOUNT_ID")) or None,
        instagram_account_id=(row.instagram_account_id if row else None) or (get_settings().connector_mode == "live" and _env("META_INSTAGRAM_ACCOUNT_ID")) or None,
        page_id=row.page_id if row else None,
        scopes=row.scopes if row else ["ads_read", "read_insights", "pages_read_engagement", "instagram_basic"],
        environment_valid=env_valid,
        missing_environment=missing,
        last_checked_at=row.last_checked_at if row else None,
        last_sync_at=row.last_sync_at if row else None,
        message="Meta live reads are configured." if env_valid else "Meta live credentials are missing; mock campaign insight ingestion is available." if settings.connector_mode == "mock" else "Meta credentials are missing.",
    )


def ingest_meta_campaign_insights(business_id: str | None = None) -> MetaIngestionResult:
    resolved_id = business_id or _dp360_business_id()
    settings = get_settings()
    status = meta_status(resolved_id)
    now = datetime.now(timezone.utc)
    if settings.connector_mode != "mock" and not status.environment_valid:
        _record_meta_failure(resolved_id, "missing_credentials", "Missing Meta environment credentials.", now)
        return MetaIngestionResult(
            business_id=resolved_id,
            mode=settings.connector_mode,
            sync_status="failed",
            rows_ingested=0,
            status=meta_status(resolved_id),
            insights=list_meta_campaign_insights(resolved_id),
            message="Meta ingestion failed because required credentials are missing.",
        )

    rows = _mock_meta_rows(now) if settings.connector_mode == "mock" or not status.environment_valid else _live_ready_rows(now)
    with SessionLocal() as session:
        campaign = _ensure_meta_campaign(session, resolved_id, now)
        session.query(MetaCampaignInsightModel).filter(MetaCampaignInsightModel.business_id == resolved_id).delete()
        session.query(MarketingAnalyticsModel).filter(
            MarketingAnalyticsModel.business_id == resolved_id,
            MarketingAnalyticsModel.campaign_id == campaign.campaign_id,
            MarketingAnalyticsModel.channel.in_(["Meta Ads", "Instagram"]),
        ).delete(synchronize_session=False)
        for row in rows:
            insight = MetaCampaignInsightModel(
                insight_id=str(uuid4()),
                business_id=resolved_id,
                campaign_id=campaign.campaign_id,
                external_campaign_id=row["external_campaign_id"],
                campaign_name=row["campaign_name"],
                source=row["source"],
                channel=row["channel"],
                spend=int(round(row["spend"] * 100)),
                impressions=row["impressions"],
                reach=row["reach"],
                clicks=row["clicks"],
                ctr=int(round(row["ctr"] * 100)),
                cpc=int(round(row["cpc"] * 100)),
                leads=row["leads"],
                sync_status="mock" if settings.connector_mode == "mock" or not status.environment_valid else "synced",
                raw_payload=row,
                captured_at=now,
                created_at=now,
                updated_at=now,
            )
            session.add(insight)
            session.add(
                MarketingAnalyticsModel(
                    analytics_id=str(uuid4()),
                    campaign_id=campaign.campaign_id,
                    business_id=resolved_id,
                    channel=row["channel"],
                    impressions=row["impressions"],
                    clicks=row["clicks"],
                    conversions=max(0, row["leads"]),
                    leads=row["leads"],
                    spend=int(round(row["spend"])),
                    revenue=row["leads"] * 18000,
                    captured_at=now,
                )
            )
        config = (
            session.query(MetaConnectorConfigModel)
            .filter(MetaConnectorConfigModel.business_id == resolved_id)
            .one_or_none()
        )
        if config is None:
            config = MetaConnectorConfigModel(config_id=str(uuid4()), business_id=resolved_id, created_at=now, updated_at=now)
            session.add(config)
        config.status = "mock_available" if settings.connector_mode == "mock" or not status.environment_valid else "configured"
        config.authentication_status = "mock_contract" if settings.connector_mode == "mock" or not status.environment_valid else "configured"
        config.last_checked_at = now
        config.last_sync_at = now
        config.updated_at = now
        session.add(EventModel(event_id=str(uuid4()), business_id=resolved_id, source_agent="meta-connector", target_agent="marketing", event_type="META_INSIGHTS_INGESTED", payload={"rows": len(rows), "mode": settings.connector_mode}, timestamp=now))
        session.commit()
    insights = list_meta_campaign_insights(resolved_id)
    return MetaIngestionResult(
        business_id=resolved_id,
        mode="mock_contract" if settings.connector_mode == "mock" or not status.environment_valid else "live",
        sync_status="mock" if settings.connector_mode == "mock" or not status.environment_valid else "synced",
        rows_ingested=len(insights),
        status=meta_status(resolved_id),
        insights=insights,
        message=f"Meta campaign insights ingested in {'mock contract' if settings.connector_mode == 'mock' or not status.environment_valid else 'live'} mode.",
    )


def list_meta_campaign_insights(business_id: str | None = None) -> list[MetaCampaignInsightRow]:
    resolved_id = business_id or _dp360_business_id()
    with SessionLocal() as session:
        rows = (
            session.query(MetaCampaignInsightModel)
            .filter(MetaCampaignInsightModel.business_id == resolved_id)
            .order_by(MetaCampaignInsightModel.captured_at.desc(), MetaCampaignInsightModel.campaign_name.asc())
            .all()
        )
        return [_meta_insight_detail(row) for row in rows]


def request_meta_ad_action(request: MetaAdActionRequest) -> MetaAdApprovalRecord:
    if request.action not in META_WRITE_ACTIONS:
        raise ValueError(f"Meta action is not approval-gated or supported: {request.action}")
    business_id = request.business_id or _dp360_business_id()
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = MetaAdApprovalModel(
            approval_id=str(uuid4()),
            business_id=business_id,
            action=request.action,
            campaign_name=request.campaign_name.strip(),
            budget=request.budget,
            audience=request.audience,
            creative=request.creative,
            expected_goal=request.expected_goal.strip(),
            status="pending",
            approval_required=1,
            external_write_blocked=1,
            external_write_attempted=0,
            requested_by=request.requested_by.strip() or "Marketing Executive",
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.add(
            EventModel(
                event_id=str(uuid4()),
                business_id=business_id,
                source_agent="marketing",
                target_agent="founder",
                event_type="META_AD_APPROVAL_REQUIRED",
                payload={
                    "approval_id": row.approval_id,
                    "action": row.action,
                    "campaign_name": row.campaign_name,
                    "budget": row.budget,
                    "external_write_blocked": True,
                },
                timestamp=now,
            )
        )
        session.commit()
        session.refresh(row)
        approval = _meta_ad_approval_detail(row)
    audit = record_audit(
        AuditEventCreate(
            business_id=business_id,
            action="meta.ad_approval.requested",
            resource_type="meta_ad_approval",
            resource_id=approval.approval_id,
            approval_id=approval.approval_id,
            outcome="blocked_pending_approval",
            metadata={
                "meta_action": approval.action,
                "campaign_name": approval.campaign_name,
                "budget": approval.budget,
                "external_write_attempted": False,
            },
        )
    )
    with SessionLocal() as session:
        row = session.get(MetaAdApprovalModel, approval.approval_id)
        if row:
            row.audit_event_id = audit.audit_id
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(row)
            return _meta_ad_approval_detail(row)
    return approval


def list_meta_ad_approvals(business_id: str | None = None, status: str | None = None) -> list[MetaAdApprovalRecord]:
    resolved_id = business_id or _dp360_business_id()
    with SessionLocal() as session:
        query = session.query(MetaAdApprovalModel).filter(MetaAdApprovalModel.business_id == resolved_id)
        if status:
            query = query.filter(MetaAdApprovalModel.status == status)
        rows = query.order_by(MetaAdApprovalModel.created_at.desc()).all()
        return [_meta_ad_approval_detail(row) for row in rows]


def decide_meta_ad_approval(approval_id: str, decision: MetaApprovalDecisionRequest, status: str) -> MetaAdApprovalRecord:
    if status not in {"approved", "rejected"}:
        raise ValueError("Meta approval decision must be approved or rejected.")
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = session.get(MetaAdApprovalModel, approval_id)
        if row is None:
            raise ValueError("Meta approval not found.")
        if row.status != "pending":
            raise ValueError(f"Meta approval is already {row.status}.")
        row.status = status
        row.decided_by = decision.decided_by.strip() or "Founder"
        row.decision_comment = decision.comment
        row.decided_at = now
        row.updated_at = now
        row.external_write_attempted = 0
        row.external_write_blocked = 0 if status == "approved" else 1
        session.add(
            EventModel(
                event_id=str(uuid4()),
                business_id=row.business_id,
                source_agent="founder",
                target_agent="marketing",
                event_type="META_AD_APPROVAL_APPROVED" if status == "approved" else "META_AD_APPROVAL_REJECTED",
                payload={
                    "approval_id": row.approval_id,
                    "action": row.action,
                    "campaign_name": row.campaign_name,
                    "external_write_attempted": False,
                },
                timestamp=now,
            )
        )
        session.commit()
        session.refresh(row)
        approval = _meta_ad_approval_detail(row)
    audit = record_audit(
        AuditEventCreate(
            business_id=approval.business_id,
            action=f"meta.ad_approval.{status}",
            resource_type="meta_ad_approval",
            resource_id=approval.approval_id,
            approval_id=approval.approval_id,
            outcome=status,
            metadata={
                "meta_action": approval.action,
                "campaign_name": approval.campaign_name,
                "budget": approval.budget,
                "external_write_attempted": False,
                "decision_comment": approval.decision_comment,
            },
        )
    )
    with SessionLocal() as session:
        row = session.get(MetaAdApprovalModel, approval.approval_id)
        if row:
            row.audit_event_id = audit.audit_id
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(row)
            return _meta_ad_approval_detail(row)
    return approval


def _env(name: str) -> str:
    import os

    return os.getenv(name, "")


def _meta_env_status() -> tuple[bool, list[str]]:
    missing = [name for name in META_REQUIRED_ENV if not _env(name)]
    return not missing, missing


def _mock_meta_rows(now: datetime) -> list[dict[str, Any]]:
    return [
        {
            "external_campaign_id": "meta_dp360_cloud_kitchens_awareness",
            "campaign_name": "DP360 Cloud Kitchens Awareness",
            "source": "meta",
            "channel": "Meta Ads",
            "spend": 1240.0,
            "impressions": 48200,
            "reach": 37100,
            "clicks": 1568,
            "ctr": 3.25,
            "cpc": 0.79,
            "leads": 42,
            "captured_at": now.isoformat(),
        },
        {
            "external_campaign_id": "instagram_dp360_operator_reels",
            "campaign_name": "DP360 Operator Reels",
            "source": "instagram",
            "channel": "Instagram",
            "spend": 680.0,
            "impressions": 29400,
            "reach": 22600,
            "clicks": 912,
            "ctr": 3.1,
            "cpc": 0.75,
            "leads": 25,
            "captured_at": now.isoformat(),
        },
        {
            "external_campaign_id": "meta_dp360_retention_demo",
            "campaign_name": "DP360 Retention Demo Retargeting",
            "source": "meta",
            "channel": "Meta Ads",
            "spend": 510.0,
            "impressions": 11800,
            "reach": 8200,
            "clicks": 578,
            "ctr": 4.9,
            "cpc": 0.88,
            "leads": 31,
            "captured_at": now.isoformat(),
        },
    ]


def _live_ready_rows(now: datetime) -> list[dict[str, Any]]:
    return [
        {
            "external_campaign_id": "live_ready_empty",
            "campaign_name": "Meta live connector ready",
            "source": "meta",
            "channel": "Meta Ads",
            "spend": 0.0,
            "impressions": 0,
            "reach": 0,
            "clicks": 0,
            "ctr": 0.0,
            "cpc": 0.0,
            "leads": 0,
            "captured_at": now.isoformat(),
        }
    ]


def _ensure_meta_campaign(session, business_id: str, now: datetime) -> MarketingCampaignModel:
    campaign = (
        session.query(MarketingCampaignModel)
        .filter(MarketingCampaignModel.business_id == business_id, func.lower(MarketingCampaignModel.name) == "dp360 meta instagram demand cockpit")
        .one_or_none()
    )
    if campaign is not None:
        campaign.updated_at = now
        return campaign
    campaign = MarketingCampaignModel(
        campaign_id=str(uuid4()),
        business_id=business_id,
        name="DP360 Meta Instagram Demand Cockpit",
        objective="Track Meta and Instagram campaign performance for DP360 demand generation.",
        audience={"segment": "eCommerce and cloud kitchen operators", "source": "meta_instagram_ingestion"},
        channels=["Meta Ads", "Instagram"],
        budget=2500,
        goals=["Measure paid social demand", "Track leads", "Feed marketing cockpit"],
        kpis=["spend", "impressions", "reach", "clicks", "CTR", "CPC", "leads"],
        status="active",
        start_date=now,
        end_date=now + timedelta(days=30),
        campaign_plan={"source": "meta_connector", "mode": get_settings().connector_mode},
        created_at=now,
        updated_at=now,
    )
    session.add(campaign)
    session.flush()
    return campaign


def _record_meta_failure(business_id: str, sync_status: str, error: str, now: datetime) -> None:
    with SessionLocal() as session:
        row = MetaCampaignInsightModel(
            insight_id=str(uuid4()),
            business_id=business_id,
            campaign_id=None,
            external_campaign_id="meta_ingestion_failed",
            campaign_name="Meta ingestion failed",
            source="meta",
            channel="Meta Ads",
            spend=0,
            impressions=0,
            reach=0,
            clicks=0,
            ctr=0,
            cpc=0,
            leads=0,
            sync_status=sync_status,
            error=error,
            raw_payload={"error": error},
            captured_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.add(EventModel(event_id=str(uuid4()), business_id=business_id, source_agent="meta-connector", target_agent="marketing", event_type="META_INSIGHTS_FAILED", payload={"status": sync_status, "error": error}, timestamp=now))
        session.commit()


def _meta_insight_detail(row: MetaCampaignInsightModel) -> MetaCampaignInsightRow:
    return MetaCampaignInsightRow(
        insight_id=row.insight_id,
        business_id=row.business_id,
        campaign_id=row.campaign_id,
        external_campaign_id=row.external_campaign_id,
        campaign_name=row.campaign_name,
        source=row.source,
        channel=row.channel,
        spend=round(row.spend / 100, 2),
        impressions=row.impressions,
        reach=row.reach,
        clicks=row.clicks,
        ctr=round(row.ctr / 100, 2),
        cpc=round(row.cpc / 100, 2),
        leads=row.leads,
        sync_status=row.sync_status,
        error=row.error,
        captured_at=row.captured_at,
        updated_at=row.updated_at,
    )


def _meta_ad_approval_detail(row: MetaAdApprovalModel) -> MetaAdApprovalRecord:
    return MetaAdApprovalRecord(
        approval_id=row.approval_id,
        business_id=row.business_id,
        action=row.action,
        campaign_name=row.campaign_name,
        budget=row.budget,
        audience=row.audience or {},
        creative=row.creative or {},
        expected_goal=row.expected_goal,
        status=row.status,
        approval_required=bool(row.approval_required),
        external_write_blocked=bool(row.external_write_blocked),
        external_write_attempted=bool(row.external_write_attempted),
        requested_by=row.requested_by,
        decided_by=row.decided_by,
        decision_comment=row.decision_comment,
        audit_event_id=row.audit_event_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        decided_at=row.decided_at,
    )


def _ratio(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) / float(denominator), 2) if denominator else 0.0


def _pct(numerator: int | float, denominator: int | float) -> float:
    return round(float(numerator) / float(denominator) * 100, 2) if denominator else 0.0


def _source_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = grouped.setdefault(row["channel"], {"source": row["channel"], "spend": 0, "impressions": 0, "clicks": 0, "leads": 0})
        item["spend"] += row["spend"]
        item["impressions"] += row["impressions"]
        item["clicks"] += row["clicks"]
        item["leads"] += row["leads"]
    return [
        {
            **item,
            "ctr": _pct(item["clicks"], item["impressions"]),
            "cpc": _ratio(item["spend"], item["clicks"]),
            "cpl": _ratio(item["spend"], item["leads"]),
        }
        for item in sorted(grouped.values(), key=lambda value: value["leads"], reverse=True)
    ]


def _mock_kpi_analytics(session, business_id: str, now: datetime) -> list[tuple[MarketingAnalyticsModel, MarketingCampaignModel]]:
    campaign = (
        session.query(MarketingCampaignModel)
        .filter(MarketingCampaignModel.business_id == business_id, func.lower(MarketingCampaignModel.name) == "dp360 mock marketing cockpit")
        .one_or_none()
    )
    if campaign is None:
        campaign = MarketingCampaignModel(
            campaign_id=str(uuid4()),
            business_id=business_id,
            name="DP360 Mock Marketing Cockpit",
            objective="Provide stable DP360 cockpit fixture data for local demos.",
            audience={"segment": "eCommerce and cloud kitchen founders"},
            channels=["Meta Ads", "LinkedIn", "Google Ads"],
            budget=12500,
            goals=["Generate qualified demos", "Track lead quality", "Support proposal conversion"],
            kpis=["spend", "impressions", "clicks", "leads", "qualified_leads", "demos", "CAC", "ROAS"],
            status="active",
            start_date=now - timedelta(days=7),
            end_date=now + timedelta(days=23),
            campaign_plan={"source": "mock_fixture", "approval_policy": "no_external_writes"},
            created_at=now,
            updated_at=now,
        )
        session.add(campaign)
        session.flush()
    rows = session.query(MarketingAnalyticsModel).filter(MarketingAnalyticsModel.business_id == business_id, MarketingAnalyticsModel.campaign_id == campaign.campaign_id).all()
    if not rows:
        for channel, impressions, clicks, leads, spend, revenue in [
            ("Meta Ads", 48200, 1568, 42, 1240, 180000),
            ("LinkedIn", 18600, 512, 18, 1900, 125000),
            ("Google Ads", 22400, 868, 24, 2100, 160000),
        ]:
            row = MarketingAnalyticsModel(
                analytics_id=str(uuid4()),
                campaign_id=campaign.campaign_id,
                business_id=business_id,
                channel=channel,
                impressions=impressions,
                clicks=clicks,
                conversions=leads,
                leads=leads,
                spend=spend,
                revenue=revenue,
                captured_at=now,
            )
            session.add(row)
            rows.append(row)
        session.commit()
    return [(row, campaign) for row in rows]


def _campaign_health_decision(ctr: float, cpc: float, lead_cost: float, demo_conversion: float, lead_quality: float, leads: int) -> tuple[str, str, str, int]:
    if leads == 0:
        return "red", "change_audience", "No leads are being generated; audience or offer requires review.", 88
    if ctr < 1.0:
        return "red", "change_creative", f"CTR is {ctr}%, below the 1.0% minimum for DP360 demand tests.", 86
    if lead_cost > 250 or cpc > 8:
        return "yellow", "review_lead_quality", f"Acquisition cost is elevated: CPC ${cpc}, lead cost ${lead_cost}.", 78
    if demo_conversion < 10:
        return "yellow", "change_audience", f"Demo conversion is {demo_conversion}%; improve audience qualification before scaling.", 80
    if lead_quality >= 40 and demo_conversion >= 15 and ctr >= 2:
        return "green", "scale", f"Healthy campaign: {ctr}% CTR, {lead_quality}% lead quality, {demo_conversion}% demo conversion.", 84
    return "yellow", "review_lead_quality", "Campaign is generating demand but needs lead quality review before spend changes.", 72


def _pain_points(industry: str) -> list[str]:
    if industry == "Cloud Kitchens":
        return ["delivery SLA visibility", "multi-brand reporting", "kitchen throughput", "repeat order retention"]
    return ["fragmented customer data", "manual campaign execution", "weak executive visibility", "slow follow-up"]


def _budget_split(channels: list[str], budget: int) -> dict[str, int]:
    if not channels:
        return {}
    base = budget // len(channels)
    split = {channel: base for channel in channels}
    if "Google Ads" in split:
        split["Google Ads"] += budget - sum(split.values())
    return split


def _as_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _content_assets(campaign_id: str, business_id: str, industry: str, now: datetime) -> list[MarketingContentModel]:
    specs = [
        ("linkedin_post", "LinkedIn", "Why cloud kitchens need an operating system", "Most cloud kitchens do not have a strategy problem. They have an execution visibility problem. DP360 turns customer, kitchen, and growth signals into CEO/PM/CTO action.", "Book the DP360 cloud kitchen demo"),
        ("linkedin_post", "LinkedIn", "The hidden cost of manual kitchen reporting", "Manual reports delay decisions. DP360 keeps operators aligned on priorities, risks, and tasks from one dashboard.", "See the operating dashboard"),
        ("blog", "SEO", "How AI operating systems help cloud kitchens scale", f"A practical guide for {industry.lower()} teams using DP360 to connect demand, operations, and execution.", "Read the DP360 playbook"),
        ("case_study", "Website Content", "Cloud kitchen expansion command center", "A narrative customer story showing how a multi-brand kitchen operator improved visibility, retention, and execution speed.", "Request the case study"),
        ("landing_page", "Website Content", "DP360 for Cloud Kitchens", "Hero: Run every kitchen, campaign, and objective from one AI business operating system. Sections: pain, workflow, executive briefs, tasks, proof, demo CTA.", "Schedule a 20-minute walkthrough"),
        ("email_1", "Email Campaigns", "Cloud kitchen growth is becoming an execution problem", "Introduce the problem and invite operators to compare their current reporting cycle with DP360.", "Reply for the checklist"),
        ("email_2", "Email Campaigns", "What your kitchen dashboard should tell you daily", "Explain CEO, PM, CTO, and Operations briefs for cloud kitchen teams.", "Open the sample brief"),
        ("email_3", "Email Campaigns", "Turn retention goals into execution tasks", "Show the objective-to-task workflow and request a demo.", "Book the demo"),
        ("google_ad", "Google Ads", "Cloud Kitchen Operating System", "Headline: Cloud Kitchen AI Dashboard. Description: Turn strategy, operations and retention goals into execution tasks with DP360.", "Start your DP360 demo"),
        ("meta_ad", "Meta Ads", "Scale kitchens without spreadsheet chaos", "Creative concept for operators: one dashboard for objectives, campaigns, execution, and risks.", "See DP360 in action"),
        ("webinar", "Webinars", "From kitchen chaos to execution rhythm", "Live demo agenda covering customer context, executive briefs, campaigns, and task generation.", "Reserve a webinar seat"),
        ("customer_story", "Website Content", "The 3-school lunch launch story", "Story-led asset connecting EatOnTime launch lessons to DP360 operating discipline.", "Explore the launch workflow"),
    ]
    return [
        MarketingContentModel(
            content_id=str(uuid4()),
            campaign_id=campaign_id,
            business_id=business_id,
            content_type=content_type,
            channel=channel,
            title=title,
            body=body,
            call_to_action=cta,
            status="draft" if content_type not in {"landing_page", "google_ad"} else "ready",
            metadata_json={"source": "deterministic_marketing_executive", "industry": industry},
            created_at=now + timedelta(minutes=index),
        )
        for index, (content_type, channel, title, body, cta) in enumerate(specs)
    ]


def _calendar_items(campaign_id: str, business_id: str, industry: str, now: datetime, duration_days: int) -> list[MarketingCalendarItemModel]:
    channels = ["LinkedIn", "Email Campaigns", "Google Ads", "SEO", "Website Content", "LinkedIn", "Webinars"]
    items: list[MarketingCalendarItemModel] = []
    for day in range(duration_days):
        channel = channels[day % len(channels)]
        content_type = "campaign_touchpoint" if channel != "Email Campaigns" else "email"
        items.append(
            MarketingCalendarItemModel(
                calendar_item_id=str(uuid4()),
                campaign_id=campaign_id,
                business_id=business_id,
                title=f"Day {day + 1}: {industry} {channel} activation",
                channel=channel,
                content_type=content_type,
                scheduled_for=now + timedelta(days=day),
                status="planned",
                created_at=now,
            )
        )
    planning = [("weekly", 7), ("weekly", 14), ("weekly", 21), ("weekly", 28), ("monthly", 30), ("quarterly", 90)]
    for label, offset in planning:
        if label == "weekly" and offset > duration_days:
            continue
        items.append(
            MarketingCalendarItemModel(
                calendar_item_id=str(uuid4()),
                campaign_id=campaign_id,
                business_id=business_id,
                title=f"{label.title()} {industry} campaign review",
                channel="Operations",
                content_type=label,
                scheduled_for=now + timedelta(days=offset),
                status="planned",
                created_at=now,
            )
        )
    return items


def _analytics_rows(campaign_id: str, business_id: str, channels: list[str], budget: int, now: datetime) -> list[MarketingAnalyticsModel]:
    split = _budget_split(channels, budget)
    rows: list[MarketingAnalyticsModel] = []
    for index, channel in enumerate(channels):
        spend = split.get(channel, 0)
        impressions = 18000 - index * 1700
        clicks = max(120, int(impressions * (0.038 - index * 0.002)))
        conversions = max(8, clicks // (11 + index))
        leads = max(5, conversions // 2)
        rows.append(
            MarketingAnalyticsModel(
                analytics_id=str(uuid4()),
                campaign_id=campaign_id,
                business_id=business_id,
                channel=channel,
                impressions=impressions,
                clicks=clicks,
                conversions=conversions,
                leads=leads,
                spend=spend,
                revenue=leads * 18000,
                captured_at=now,
            )
        )
    return rows


def _campaign_detail(campaign: MarketingCampaignModel) -> CampaignDetail:
    return CampaignDetail(
        campaign_id=campaign.campaign_id,
        name=campaign.name,
        objective=campaign.objective,
        audience=campaign.audience,
        channels=campaign.channels,
        budget=campaign.budget,
        goals=campaign.goals,
        kpis=campaign.kpis,
        status=campaign.status,
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        campaign_plan=campaign.campaign_plan,
    )


def _content_detail(content: MarketingContentModel) -> ContentAsset:
    return ContentAsset(
        content_id=content.content_id,
        campaign_id=content.campaign_id,
        content_type=content.content_type,
        channel=content.channel,
        title=content.title,
        body=content.body,
        call_to_action=content.call_to_action,
        status=content.status,
        metadata=content.metadata_json,
        created_at=content.created_at,
    )


def _calendar_detail(item: MarketingCalendarItemModel) -> CalendarItem:
    return CalendarItem(
        calendar_item_id=item.calendar_item_id,
        campaign_id=item.campaign_id,
        title=item.title,
        channel=item.channel,
        content_type=item.content_type,
        scheduled_for=item.scheduled_for,
        status=item.status,
    )


def _analytics_detail(item: MarketingAnalyticsModel, campaign: MarketingCampaignModel) -> AnalyticsRow:
    ctr = round(item.clicks / item.impressions * 100, 2) if item.impressions else 0
    cpl = round(item.spend / item.leads, 2) if item.leads else 0
    roas = round(item.revenue / item.spend, 2) if item.spend else 0
    return AnalyticsRow(
        campaign_id=item.campaign_id,
        campaign_name=campaign.name,
        channel=item.channel,
        impressions=item.impressions,
        clicks=item.clicks,
        ctr=ctr,
        conversions=item.conversions,
        leads=item.leads,
        spend=item.spend,
        cpl=cpl,
        roas=roas,
        pipeline_contribution=item.revenue,
    )

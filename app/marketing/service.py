from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func

from app.business.context import BusinessContextManager
from app.business.service import get_business_by_name
from app.db import SessionLocal
from app.db.models import MarketingAnalytics as MarketingAnalyticsModel
from app.db.models import MarketingCalendarItem as MarketingCalendarItemModel
from app.db.models import MarketingCampaign as MarketingCampaignModel
from app.db.models import MarketingContent as MarketingContentModel
from app.marketing.schemas import (
    AnalyticsRow,
    CalendarItem,
    CampaignDetail,
    CampaignGenerationResult,
    CampaignRequest,
    ContentAsset,
    MarketingDashboard,
    MarketingSummary,
)


SUPPORTED_CHANNELS = ["LinkedIn", "Google Ads", "Meta Ads", "Email Campaigns", "Website Content", "SEO", "Webinars"]


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

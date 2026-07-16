from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func

from app.business.context import BusinessContextManager
from app.business.service import get_business_by_name
from app.db import SessionLocal
from app.db.models import SalesActivity as SalesActivityModel
from app.db.models import SalesCompany as SalesCompanyModel
from app.db.models import SalesContact as SalesContactModel
from app.db.models import SalesDeal as SalesDealModel
from app.db.models import SalesLead as SalesLeadModel
from app.sales.schemas import (
    DemoScheduleResult,
    DemoScheduleResponse,
    ICPProfile,
    ProspectGenerationResult,
    ProspectResearchResult,
    SalesOutreachPackage,
    SalesDashboard,
    SalesLeadDetail,
    SalesPipelineResponse,
    SalesSummary,
    StageUpdateResult,
)


INDUSTRY_TEMPLATES = {
    "ecommerce": {
        "label": "eCommerce",
        "icp": "E-commerce operators with omnichannel growth, repeat purchase, and retention challenges.",
        "pain_points": ["Low repeat purchase rate", "Fragmented customer data", "Manual retention campaigns"],
        "buying_signals": ["Hiring growth marketing", "Launching new channels", "Expanding internationally"],
        "roles": ["VP Growth", "Head of eCommerce", "Director of Retention"],
    },
    "cloud kitchens": {
        "label": "Cloud Kitchens",
        "icp": "Cloud kitchen operators scaling delivery, kitchen throughput, and multi-brand operations.",
        "pain_points": ["Kitchen throughput issues", "Delivery exception management", "Poor visibility across brands"],
        "buying_signals": ["Opening new kitchens", "Adding new brands", "Automating dispatch"],
        "roles": ["Head of Operations", "Founder", "Growth Lead"],
    },
    "retail": {
        "label": "Retail",
        "icp": "Retail chains managing store visibility, merchandising, promotions, and loyalty.",
        "pain_points": ["Store-level visibility gaps", "Inventory blind spots", "Weak promotion ROI"],
        "buying_signals": ["Expanding store network", "Rolling out loyalty programs", "Centralizing reports"],
        "roles": ["Retail Operations Director", "Head of CRM", "Commercial Director"],
    },
    "d2c": {
        "label": "D2C",
        "icp": "Direct-to-consumer brands seeking growth, retention, and customer intelligence.",
        "pain_points": ["CAC pressure", "Poor retention analytics", "Manual customer segmentation"],
        "buying_signals": ["New product launch", "Paid media scale-up", "Retention initiative"],
        "roles": ["Founder", "Head of Growth", "Retention Manager"],
    },
    "restaurant chains": {
        "label": "Restaurant Chains",
        "icp": "Restaurant groups needing better operational, customer, and location-level visibility.",
        "pain_points": ["Operational fragmentation", "Low guest retention", "Procurement inconsistency"],
        "buying_signals": ["Opening new locations", "Centralizing reporting", "Improving customer experience"],
        "roles": ["COO", "Marketing Director", "Guest Experience Lead"],
    },
}

PIPELINE_STAGES = [
    "prospecting",
    "demo_requested",
    "demo_scheduled",
    "demo_completed",
    "proposal_sent",
    "negotiation",
    "won",
    "lost",
]


def _dp360_business_id() -> str:
    business = get_business_by_name("DP360")
    return business.business_id if business is not None else BusinessContextManager.get_active_business().business_id


def _normalize_industry(raw: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip()
    compact = normalized.replace(" ", "")
    for key, template in INDUSTRY_TEMPLATES.items():
        if key.replace(" ", "") == compact or template["label"].lower().replace(" ", "") == compact:
            return template["label"]
    return "eCommerce"


def _template(industry: str) -> dict[str, Any]:
    normalized = _normalize_industry(industry).lower()
    for template in INDUSTRY_TEMPLATES.values():
        if template["label"].lower() == normalized:
            return template
    return INDUSTRY_TEMPLATES["ecommerce"]


def generate_icp(industry: str) -> ICPProfile:
    template = _template(industry)
    return ICPProfile(
        industry=template["label"],
        ideal_customer_profile=template["icp"],
        pain_points=template["pain_points"],
        buying_signals=template["buying_signals"],
        priority_ranking=[
            {"rank": 1, "segment": "Mid-market teams with active growth targets", "reason": "Fastest ROI and shorter sales cycles"},
            {"rank": 2, "segment": "Multi-location or multi-brand operators", "reason": "High operational complexity"},
            {"rank": 3, "segment": "Founder-led growth teams", "reason": "Strong urgency and clear owner"},
        ],
    )


def _company_templates(industry: str, target_count: int) -> list[dict[str, Any]]:
    template = _template(industry)
    label = template["label"]
    countries = ["US", "UK", "India", "UAE", "Canada"]
    sizes = ["11-50", "51-200", "201-1000", "1001-5000"]
    prospects: list[dict[str, Any]] = []
    for index in range(target_count):
        number = index + 1
        name = f"{label} Growth Co {number:02d}"
        slug = re.sub(r"[^a-z0-9]+", "", name.lower())
        score = 96 - min(index, 35) + (index % 5)
        priority = "high" if score >= 82 else "medium" if score >= 68 else "low"
        role = template["roles"][index % len(template["roles"])]
        prospects.append(
            {
                "name": name,
                "industry": label,
                "website": f"https://{slug}.example",
                "size": sizes[index % len(sizes)],
                "country": countries[index % len(countries)],
                "linkedin": f"https://www.linkedin.com/company/{slug}",
                "business_summary": f"{name} matches DP360's ICP: {template['icp']} Primary pain: {template['pain_points'][index % len(template['pain_points'])]}.",
                "ai_opportunity_score": max(55, min(98, score)),
                "sales_priority": priority,
                "decision_makers": [
                    {"name": f"Alex Rivera {number:02d}", "role": role, "email": f"alex{number:02d}@{slug}.example"},
                    {"name": f"Jamie Chen {number:02d}", "role": "Operations Lead", "email": f"jamie{number:02d}@{slug}.example"},
                ],
            }
        )
    return prospects


def build_prospect_research(query: str, target_count: int = 50, industries: list[str] | None = None) -> ProspectGenerationResult:
    industry = _normalize_industry((industries or ["eCommerce"])[0])
    business_id = _dp360_business_id()
    icp = generate_icp(industry)
    prospects = _company_templates(industry, target_count)
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        for index, item in enumerate(prospects):
            company = (
                session.query(SalesCompanyModel)
                .filter(SalesCompanyModel.business_id == business_id, func.lower(SalesCompanyModel.name) == item["name"].lower())
                .one_or_none()
            )
            if company is None:
                company = SalesCompanyModel(
                    company_id=str(uuid4()),
                    business_id=business_id,
                    name=item["name"],
                    industry=item["industry"],
                    website=item["website"],
                    company_size=item["size"],
                    country=item["country"],
                    linkedin_url=item["linkedin"],
                    business_summary=item["business_summary"],
                    ai_opportunity_score=item["ai_opportunity_score"],
                    sales_priority=item["sales_priority"],
                    created_at=now,
                )
                session.add(company)
                session.flush()
            else:
                company.industry = item["industry"]
                company.website = item["website"]
                company.company_size = item["size"]
                company.country = item["country"]
                company.linkedin_url = item["linkedin"]
                company.business_summary = item["business_summary"]
                company.ai_opportunity_score = item["ai_opportunity_score"]
                company.sales_priority = item["sales_priority"]
                session.flush()

            contact = session.query(SalesContactModel).filter(SalesContactModel.company_id == company.company_id).first()
            if contact is None:
                maker = item["decision_makers"][0]
                contact = SalesContactModel(
                    contact_id=str(uuid4()),
                    company_id=company.company_id,
                    business_id=business_id,
                    name=maker["name"],
                    role=maker["role"],
                    email=maker["email"],
                    linkedin_url=item["linkedin"],
                    created_at=now,
                )
                session.add(contact)
                session.flush()

            lead = session.query(SalesLeadModel).filter(SalesLeadModel.company_id == company.company_id).one_or_none()
            stage = _stage_for_index(index)
            if lead is None:
                lead = SalesLeadModel(
                    lead_id=str(uuid4()),
                    business_id=business_id,
                    company_id=company.company_id,
                    contact_id=contact.contact_id,
                    title=f"{company.name} DP360 opportunity",
                    status=_lead_status_for_stage(stage),
                    pipeline_stage=stage,
                    ai_opportunity_score=company.ai_opportunity_score,
                    sales_priority=company.sales_priority,
                    outreach_email=_cold_email(company, contact),
                    outreach_linkedin=_linkedin_message(company, contact),
                    next_action=_next_action(stage),
                    demo_requested_at=now if stage in {"demo_requested", "demo_scheduled", "demo_completed", "proposal_sent", "negotiation"} else None,
                    demo_scheduled_at=now + timedelta(days=7 + index % 10) if stage in {"demo_scheduled", "demo_completed", "proposal_sent", "negotiation"} else None,
                    demo_completed_at=now - timedelta(days=index % 5) if stage in {"demo_completed", "proposal_sent", "negotiation"} else None,
                    proposal_sent_at=now if stage in {"proposal_sent", "negotiation"} else None,
                    negotiation_started_at=now if stage == "negotiation" else None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(lead)
                session.flush()
                session.add(
                    SalesDealModel(
                        deal_id=str(uuid4()),
                        business_id=business_id,
                        lead_id=lead.lead_id,
                        pipeline_stage=stage,
                        amount=75000 + (index * 2500),
                        probability=_probability(stage),
                        expected_close_date=now + timedelta(days=30 + index % 45),
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                lead.status = _lead_status_for_stage(stage)
                lead.pipeline_stage = stage
                lead.ai_opportunity_score = company.ai_opportunity_score
                lead.sales_priority = company.sales_priority
                lead.outreach_email = _cold_email(company, contact)
                lead.outreach_linkedin = _linkedin_message(company, contact)
                lead.next_action = _next_action(stage)
                lead.updated_at = now
                deal = session.query(SalesDealModel).filter(SalesDealModel.lead_id == lead.lead_id).first()
                if deal:
                    deal.pipeline_stage = stage
                    deal.probability = _probability(stage)
                    deal.updated_at = now

            _ensure_activity(session, business_id, lead.lead_id, "outreach", f"Send cold email and LinkedIn message to {company.name}", now + timedelta(days=1))
            _ensure_activity(session, business_id, lead.lead_id, "follow_up", f"Follow up with {contact.name} about DP360 demo", now + timedelta(days=3 + index % 5))
        session.commit()

    return ProspectGenerationResult(
        query=query,
        target_count=target_count,
        industry=industry,
        generated_count=len(prospects),
        prospects=[
            ProspectResearchResult(
                company=item["name"],
                industry=item["industry"],
                website=item["website"],
                size=item["size"],
                country=item["country"],
                linkedin=item["linkedin"],
                decision_makers=item["decision_makers"],
                business_summary=item["business_summary"],
                ai_opportunity_score=item["ai_opportunity_score"],
                sales_priority=item["sales_priority"],
            )
            for item in prospects
        ],
        icp=icp,
    )


def _stage_for_index(index: int) -> str:
    if index < 5:
        return "demo_scheduled"
    if index < 10:
        return "demo_requested"
    if index < 16:
        return "proposal_sent"
    if index < 20:
        return "negotiation"
    return "prospecting"


def _lead_status_for_stage(stage: str) -> str:
    return {
        "prospecting": "new",
        "demo_requested": "demo_requested",
        "demo_scheduled": "demo_scheduled",
        "demo_completed": "demo_completed",
        "proposal_sent": "proposal_sent",
        "negotiation": "negotiation",
        "won": "won",
        "lost": "lost",
    }.get(stage, "new")


def _probability(stage: str) -> int:
    return {
        "prospecting": 25,
        "demo_requested": 40,
        "demo_scheduled": 55,
        "demo_completed": 65,
        "proposal_sent": 75,
        "negotiation": 85,
        "won": 100,
        "lost": 0,
    }.get(stage, 25)


def _next_action(stage: str) -> str:
    return {
        "prospecting": "Send personalized outreach and schedule discovery",
        "demo_requested": "Confirm demo time and send agenda",
        "demo_scheduled": "Prepare DP360 demo workspace and reminder",
        "demo_completed": "Send recap and proposal request",
        "proposal_sent": "Follow up on proposal and commercial terms",
        "negotiation": "Align on rollout plan and procurement steps",
    }.get(stage, "Review lead")


def _ensure_activity(session, business_id: str, lead_id: str, activity_type: str, summary: str, due_date: datetime) -> None:
    exists = (
        session.query(SalesActivityModel)
        .filter(SalesActivityModel.lead_id == lead_id, SalesActivityModel.activity_type == activity_type, SalesActivityModel.summary == summary)
        .first()
    )
    if exists is None:
        session.add(
            SalesActivityModel(
                activity_id=str(uuid4()),
                business_id=business_id,
                lead_id=lead_id,
                activity_type=activity_type,
                summary=summary,
                due_date=due_date,
                created_at=datetime.now(timezone.utc),
            )
        )


def _cold_email(company: Any, contact: Any) -> str:
    return (
        f"Subject: Reduce retention blind spots at {company.name}\n\n"
        f"Hi {contact.name},\n\n"
        f"{company.business_summary}\n\n"
        "DP360 helps growth and operations teams unify customer context, find retention opportunities, "
        "and turn them into executive-ready action plans.\n\n"
        "Would you be open to a 20-minute demo next week?"
    )


def _linkedin_message(company: Any, contact: Any) -> str:
    return (
        f"Hi {contact.name}, noticed {company.name} matches a pattern we see in teams trying to improve retention visibility. "
        "Worth comparing notes on how DP360 turns customer signals into CEO/PM/CTO actions?"
    )


def _follow_up_email(company: Any, contact: Any) -> str:
    return f"Hi {contact.name}, following up on DP360 for {company.name}. Would Tuesday or Thursday work for a short walkthrough?"


def _meeting_request(company: Any, contact: Any) -> str:
    return f"Meeting request: DP360 demo for {company.name} with {contact.name}; agenda: retention signals, executive brief, task generation."


def _proposal_request(company: Any, contact: Any) -> str:
    return f"Proposal request for {company.name}: confirm use case, expected users, data sources, and pilot success criteria."


def _demo_invitation(company: Any, contact: Any) -> str:
    return f"Demo invitation for {contact.name}: See DP360 generate executive recommendations and execution tasks from customer context."


def list_leads() -> list[SalesLeadDetail]:
    with SessionLocal() as session:
        rows = (
            session.query(SalesLeadModel, SalesCompanyModel, SalesContactModel)
            .join(SalesCompanyModel, SalesLeadModel.company_id == SalesCompanyModel.company_id)
            .outerjoin(SalesContactModel, SalesLeadModel.contact_id == SalesContactModel.contact_id)
            .order_by(SalesLeadModel.ai_opportunity_score.desc(), SalesLeadModel.created_at.desc())
            .all()
        )
        return [_lead_detail(lead, company, contact) for lead, company, contact in rows]


def _lead_detail(lead: SalesLeadModel, company: SalesCompanyModel, contact: SalesContactModel | None) -> SalesLeadDetail:
    return SalesLeadDetail(
        lead_id=lead.lead_id,
        company=company.name,
        industry=company.industry,
        website=company.website,
        contact_name=contact.name if contact else None,
        contact_role=contact.role if contact else None,
        contact_email=contact.email if contact else None,
        title=lead.title,
        status=lead.status,
        pipeline_stage=lead.pipeline_stage,
        ai_opportunity_score=lead.ai_opportunity_score,
        sales_priority=lead.sales_priority,
        outreach_email=lead.outreach_email,
        outreach_linkedin=lead.outreach_linkedin,
        follow_up_email=_follow_up_email(company, contact) if contact else None,
        meeting_request=_meeting_request(company, contact) if contact else None,
        proposal_request=_proposal_request(company, contact) if contact else None,
        demo_invitation=_demo_invitation(company, contact) if contact else None,
        next_action=lead.next_action,
        created_at=lead.created_at.isoformat() if lead.created_at else None,
    )


def get_pipeline() -> SalesPipelineResponse:
    with SessionLocal() as session:
        deal_rows = session.query(SalesDealModel).all()
        lead_rows = session.query(SalesLeadModel).all()
    stages = [
        {
            "stage": stage,
            "count": sum(1 for item in deal_rows if item.pipeline_stage == stage),
            "value": sum(item.amount for item in deal_rows if item.pipeline_stage == stage),
            "probability": max([item.probability for item in deal_rows if item.pipeline_stage == stage], default=0),
        }
        for stage in PIPELINE_STAGES
    ]
    funnel = [
        {"stage": "prospects", "count": len(lead_rows)},
        {"stage": "demo_requested", "count": sum(1 for item in lead_rows if item.status in {"demo_requested", "demo_scheduled", "demo_completed", "proposal_sent", "negotiation", "won"})},
        {"stage": "proposal_sent", "count": sum(1 for item in lead_rows if item.status in {"proposal_sent", "negotiation", "won"})},
        {"stage": "negotiation", "count": sum(1 for item in lead_rows if item.status in {"negotiation", "won"})},
        {"stage": "won", "count": sum(1 for item in lead_rows if item.status == "won")},
    ]
    return SalesPipelineResponse(stages=stages, total_value=sum(item.amount for item in deal_rows), conversion_funnel=funnel)


def get_demos() -> DemoScheduleResponse:
    with SessionLocal() as session:
        rows = (
            session.query(SalesLeadModel, SalesCompanyModel, SalesContactModel)
            .join(SalesCompanyModel, SalesLeadModel.company_id == SalesCompanyModel.company_id)
            .outerjoin(SalesContactModel, SalesLeadModel.contact_id == SalesContactModel.contact_id)
            .filter(SalesLeadModel.status.in_(["demo_requested", "demo_scheduled", "demo_completed"]))
            .order_by(SalesLeadModel.demo_scheduled_at.asc().nullslast(), SalesLeadModel.created_at.desc())
            .limit(10)
            .all()
        )
    return DemoScheduleResponse(
        upcoming_demos=[
            {
                "lead_id": lead.lead_id,
                "company": company.name,
                "contact": contact.name if contact else None,
                "status": lead.status,
                "scheduled_at": lead.demo_scheduled_at.isoformat() if lead.demo_scheduled_at else None,
                "next_action": lead.next_action,
            }
            for lead, company, contact in rows
        ]
    )


def get_summary() -> SalesSummary:
    with SessionLocal() as session:
        prospects = session.query(SalesCompanyModel).count()
        leads = session.query(SalesLeadModel).count()
        warm = session.query(SalesLeadModel).filter(SalesLeadModel.status != "new").count()
        pipeline_value = sum(item.amount for item in session.query(SalesDealModel).all())
        upcoming = session.query(SalesLeadModel).filter(SalesLeadModel.status.in_(["demo_requested", "demo_scheduled"])).count()
        high_priority = session.query(SalesLeadModel).filter(SalesLeadModel.sales_priority == "high").count()
    health = "healthy" if leads >= 50 and upcoming > 0 else "needs_prospecting"
    return SalesSummary(
        prospects=prospects,
        leads=leads,
        pipeline_value=pipeline_value,
        upcoming_demos=upcoming,
        warm_leads=warm,
        high_priority_opportunities=high_priority,
        revenue_forecast=int(pipeline_value * 0.55),
        pipeline_health=health,
        next_actions=[
            "Send personalized outreach to high-priority prospects",
            "Confirm demo times for requested demos",
            "Prepare DP360 retention demo workspace for scheduled calls",
            "Follow up on proposal-ready opportunities",
        ],
    )


def get_dashboard() -> SalesDashboard:
    with SessionLocal() as session:
        activities = (
            session.query(SalesActivityModel, SalesLeadModel, SalesCompanyModel)
            .join(SalesLeadModel, SalesActivityModel.lead_id == SalesLeadModel.lead_id)
            .join(SalesCompanyModel, SalesLeadModel.company_id == SalesCompanyModel.company_id)
            .order_by(SalesActivityModel.due_date.asc().nullslast(), SalesActivityModel.created_at.desc())
            .limit(12)
            .all()
        )
    return SalesDashboard(
        summary=get_summary(),
        leads=list_leads()[:25],
        pipeline=get_pipeline(),
        demos=get_demos(),
        daily_activities=[
            {
                "activity_id": activity.activity_id,
                "company": company.name,
                "activity_type": activity.activity_type,
                "summary": activity.summary,
                "due_date": activity.due_date.isoformat() if activity.due_date else None,
                "completed": activity.completed_at is not None,
            }
            for activity, _lead, company in activities
        ],
    )


def get_outreach_package(lead_id: str) -> SalesOutreachPackage:
    lead, company, contact = _lead_bundle(lead_id)
    return SalesOutreachPackage(
        lead_id=lead.lead_id,
        company=company.name,
        contact_name=contact.name if contact else None,
        cold_email=lead.outreach_email or _cold_email(company, contact),
        linkedin_message=lead.outreach_linkedin or _linkedin_message(company, contact),
        follow_up_email=_follow_up_email(company, contact),
        meeting_request=_meeting_request(company, contact),
        proposal_request=_proposal_request(company, contact),
        demo_invitation=_demo_invitation(company, contact),
        research_source="deterministic_icp_demo_dataset",
        decision_maker_source="icp_role_template",
    )


def schedule_demo(lead_id: str, scheduled_at: datetime | None = None, meeting_url: str | None = None, owner: str = "Founder") -> DemoScheduleResult:
    scheduled_at = scheduled_at or datetime.now(timezone.utc) + timedelta(days=3)
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        lead = session.get(SalesLeadModel, lead_id)
        if lead is None:
            raise ValueError("Lead not found.")
        company = session.get(SalesCompanyModel, lead.company_id)
        contact = session.get(SalesContactModel, lead.contact_id) if lead.contact_id else None
        lead.status = "demo_scheduled"
        lead.pipeline_stage = "demo_scheduled"
        lead.demo_requested_at = lead.demo_requested_at or now
        lead.demo_scheduled_at = scheduled_at
        lead.next_action = "Run DP360 demo and capture buying criteria"
        lead.updated_at = now
        deal = session.query(SalesDealModel).filter(SalesDealModel.lead_id == lead.lead_id).first()
        if deal:
            deal.pipeline_stage = "demo_scheduled"
            deal.probability = _probability("demo_scheduled")
            deal.updated_at = now
        _ensure_activity(
            session,
            lead.business_id,
            lead.lead_id,
            "demo_scheduled",
            f"Demo scheduled for {company.name if company else 'lead'} with {owner}",
            scheduled_at,
        )
        session.commit()
        company_name = company.name if company else "Unknown company"
        contact_name = contact.name if contact else None
    return DemoScheduleResult(
        lead_id=lead_id,
        company=company_name,
        status="demo_scheduled",
        pipeline_stage="demo_scheduled",
        scheduled_at=scheduled_at,
        calendar_invite_ics=_calendar_invite(company_name, contact_name, scheduled_at, meeting_url),
        next_action="Run DP360 demo and capture buying criteria",
    )


def update_stage(lead_id: str, status: str) -> StageUpdateResult:
    allowed = {"demo_requested", "demo_scheduled", "demo_completed", "proposal_sent", "negotiation", "won", "lost"}
    if status not in allowed:
        raise ValueError(f"Unsupported sales status: {status}")
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        lead = session.get(SalesLeadModel, lead_id)
        if lead is None:
            raise ValueError("Lead not found.")
        company = session.get(SalesCompanyModel, lead.company_id)
        lead.status = status
        lead.pipeline_stage = "prospecting" if status == "demo_requested" else status
        if status == "demo_requested":
            lead.demo_requested_at = lead.demo_requested_at or now
            lead.pipeline_stage = "demo_requested"
        elif status == "demo_completed":
            lead.demo_completed_at = now
        elif status == "proposal_sent":
            lead.proposal_sent_at = now
        elif status == "negotiation":
            lead.negotiation_started_at = now
        elif status == "won":
            lead.won_at = now
        elif status == "lost":
            lead.lost_at = now
        lead.next_action = _next_action(lead.pipeline_stage)
        lead.updated_at = now
        deal = session.query(SalesDealModel).filter(SalesDealModel.lead_id == lead.lead_id).first()
        if deal:
            deal.pipeline_stage = lead.pipeline_stage
            deal.probability = _probability(lead.pipeline_stage)
            deal.updated_at = now
        _ensure_activity(session, lead.business_id, lead.lead_id, "stage_update", f"Sales stage updated to {status}", now)
        session.commit()
        company_name = company.name if company else "Unknown company"
        next_action = lead.next_action or "Review lead"
        pipeline_stage = lead.pipeline_stage
    return StageUpdateResult(
        lead_id=lead_id,
        company=company_name,
        status=status,
        pipeline_stage=pipeline_stage,
        next_action=next_action,
    )


def _lead_bundle(lead_id: str) -> tuple[SalesLeadModel, SalesCompanyModel, SalesContactModel | None]:
    with SessionLocal() as session:
        row = (
            session.query(SalesLeadModel, SalesCompanyModel, SalesContactModel)
            .join(SalesCompanyModel, SalesLeadModel.company_id == SalesCompanyModel.company_id)
            .outerjoin(SalesContactModel, SalesLeadModel.contact_id == SalesContactModel.contact_id)
            .filter(SalesLeadModel.lead_id == lead_id)
            .one_or_none()
        )
        if row is None:
            raise ValueError("Lead not found.")
        lead, company, contact = row
        session.expunge(lead)
        session.expunge(company)
        if contact is not None:
            session.expunge(contact)
        return lead, company, contact


def _calendar_invite(company: str, contact_name: str | None, scheduled_at: datetime, meeting_url: str | None) -> str:
    start = scheduled_at.astimezone(timezone.utc)
    end = start + timedelta(minutes=30)
    uid = f"pardha-demo-{re.sub(r'[^a-z0-9]+', '-', company.lower())}@pardha.local"
    description = f"DP360 demo for {company}. Contact: {contact_name or 'TBD'}. {meeting_url or ''}".strip()
    return "\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Pardha//Sales Executive//EN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:DP360 demo - {company}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )

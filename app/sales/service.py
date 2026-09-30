from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func

from app.business.context import BusinessContextManager
from app.business.service import get_business_by_name
from app.db import SessionLocal
from app.events.bus import EventCreate, publish_event
from app.db.models import SalesActivity as SalesActivityModel
from app.db.models import SalesCompany as SalesCompanyModel
from app.db.models import SalesContact as SalesContactModel
from app.db.models import SalesDemoBooking as SalesDemoBookingModel
from app.db.models import SalesDeal as SalesDealModel
from app.db.models import SalesLead as SalesLeadModel
from app.db.models import SalesLeadQualification as SalesLeadQualificationModel
from app.db.models import SalesPostDemoDraft as SalesPostDemoDraftModel
from app.sales.schemas import (
    CalendarAvailabilityResponse,
    DemoBookingRecord,
    DemoBookingRequest,
    DemoBookingStatusRequest,
    DemoScheduleResult,
    DemoScheduleResponse,
    ICPProfile,
    LeadQualificationRequest,
    LeadQualificationResult,
    PostDemoDraftRecord,
    PostDemoDraftRequest,
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
DEMO_BOOKING_STATUSES = {"requested", "booked", "attended", "no_show", "completed", "follow_up_sent"}
DEMO_STATUS_TO_LEAD_STATUS = {
    "requested": "demo_requested",
    "booked": "demo_scheduled",
    "attended": "demo_completed",
    "completed": "demo_completed",
    "follow_up_sent": "proposal_sent",
}


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
            session.query(SalesLeadModel, SalesCompanyModel, SalesContactModel, SalesLeadQualificationModel)
            .join(SalesCompanyModel, SalesLeadModel.company_id == SalesCompanyModel.company_id)
            .outerjoin(SalesContactModel, SalesLeadModel.contact_id == SalesContactModel.contact_id)
            .outerjoin(SalesLeadQualificationModel, SalesLeadModel.lead_id == SalesLeadQualificationModel.lead_id)
            .order_by(SalesLeadModel.ai_opportunity_score.desc(), SalesLeadModel.created_at.desc())
            .all()
        )
        return [_lead_detail(lead, company, contact, qualification) for lead, company, contact, qualification in rows]


def _lead_detail(lead: SalesLeadModel, company: SalesCompanyModel, contact: SalesContactModel | None, qualification: SalesLeadQualificationModel | None = None) -> SalesLeadDetail:
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
        qualification_score=qualification.score if qualification else None,
        qualification_status=qualification.qualification_status if qualification else None,
        qualification_recommendation=qualification.recommendation if qualification else None,
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
        booking_rows = (
            session.query(SalesDemoBookingModel, SalesCompanyModel, SalesContactModel)
            .join(SalesCompanyModel, SalesDemoBookingModel.company_id == SalesCompanyModel.company_id)
            .outerjoin(SalesContactModel, SalesDemoBookingModel.contact_id == SalesContactModel.contact_id)
            .filter(SalesDemoBookingModel.status.in_(["requested", "booked", "attended", "completed"]))
            .order_by(SalesDemoBookingModel.scheduled_at.asc().nullslast(), SalesDemoBookingModel.created_at.desc())
            .limit(10)
            .all()
        )
        if booking_rows:
            return DemoScheduleResponse(
                upcoming_demos=[
                    {
                        "booking_id": booking.booking_id,
                        "lead_id": booking.lead_id,
                        "company": company.name,
                        "contact": contact.name if contact else None,
                        "status": booking.status,
                        "scheduled_at": booking.scheduled_at.isoformat() if booking.scheduled_at else None,
                        "next_action": _next_demo_booking_action(booking.status),
                    }
                    for booking, company, contact in booking_rows
                ]
            )
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


def calendar_availability(days: int = 5) -> CalendarAvailabilityResponse:
    return CalendarAvailabilityResponse(mode="mock", timezone="UTC", slots=_mock_calendar_slots(days))


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


def qualify_lead(lead_id: str, request: LeadQualificationRequest) -> LeadQualificationResult:
    now = datetime.now(timezone.utc)
    score, status, factors, missing = _score_qualification(request)
    recommendation = _qualification_recommendation(status, score)
    with SessionLocal() as session:
        lead = session.get(SalesLeadModel, lead_id)
        if lead is None:
            raise ValueError("Lead not found.")
        company = session.get(SalesCompanyModel, lead.company_id)
        contact = session.get(SalesContactModel, lead.contact_id) if lead.contact_id else None
        event_payload = {
            "business_id": lead.business_id,
            "lead_id": lead.lead_id,
            "company": company.name if company else "Unknown company",
            "contact_email": contact.email if contact else None,
            "lead_score": score,
            "qualification_status": status,
            "sales_recommendation": recommendation,
            "hubspot_safe_mode": True,
        }
        row = (
            session.query(SalesLeadQualificationModel)
            .filter(SalesLeadQualificationModel.lead_id == lead.lead_id)
            .one_or_none()
        )
        if row is None:
            row = SalesLeadQualificationModel(
                qualification_id=str(uuid4()),
                business_id=lead.business_id,
                lead_id=lead.lead_id,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
        row.business_type = request.business_type.strip()
        row.location = request.location.strip()
        row.stage = request.stage.strip()
        row.budget = request.budget
        row.timeline = request.timeline.strip()
        row.requirement = request.requirement.strip()
        row.source = request.source.strip()
        row.score = score
        row.qualification_status = status
        row.missing_fields = missing
        row.scoring_factors = factors
        row.recommendation = recommendation
        row.hubspot_event_payload = event_payload
        row.updated_at = now
        lead.ai_opportunity_score = max(lead.ai_opportunity_score, score)
        lead.sales_priority = "high" if status == "qualified" else "medium" if status == "nurture" else "low"
        lead.next_action = recommendation
        if status == "qualified" and lead.status == "new":
            lead.status = "demo_requested"
            lead.pipeline_stage = "demo_requested"
            lead.demo_requested_at = lead.demo_requested_at or now
        lead.updated_at = now
        _ensure_activity(session, lead.business_id, lead.lead_id, "qualification", recommendation, now + timedelta(days=1))
        session.commit()
        session.refresh(row)
        result = _qualification_result(row)

    publish_event(EventCreate(
        business_id=result.hubspot_event_payload.get("business_id"),
        source_agent="sales",
        target_agent="hubspot",
        event_type="hubspot.lead_qualification_ready",
        payload=result.hubspot_event_payload,
    ))
    return result


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


def create_demo_booking(lead_id: str, request: DemoBookingRequest) -> DemoBookingRecord:
    requested_slot = request.requested_slot or _parse_slot(_mock_calendar_slots(1)[0]["start"])
    _assert_available_slot(requested_slot)
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        lead = session.get(SalesLeadModel, lead_id)
        if lead is None:
            raise ValueError("Lead not found.")
        qualification = session.query(SalesLeadQualificationModel).filter(SalesLeadQualificationModel.lead_id == lead_id).one_or_none()
        if qualification is None or qualification.qualification_status != "qualified":
            raise ValueError("Lead must be qualified before creating a demo booking.")
        company = session.get(SalesCompanyModel, lead.company_id)
        if company is None:
            raise ValueError("Lead company not found.")
        contact = session.get(SalesContactModel, lead.contact_id) if lead.contact_id else None
        existing = (
            session.query(SalesDemoBookingModel)
            .filter(SalesDemoBookingModel.lead_id == lead_id, SalesDemoBookingModel.status.in_(["requested", "booked", "attended"]))
            .order_by(SalesDemoBookingModel.created_at.desc())
            .first()
        )
        booking = existing or SalesDemoBookingModel(
            booking_id=str(uuid4()),
            business_id=lead.business_id,
            lead_id=lead.lead_id,
            company_id=lead.company_id,
            contact_id=lead.contact_id,
            created_at=now,
        )
        booking.status = "booked" if request.requested_slot else "requested"
        booking.requested_slot = requested_slot
        booking.scheduled_at = requested_slot if request.requested_slot else None
        booking.meeting_url = request.meeting_url
        booking.owner = request.owner.strip() or "Founder"
        booking.calendar_mode = "mock"
        booking.notes = request.notes
        booking.updated_at = now
        lead.status = "demo_scheduled" if booking.status == "booked" else "demo_requested"
        lead.pipeline_stage = lead.status
        lead.demo_requested_at = lead.demo_requested_at or now
        if booking.status == "booked":
            lead.demo_scheduled_at = requested_slot
        lead.next_action = _next_demo_booking_action(booking.status)
        lead.updated_at = now
        deal = session.query(SalesDealModel).filter(SalesDealModel.lead_id == lead.lead_id).first()
        if deal:
            deal.pipeline_stage = lead.pipeline_stage
            deal.probability = _probability(lead.pipeline_stage)
            deal.updated_at = now
        booking.hubspot_event_payload = _demo_hubspot_payload(booking, lead, company, contact)
        session.add(booking)
        _ensure_activity(session, lead.business_id, lead.lead_id, "demo_booking", _next_demo_booking_action(booking.status), requested_slot)
        session.commit()
        session.refresh(booking)
        result = _demo_booking_detail(booking, company, contact)
    if result.status == "booked":
        _emit_hubspot_demo_event(result)
    return result


def list_demo_bookings(business_id: str | None = None) -> list[DemoBookingRecord]:
    resolved_id = business_id or _dp360_business_id()
    with SessionLocal() as session:
        rows = (
            session.query(SalesDemoBookingModel, SalesCompanyModel, SalesContactModel)
            .join(SalesCompanyModel, SalesDemoBookingModel.company_id == SalesCompanyModel.company_id)
            .outerjoin(SalesContactModel, SalesDemoBookingModel.contact_id == SalesContactModel.contact_id)
            .filter(SalesDemoBookingModel.business_id == resolved_id)
            .order_by(SalesDemoBookingModel.created_at.desc())
            .all()
        )
        return [_demo_booking_detail(booking, company, contact) for booking, company, contact in rows]


def update_demo_booking_status(booking_id: str, request: DemoBookingStatusRequest) -> DemoBookingRecord:
    status = request.status.replace("-", "_")
    if status not in DEMO_BOOKING_STATUSES:
        raise ValueError(f"Unsupported demo booking status: {request.status}")
    scheduled_at = request.scheduled_at
    if scheduled_at is not None:
        _assert_available_slot(scheduled_at)
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        booking = session.get(SalesDemoBookingModel, booking_id)
        if booking is None:
            raise ValueError("Demo booking not found.")
        lead = session.get(SalesLeadModel, booking.lead_id)
        company = session.get(SalesCompanyModel, booking.company_id)
        contact = session.get(SalesContactModel, booking.contact_id) if booking.contact_id else None
        if lead is None or company is None:
            raise ValueError("Demo booking lead or company not found.")
        booking.status = status
        booking.notes = request.notes or booking.notes
        booking.updated_at = now
        if request.meeting_url:
            booking.meeting_url = request.meeting_url
        if status == "booked":
            booking.scheduled_at = scheduled_at or booking.scheduled_at or booking.requested_slot
            if booking.scheduled_at is None:
                raise ValueError("Booked demos require an available scheduled_at slot.")
            lead.demo_scheduled_at = booking.scheduled_at
        if status in {"attended", "completed"}:
            lead.demo_completed_at = now
        lead_status = DEMO_STATUS_TO_LEAD_STATUS.get(status)
        if lead_status:
            lead.status = lead_status
            lead.pipeline_stage = lead_status
        lead.next_action = _next_demo_booking_action(status)
        lead.updated_at = now
        deal = session.query(SalesDealModel).filter(SalesDealModel.lead_id == lead.lead_id).first()
        if deal and lead_status:
            deal.pipeline_stage = lead.pipeline_stage
            deal.probability = _probability(lead.pipeline_stage)
            deal.updated_at = now
        booking.hubspot_event_payload = _demo_hubspot_payload(booking, lead, company, contact)
        _ensure_activity(session, lead.business_id, lead.lead_id, f"demo_{status}", _next_demo_booking_action(status), now)
        session.commit()
        session.refresh(booking)
        result = _demo_booking_detail(booking, company, contact)
    if result.status in {"booked", "completed"}:
        _emit_hubspot_demo_event(result)
    return result


def create_post_demo_draft(booking_id: str, request: PostDemoDraftRequest) -> PostDemoDraftRecord:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        booking = session.get(SalesDemoBookingModel, booking_id)
        if booking is None:
            raise ValueError("Demo booking not found.")
        if booking.status != "completed":
            raise ValueError("Post-demo drafts require a completed demo booking.")
        lead = session.get(SalesLeadModel, booking.lead_id)
        company = session.get(SalesCompanyModel, booking.company_id)
        contact = session.get(SalesContactModel, booking.contact_id) if booking.contact_id else None
        if lead is None or company is None:
            raise ValueError("Demo booking lead or company not found.")
        deal = session.query(SalesDealModel).filter(SalesDealModel.lead_id == lead.lead_id).first()
        qualification = session.query(SalesLeadQualificationModel).filter(SalesLeadQualificationModel.lead_id == lead.lead_id).one_or_none()
        pain_points = request.pain_points or _default_demo_pain_points(qualification, request.demo_summary)
        dp360_fit = _dp360_fit(company, pain_points, qualification)
        follow_up = _post_demo_follow_up(company, contact, request, pain_points, dp360_fit)
        proposal = _proposal_draft(company, contact, request, pain_points, dp360_fit)
        draft = SalesPostDemoDraftModel(
            draft_id=str(uuid4()),
            business_id=booking.business_id,
            booking_id=booking.booking_id,
            lead_id=booking.lead_id,
            deal_id=deal.deal_id if deal else None,
            company_id=booking.company_id,
            contact_id=booking.contact_id,
            demo_summary=request.demo_summary.strip(),
            pain_points=pain_points,
            dp360_fit=dp360_fit,
            next_action=request.next_action.strip(),
            commercial_cta=request.commercial_cta.strip(),
            follow_up_email=follow_up,
            proposal_draft=proposal,
            approval_status="pending",
            external_send_blocked=1,
            hubspot_event_payload={},
            reasoning_provider="deterministic",
            reasoning_model="template",
            created_by=request.created_by.strip() or "Sales Executive",
            created_at=now,
            updated_at=now,
        )
        draft.hubspot_event_payload = _post_demo_hubspot_payload(draft, company, contact)
        session.add(draft)
        lead.status = "proposal_sent"
        lead.pipeline_stage = "proposal_sent"
        lead.proposal_sent_at = lead.proposal_sent_at or now
        lead.next_action = "Founder approval required before sending post-demo follow-up."
        lead.updated_at = now
        if deal:
            deal.pipeline_stage = "proposal_sent"
            deal.probability = _probability("proposal_sent")
            deal.updated_at = now
        _ensure_activity(session, lead.business_id, lead.lead_id, "post_demo_draft", "Review and approve post-demo follow-up draft", now + timedelta(days=1))
        session.commit()
        session.refresh(draft)
        result = _post_demo_draft_detail(draft, company, contact)
    publish_event(
        EventCreate(
            business_id=result.business_id,
            source_agent="sales",
            target_agent="hubspot",
            event_type="hubspot.post_demo_activity_ready",
            payload=result.hubspot_event_payload,
        )
    )
    return result


def list_post_demo_drafts(lead_id: str | None = None, booking_id: str | None = None) -> list[PostDemoDraftRecord]:
    with SessionLocal() as session:
        query = (
            session.query(SalesPostDemoDraftModel, SalesCompanyModel, SalesContactModel)
            .join(SalesCompanyModel, SalesPostDemoDraftModel.company_id == SalesCompanyModel.company_id)
            .outerjoin(SalesContactModel, SalesPostDemoDraftModel.contact_id == SalesContactModel.contact_id)
        )
        if lead_id:
            query = query.filter(SalesPostDemoDraftModel.lead_id == lead_id)
        if booking_id:
            query = query.filter(SalesPostDemoDraftModel.booking_id == booking_id)
        rows = query.order_by(SalesPostDemoDraftModel.created_at.desc()).all()
        return [_post_demo_draft_detail(draft, company, contact) for draft, company, contact in rows]


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


def _mock_calendar_slots(days: int = 5) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0)
    slots: list[dict[str, Any]] = []
    cursor = now + timedelta(days=1)
    while len(slots) < max(1, days) * 3:
        if cursor.weekday() < 5:
            for hour in (10, 14, 16):
                start = cursor.replace(hour=hour)
                slots.append(
                    {
                        "slot_id": _slot_key(start),
                        "start": start.isoformat(),
                        "end": (start + timedelta(minutes=30)).isoformat(),
                        "owner": "Founder",
                        "available": True,
                        "source": "mock_calendar_adapter",
                    }
                )
        cursor += timedelta(days=1)
    return slots[: max(1, days) * 3]


def _assert_available_slot(value: datetime) -> None:
    requested = _slot_key(value)
    available = {_slot_key(_parse_slot(slot["start"])) for slot in _mock_calendar_slots(14) if slot["available"]}
    if requested not in available:
        raise ValueError("Requested demo slot is not available in the mock calendar adapter.")


def _parse_slot(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _slot_key(value: datetime) -> str:
    aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return aware.replace(second=0, microsecond=0).isoformat()


def _demo_hubspot_payload(booking: SalesDemoBookingModel, lead: SalesLeadModel, company: SalesCompanyModel, contact: SalesContactModel | None) -> dict[str, Any]:
    return {
        "business_id": booking.business_id,
        "booking_id": booking.booking_id,
        "lead_id": booking.lead_id,
        "company": company.name,
        "contact_email": contact.email if contact else None,
        "demo_status": booking.status,
        "scheduled_at": booking.scheduled_at.isoformat() if booking.scheduled_at else None,
        "meeting_url": booking.meeting_url,
        "hubspot_safe_mode": True,
        "activity_type": "demo_booking",
        "lead_status": lead.status,
    }


def _emit_hubspot_demo_event(booking: DemoBookingRecord) -> None:
    publish_event(
        EventCreate(
            business_id=booking.business_id,
            source_agent="sales",
            target_agent="hubspot",
            event_type="hubspot.demo_activity_ready",
            payload=booking.hubspot_event_payload,
        )
    )


def _next_demo_booking_action(status: str) -> str:
    actions = {
        "requested": "Confirm calendar slot and send DP360 demo agenda",
        "booked": "Prepare DP360 demo workspace and send meeting reminder",
        "attended": "Capture buying criteria and stakeholder notes",
        "no_show": "Send reschedule follow-up and keep lead warm",
        "completed": "Create proposal request and sync HubSpot activity draft",
        "follow_up_sent": "Track reply and move qualified opportunity forward",
    }
    return actions.get(status, "Review demo booking")


def _demo_booking_detail(booking: SalesDemoBookingModel, company: SalesCompanyModel, contact: SalesContactModel | None) -> DemoBookingRecord:
    return DemoBookingRecord(
        booking_id=booking.booking_id,
        business_id=booking.business_id,
        lead_id=booking.lead_id,
        company=company.name,
        contact_name=contact.name if contact else None,
        contact_email=contact.email if contact else None,
        status=booking.status,
        requested_slot=booking.requested_slot,
        scheduled_at=booking.scheduled_at,
        meeting_url=booking.meeting_url,
        owner=booking.owner,
        calendar_mode=booking.calendar_mode,
        hubspot_event_payload=booking.hubspot_event_payload or {},
        notes=booking.notes,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
    )


def _default_demo_pain_points(qualification: SalesLeadQualificationModel | None, demo_summary: str) -> list[str]:
    points: list[str] = []
    if qualification and qualification.requirement:
        points.append(qualification.requirement)
    lower = demo_summary.lower()
    if "retention" in lower or "repeat" in lower:
        points.append("Improve repeat purchase and retention visibility")
    if "manual" in lower or "spreadsheet" in lower:
        points.append("Reduce manual reporting and follow-up coordination")
    if "demo" in lower or "pipeline" in lower:
        points.append("Move qualified demand into a measurable demo-to-proposal pipeline")
    return points[:4] or ["Unify sales, marketing, and execution visibility for DP360 Commerce"]


def _dp360_fit(company: SalesCompanyModel, pain_points: list[str], qualification: SalesLeadQualificationModel | None) -> str:
    context = f"for {qualification.business_type}" if qualification else f"for {company.industry}"
    return (
        f"DP360 fits {company.name} {context} by combining campaign signals, lead qualification, demo booking, "
        f"executive briefs, and execution tasks in one founder-visible operating system. "
        f"The strongest mapped needs are: {', '.join(pain_points[:3])}."
    )


def _post_demo_follow_up(company: SalesCompanyModel, contact: SalesContactModel | None, request: PostDemoDraftRequest, pain_points: list[str], dp360_fit: str) -> str:
    greeting = contact.name.split()[0] if contact and contact.name else "there"
    return "\n".join(
        [
            f"Subject: DP360 next steps for {company.name}",
            "",
            f"Hi {greeting},",
            "",
            f"Thanks for taking the time to review DP360. My notes from the discussion: {request.demo_summary.strip()}",
            "",
            f"The main priorities I captured were: {', '.join(pain_points)}.",
            "",
            dp360_fit,
            "",
            f"Recommended next step: {request.next_action.strip()}.",
            "",
            request.commercial_cta.strip(),
            "",
            "Best,",
            "DP360 Team",
        ]
    )


def _proposal_draft(company: SalesCompanyModel, contact: SalesContactModel | None, request: PostDemoDraftRequest, pain_points: list[str], dp360_fit: str) -> str:
    decision_makers = ", ".join(request.decision_makers) if request.decision_makers else (contact.name if contact else "Founder / Operations owner")
    return "\n".join(
        [
            f"# DP360 Commerce Pilot Proposal - {company.name}",
            "",
            "## Prospect Context",
            request.demo_summary.strip(),
            "",
            "## Pain Points",
            *[f"- {point}" for point in pain_points],
            "",
            "## DP360 Fit",
            dp360_fit,
            "",
            "## Pilot Scope",
            "- Connect sales, marketing, demo booking, and executive operating signals.",
            "- Track leads, qualified demos, proposal movement, CAC, ROAS, and execution follow-up.",
            "- Keep all external sends and spend-affecting actions approval-gated.",
            "",
            "## Decision Makers",
            decision_makers,
            "",
            "## Next Action",
            request.next_action.strip(),
            "",
            "## Commercial CTA",
            request.commercial_cta.strip(),
        ]
    )


def _post_demo_hubspot_payload(draft: SalesPostDemoDraftModel, company: SalesCompanyModel, contact: SalesContactModel | None) -> dict[str, Any]:
    return {
        "business_id": draft.business_id,
        "draft_id": draft.draft_id,
        "booking_id": draft.booking_id,
        "lead_id": draft.lead_id,
        "deal_id": draft.deal_id,
        "company": company.name,
        "contact_email": contact.email if contact else None,
        "activity_type": "post_demo_follow_up_draft",
        "approval_status": draft.approval_status,
        "external_send_blocked": bool(draft.external_send_blocked),
        "hubspot_safe_mode": True,
    }


def _post_demo_draft_detail(draft: SalesPostDemoDraftModel, company: SalesCompanyModel, contact: SalesContactModel | None) -> PostDemoDraftRecord:
    return PostDemoDraftRecord(
        draft_id=draft.draft_id,
        business_id=draft.business_id,
        booking_id=draft.booking_id,
        lead_id=draft.lead_id,
        deal_id=draft.deal_id,
        company=company.name,
        contact_name=contact.name if contact else None,
        contact_email=contact.email if contact else None,
        demo_summary=draft.demo_summary,
        pain_points=draft.pain_points or [],
        dp360_fit=draft.dp360_fit,
        next_action=draft.next_action,
        commercial_cta=draft.commercial_cta,
        follow_up_email=draft.follow_up_email,
        proposal_draft=draft.proposal_draft,
        approval_status=draft.approval_status,
        external_send_blocked=bool(draft.external_send_blocked),
        hubspot_event_payload=draft.hubspot_event_payload or {},
        reasoning_provider=draft.reasoning_provider,
        reasoning_model=draft.reasoning_model,
        created_by=draft.created_by,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def _score_qualification(request: LeadQualificationRequest) -> tuple[int, str, dict[str, Any], list[str]]:
    fields = {
        "business_type": request.business_type.strip(),
        "location": request.location.strip(),
        "stage": request.stage.strip(),
        "timeline": request.timeline.strip(),
        "requirement": request.requirement.strip(),
        "source": request.source.strip(),
    }
    missing = [key for key, value in fields.items() if not value]
    score = 20
    factors: dict[str, Any] = {"base": 20}

    business_type = fields["business_type"].lower()
    if any(term in business_type for term in ("ecommerce", "e-commerce", "d2c", "retail", "cloud kitchen", "restaurant")):
        score += 20
        factors["business_type_fit"] = 20
    else:
        factors["business_type_fit"] = 5
        score += 5

    stage = fields["stage"].lower()
    if any(term in stage for term in ("scaling", "growth", "pilot", "active", "launch")):
        score += 15
        factors["stage_fit"] = 15
    elif any(term in stage for term in ("idea", "research")):
        score += 5
        factors["stage_fit"] = 5
    else:
        score += 10
        factors["stage_fit"] = 10

    budget = request.budget
    if budget >= 50000:
        budget_score = 20
    elif budget >= 15000:
        budget_score = 12
    elif budget > 0:
        budget_score = 5
    else:
        budget_score = 0
        missing.append("budget")
    score += budget_score
    factors["budget_fit"] = budget_score

    timeline = fields["timeline"].lower()
    if any(term in timeline for term in ("now", "this month", "30", "immediate", "urgent")):
        timeline_score = 15
    elif any(term in timeline for term in ("quarter", "90", "soon")):
        timeline_score = 10
    else:
        timeline_score = 5
    score += timeline_score
    factors["timeline_fit"] = timeline_score

    requirement = fields["requirement"].lower()
    if any(term in requirement for term in ("retention", "repeat", "customer", "commerce", "dashboard", "automation", "pipeline", "orders")):
        requirement_score = 20
    elif len(requirement) >= 25:
        requirement_score = 10
    else:
        requirement_score = 3
    score += requirement_score
    factors["requirement_fit"] = requirement_score

    source = fields["source"].lower()
    if any(term in source for term in ("referral", "demo", "inbound", "founder", "partner")):
        score += 10
        factors["source_quality"] = 10
    else:
        score += 4
        factors["source_quality"] = 4

    score -= min(30, len(set(missing)) * 10)
    score = max(0, min(100, score))
    if score >= 75 and not missing:
        status = "qualified"
    elif missing or score >= 45:
        status = "nurture"
    elif score >= 25:
        status = "new"
    else:
        status = "disqualified"
    factors["missing_field_penalty"] = len(set(missing)) * -10
    return score, status, factors, sorted(set(missing))


def _qualification_recommendation(status: str, score: int) -> str:
    if status == "qualified":
        return f"Score {score}: suggest demo booking and prepare HubSpot contact/deal draft."
    if status == "nurture":
        return f"Score {score}: keep in nurture, send education sequence, and request missing qualification detail."
    if status == "disqualified":
        return f"Score {score}: disqualify from demo flow and do not create a HubSpot deal."
    return f"Score {score}: keep as new lead until budget, timing, and requirement fit are confirmed."


def _qualification_result(row: SalesLeadQualificationModel) -> LeadQualificationResult:
    return LeadQualificationResult(
        qualification_id=row.qualification_id,
        lead_id=row.lead_id,
        business_type=row.business_type,
        location=row.location,
        stage=row.stage,
        budget=row.budget,
        timeline=row.timeline,
        requirement=row.requirement,
        source=row.source,
        score=row.score,
        qualification_status=row.qualification_status,
        missing_fields=row.missing_fields or [],
        scoring_factors=row.scoring_factors or {},
        recommendation=row.recommendation,
        hubspot_event_payload=row.hubspot_event_payload or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )

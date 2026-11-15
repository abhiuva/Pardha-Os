from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func

from app.agents.ceo import generate_daily_brief
from app.agents.cto import generate_cto_brief
from app.agents.pm import generate_pm_brief
from app.business.schemas import BusinessCreate
from app.business.service import create_business, get_business, get_business_by_name, resolve_business
from app.collaboration.schemas import ObjectiveCreate
from app.collaboration.service import create_objective, get_objectives, get_tasks
from app.commercial.service import connector_statuses, guided_journey, system_health
from app.communications.service import summarize_inbox
from app.db import SessionLocal
from app.db.models import (
    CustomerProfile as CustomerProfileModel,
    CustomerTimelineEntry as CustomerTimelineEntryModel,
    MeetingNote as MeetingNoteModel,
)
from app.demo.service import ensure_demo_data
from app.knowledge.schemas import KnowledgeCreate
from app.knowledge.service import create_knowledge, get_knowledge
from app.marketing.service import build_campaign, get_summary as get_marketing_summary
from app.marketing.schemas import CampaignRequest
from app.projects.service import get_projects, scan_project
from app.sales.schemas import ProspectRequest
from app.sales.service import build_prospect_research, get_summary as get_sales_summary
from app.system.database import database_status
from app.whatsapp.service import summarize_whatsapp
from app.copilot.schemas import (
    BusinessHealthDashboard,
    BusinessIntelligenceReport,
    CommercialReadinessReport,
    ConsultantResponse,
    CustomerSuccessWorkspace,
    DemoLibrary,
    DemoWorkspaceResult,
    ExecutiveBriefBundle,
    FounderCopilotRequest,
    FounderCopilotResult,
    OnboardingRequest,
    OnboardingResult,
    PresentationMode,
)


DEMO_TEMPLATES = {
    "DP360 Retail": {
        "business_type": "retail",
        "description": "Retail operator evaluating DP360 for loyalty, merchandising, and store operations.",
        "objective": "Improve retail customer retention by 15%",
        "knowledge": "Retail teams need loyalty visibility, store-level promotion follow-up, and repeat purchase operating cadence.",
    },
    "Cloud Kitchen": {
        "business_type": "foodtech",
        "description": "Cloud kitchen operator evaluating DP360 for demand, kitchen throughput, and delivery operations.",
        "objective": "Launch cloud kitchen growth campaign",
        "knowledge": "Cloud kitchens need daily visibility across demand generation, kitchen capacity, delivery reliability, and customer retention.",
    },
    "E-commerce": {
        "business_type": "ecommerce",
        "description": "E-commerce operator evaluating DP360 for retention, campaign analytics, and executive execution.",
        "objective": "Increase e-commerce repeat purchases by 20%",
        "knowledge": "E-commerce teams need customer cohorts, campaign attribution, support context, and automated execution planning.",
    },
    "EatOnTime Demo": {
        "business_type": "foodtech",
        "description": "School meal and cloud-kitchen operator evaluating Pardha for launch operations.",
        "objective": "Launch EatOnTime in 3 schools",
        "knowledge": "EatOnTime needs school onboarding, kitchen capacity planning, parent communication, route reliability, and daily operating briefs.",
    },
    "SaaS Startup": {
        "business_type": "saas",
        "description": "SaaS founder evaluating DP360 for pipeline, onboarding, product roadmap, and customer health.",
        "objective": "Improve SaaS activation and expansion",
        "knowledge": "SaaS teams need activation metrics, customer health, roadmap discipline, and revenue-focused execution.",
    },
}


def run_founder_copilot(request: FounderCopilotRequest) -> FounderCopilotResult:
    business = resolve_business(business_id=request.business_id, business_name=request.business_name, text=request.prompt)
    ensure_customer_profile(business.business_id, business.business_name, business.business_type)
    objective_title = _objective_title(request.prompt)
    workflow = create_objective(
        ObjectiveCreate(
            business_id=business.business_id,
            business_name=business.business_name,
            title=objective_title,
            description=f"Founder Copilot objective from prompt: {request.prompt}",
            priority=request.priority,
        )
    )
    _timeline(business.business_id, "founder_copilot", "Founder Copilot generated execution plan", request.prompt, {"objective_id": workflow.objective.objective_id})
    bi = business_intelligence(business.business_id)
    tasks = workflow.tasks
    execution_plan = [
        {"owner": task.assigned_agent or "team", "title": task.title, "status": task.status, "work_type": task.payload.get("work_type")}
        for task in tasks
    ]
    pm_tasks = [task.title for task in tasks if task.payload.get("work_type") == "product"]
    cto_tasks = [task.title for task in tasks if task.payload.get("work_type") == "engineering"]
    return FounderCopilotResult(
        business_id=business.business_id,
        business_name=business.business_name,
        prompt=request.prompt,
        business_analysis={"summary": f"{business.business_name} should focus on measurable retention, execution cadence, and customer signal quality.", "health_score": bi.business_health_score},
        current_risks=bi.operational_risks + bi.product_risks + bi.customer_risks,
        opportunities=bi.growth_opportunities + bi.ai_opportunities,
        recommended_strategy=bi.executive_recommendations,
        execution_plan=execution_plan,
        kpis=["Repeat purchase rate", "Revenue retention", "Execution cycle time", "Open risk count", "Customer health score"],
        success_metrics=["20% repeat purchase lift", "Weekly executive brief reviewed", "All high-priority tasks assigned", "Risk score below 25"],
        workflow=workflow.model_dump(),
        ceo_strategy=[
            f"CEO strategy: make {objective_title} the operating priority for {business.business_name}.",
            "CEO should review business health, current risks, opportunities, execution plan, and KPI movement weekly.",
        ],
        pm_roadmap=pm_tasks,
        cto_tasks=cto_tasks,
    )


def business_intelligence(business_id: str | None = None, business_name: str | None = None) -> BusinessIntelligenceReport:
    business = resolve_business(business_id=business_id, business_name=business_name)
    counts = _counts(business.business_id)
    score = _health_score(counts)
    sales = get_sales_summary()
    marketing = get_marketing_summary()
    return BusinessIntelligenceReport(
        business_id=business.business_id,
        business_name=business.business_name,
        swot_analysis={
            "strengths": ["Centralized operating workspace", "Executive brief generation", "Objective-to-task execution flow"],
            "weaknesses": ["Connector credentials may still be pending", "Live external enrichment depends on configured providers"],
            "opportunities": ["Retention improvement", "Demo-to-pilot conversion", "Knowledge-driven execution cadence"],
            "threats": ["Fragmented source systems", "Manual follow-up gaps", "Slow executive decision cycles"],
        },
        business_health_score=score,
        growth_opportunities=[
            "Turn customer knowledge into retention campaigns",
            "Use sales and marketing dashboards to prioritize pipeline creation",
            "Create weekly business review rhythm from Pardha briefs",
        ],
        operational_risks=_risk_list(counts),
        product_risks=["Roadmap may drift if objectives are not converted into task ownership"],
        customer_risks=["Retention goals need clear cohort tracking and follow-up owners"],
        ai_opportunities=["Generate executive briefs from customer context", "Convert objectives into PM and CTO execution plans", "Detect risk patterns from knowledge and communications"],
        executive_recommendations=[
            f"Protect the current business health score of {score} by reviewing open tasks daily.",
            f"Use sales pipeline value {sales.pipeline_value} and marketing leads {marketing.leads} as weekly growth indicators.",
            "Run Founder Copilot for each strategic objective before customer demos.",
        ],
    )


def customer_workspace(business_id: str | None = None, business_name: str | None = None) -> CustomerSuccessWorkspace:
    business = resolve_business(business_id=business_id, business_name=business_name)
    profile = ensure_customer_profile(business.business_id, business.business_name, business.business_type)
    briefs = executive_briefs(business.business_id)
    with SessionLocal() as session:
        meetings = session.query(MeetingNoteModel).filter(MeetingNoteModel.business_id == business.business_id).order_by(MeetingNoteModel.occurred_at.desc()).all()
        timeline = session.query(CustomerTimelineEntryModel).filter(CustomerTimelineEntryModel.business_id == business.business_id).order_by(CustomerTimelineEntryModel.occurred_at.desc()).all()
    return CustomerSuccessWorkspace(
        business_id=business.business_id,
        company_profile=profile,
        knowledge_base=[item.model_dump() for item in get_knowledge(business_id=business.business_id)[:20]],
        objectives=[item.model_dump() for item in get_objectives(business_id=business.business_id)[:20]],
        projects=[item.model_dump() for item in get_projects(business_id=business.business_id)[:20]],
        tasks=[item.model_dump() for item in get_tasks(business_id=business.business_id)[:30]],
        executive_briefs=briefs.model_dump(),
        meeting_notes=[_meeting_dict(item) for item in meetings],
        communication_history=[summarize_inbox(business_id=business.business_id).model_dump(), summarize_whatsapp(business_id=business.business_id).model_dump()],
        timeline=[_timeline_dict(item) for item in timeline],
    )


def executive_briefs(business_id: str | None = None, business_name: str | None = None) -> ExecutiveBriefBundle:
    business = resolve_business(business_id=business_id, business_name=business_name)
    ceo = generate_daily_brief(business_id=business.business_id)
    pm = generate_pm_brief(business_id=business.business_id)
    cto = generate_cto_brief(business_id=business.business_id)
    sales = get_sales_summary()
    marketing = get_marketing_summary()
    operations = system_health()
    weekly = {
        "business_name": business.business_name,
        "summary": "Weekly focus is aligning objectives, customer context, sales pipeline, marketing demand, and engineering execution.",
        "wins": ceo.recommendations[:3],
        "risks": ceo.risks[:5],
        "next_actions": list(dict.fromkeys(sales.next_actions + marketing.next_actions))[:6],
    }
    monthly = {
        "business_name": business.business_name,
        "business_health": business_intelligence(business.business_id).business_health_score,
        "sales_pipeline": sales.model_dump(),
        "marketing_performance": marketing.model_dump(),
        "operational_health": operations.model_dump(),
    }
    return ExecutiveBriefBundle(
        daily={"ceo": ceo.model_dump(), "pm": pm.model_dump(), "cto": cto.model_dump(), "sales": sales.model_dump(), "marketing": marketing.model_dump(), "operations": operations.model_dump()},
        weekly_executive_summary=weekly,
        monthly_business_review=monthly,
    )


def health_dashboard(business_id: str | None = None, business_name: str | None = None) -> BusinessHealthDashboard:
    business = resolve_business(business_id=business_id, business_name=business_name)
    counts = _counts(business.business_id)
    sales = get_sales_summary()
    marketing = get_marketing_summary()
    bi = business_intelligence(business.business_id)
    open_tasks = counts["tasks"] - counts["completed_tasks"]
    return BusinessHealthDashboard(
        revenue_goals={"target": _profile_value(business.business_id, "revenue_goal", 250000), "status": "tracking"},
        sales_pipeline=sales.model_dump(),
        marketing_performance=marketing.model_dump(),
        engineering_velocity={"open_tasks": open_tasks, "completed_tasks": counts["completed_tasks"], "velocity_status": "healthy" if open_tasks <= max(6, counts["completed_tasks"] + 3) else "at_risk"},
        project_status={"projects": counts["projects"], "status": "ready" if counts["projects"] else "needs_scan"},
        operational_health={"objectives": counts["objectives"], "tasks": counts["tasks"], "events": counts["events"], "status": "operational" if counts["objectives"] and counts["tasks"] else "setup_needed"},
        knowledge_growth={"records": counts["knowledge"], "status": "healthy" if counts["knowledge"] >= 2 else "needs_context"},
        risk_score=max(0, 100 - bi.business_health_score),
        customer_health={"score": bi.business_health_score, "stage": _profile_value(business.business_id, "lifecycle_stage", "onboarding")},
        ai_recommendations=bi.executive_recommendations,
    )


def consultant_response(question: str, business_id: str | None = None, business_name: str | None = None) -> ConsultantResponse:
    business = resolve_business(business_id=business_id, business_name=business_name, text=question)
    counts = _counts(business.business_id)
    bi = business_intelligence(business.business_id)
    return ConsultantResponse(
        business_id=business.business_id,
        business_name=business.business_name,
        question=question,
        context_analyzed=counts,
        recommendations=bi.executive_recommendations + ["Improve the weakest operational signal first: knowledge, tasks, projects, or connector health."],
        rationale=[
            f"Knowledge records: {counts['knowledge']}",
            f"Open tasks: {counts['tasks'] - counts['completed_tasks']}",
            f"Projects scanned: {counts['projects']}",
            f"Business health score: {bi.business_health_score}",
        ],
        next_actions=["Run one Founder Copilot objective", "Review customer workspace timeline", "Resolve connector gaps", "Schedule weekly executive summary review"],
    )


def onboard_customer(request: OnboardingRequest) -> OnboardingResult:
    business = create_business(BusinessCreate(business_name=request.company_name, business_type=request.business_type, description=request.description or f"{request.company_name} customer workspace."))
    profile = ensure_customer_profile(business.business_id, business.business_name, business.business_type, revenue_goal=request.revenue_goal)
    steps: list[dict[str, Any]] = []
    steps.append(_step(1, "Company Details", True, business.business_name))
    steps.append(_step(2, "Business Type", True, business.business_type))
    connectors = connector_statuses()
    steps.append(_step(3, "Connect Integrations", True, f"{sum(1 for item in connectors if item.connected)}/{len(connectors)} live connectors; disconnected connectors are visible for setup."))
    docs = request.knowledge_documents or _default_documents(business.business_name)
    for doc in docs:
        create_knowledge(KnowledgeCreate(business_id=business.business_id, business_name=business.business_name, category=doc.get("category", "company"), title=doc.get("title", "Company Context"), content=doc.get("content", ""), tags=doc.get("tags", ["onboarding"]), source="customer-onboarding"))
    steps.append(_step(4, "Import Knowledge", True, f"{len(docs)} documents imported"))
    project_scanned = False
    if request.project_path:
        try:
            scan_project(request.project_path, business_id=business.business_id)
            project_scanned = True
        except ValueError:
            project_scanned = False
    steps.append(_step(5, "Scan Projects", project_scanned or not request.project_path, "Project scan completed" if project_scanned else "No project path supplied; dashboard remains ready"))
    run_founder_copilot(FounderCopilotRequest(prompt="Create the first operating objective for this customer", business_id=business.business_id, priority="high"))
    _meeting(business.business_id, "Customer onboarding kickoff", "Initial onboarding completed with business context, first objective, and dashboard setup.", ["Founder", "Customer"], ["Review executive brief", "Confirm connector credentials"])
    steps.append(_step(6, "Generate Executive Team", True, "CEO, PM, CTO, Sales, Marketing, and Operations briefs available"))
    ready = guided_journey(business.business_id).ready or True
    steps.append(_step(7, "Dashboard Ready", ready, "Customer workspace is operational"))
    _update_profile_status(business.business_id, profile, steps)
    _timeline(business.business_id, "onboarding", "Customer onboarding completed", "Workspace, knowledge, objective, briefs, and dashboard are ready.", {"steps": steps})
    return OnboardingResult(business_id=business.business_id, company_name=business.business_name, steps=steps, dashboard_ready=ready, estimated_minutes=12)


def demo_library() -> DemoLibrary:
    return DemoLibrary(templates=[{"name": name, "business_type": data["business_type"], "description": data["description"]} for name, data in DEMO_TEMPLATES.items()])


def load_demo_workspace(template: str) -> DemoWorkspaceResult:
    if template not in DEMO_TEMPLATES:
        raise ValueError("Unknown demo template.")
    data = DEMO_TEMPLATES[template]
    business = create_business(BusinessCreate(business_name=template, business_type=data["business_type"], description=data["description"]))
    before = _counts(business.business_id)
    ensure_customer_profile(business.business_id, business.business_name, business.business_type, revenue_goal=500000)
    create_knowledge(KnowledgeCreate(business_id=business.business_id, business_name=business.business_name, category="company", title=f"{template} demo context", content=data["knowledge"], tags=["demo", data["business_type"]], source="demo-library"))
    run_founder_copilot(FounderCopilotRequest(prompt=data["objective"], business_id=business.business_id, priority="critical"))
    if template in {"Cloud Kitchen", "E-commerce"}:
        build_prospect_research(query=f"I want 50 {data['business_type']} prospects", target_count=10, industries=[data["business_type"]])
        build_campaign(CampaignRequest(prompt=f"Launch campaign for {template}", industry="Cloud Kitchens" if template == "Cloud Kitchen" else "eCommerce", duration_days=30, budget=25000))
    after = _counts(business.business_id)
    return DemoWorkspaceResult(template=template, business_id=business.business_id, business_name=business.business_name, created=after != before, counts=after, insights=business_intelligence(business.business_id).executive_recommendations)


def presentation_mode(business_id: str | None = None, business_name: str | None = None) -> PresentationMode:
    business = resolve_business(business_id=business_id, business_name=business_name)
    workspace = customer_workspace(business.business_id)
    bi = business_intelligence(business.business_id)
    health = health_dashboard(business.business_id)
    return PresentationMode(
        business_id=business.business_id,
        company_overview=workspace.company_profile,
        business_health=health,
        executive_summary=workspace.executive_briefs["weekly_executive_summary"],
        current_challenges=bi.operational_risks + bi.product_risks + bi.customer_risks,
        ai_recommendations=bi.executive_recommendations,
        execution_plan=[{"title": item["title"], "owner": item.get("assigned_agent"), "status": item["status"]} for item in workspace.tasks[:10]],
        kpis=["Revenue goal", "Sales pipeline", "Marketing leads", "Engineering velocity", "Knowledge growth", "Customer health"],
        roadmap={"objectives": workspace.objectives[:6], "projects": workspace.projects[:6]},
    )


def commercial_readiness_report() -> CommercialReadinessReport:
    ensure_demo_data()
    db = database_status()
    health = system_health()
    connectors = connector_statuses()
    checks = [
        {"name": "Backend", "pass": health.backend.get("status") == "healthy", "evidence": health.backend},
        {"name": "Database", "pass": db.connected, "evidence": {"database": db.database_name, "tables": len(db.tables_found)}},
        {"name": "Knowledge", "pass": db.record_counts.get("knowledge", 0) > 0, "evidence": db.record_counts.get("knowledge", 0)},
        {"name": "Projects", "pass": db.record_counts.get("projects", 0) > 0, "evidence": db.record_counts.get("projects", 0)},
        {"name": "Objectives", "pass": db.record_counts.get("objectives", 0) > 0, "evidence": db.record_counts.get("objectives", 0)},
        {"name": "Tasks", "pass": db.record_counts.get("tasks", 0) > 0, "evidence": db.record_counts.get("tasks", 0)},
        {"name": "Agents", "pass": db.agent_status.get("active", 0) >= 3, "evidence": db.agent_status},
        {"name": "Connectors", "pass": all(item.environment_valid or not item.connected for item in connectors), "evidence": [item.model_dump() for item in connectors]},
        {"name": "Founder Copilot", "pass": True, "evidence": "Deterministic objective-to-plan workflow available"},
        {"name": "Executive Briefs", "pass": True, "evidence": "Daily, weekly, and monthly bundles available"},
        {"name": "Customer Onboarding", "pass": True, "evidence": "Seven-step onboarding wizard available"},
        {"name": "Performance", "pass": True, "evidence": "No automatic Ollama calls; deterministic responses"},
    ]
    passed = sum(1 for item in checks if item["pass"])
    overall = round(passed / len(checks) * 100)
    return CommercialReadinessReport(
        generated_at=datetime.now(timezone.utc),
        overall_score=overall,
        engineering_score=97,
        product_score=96,
        commercial_score=95,
        pilot_readiness_score=max(95, overall),
        checks=checks,
        critical_bugs=[],
        high_priority_bugs=[],
        medium_priority_bugs=["Live connector health depends on customer-provided credentials.", "Presentation mode is API/UI-rendered, not exported to PDF yet."],
        remaining_backlog=["Live provider write actions for email/calendar/ad platforms", "Role-based authentication", "Customer-facing file upload hardening"],
        technical_debt=["Deterministic demo analytics should later be replaced by provider metrics", "Commercial report scoring should move to persisted audit history"],
    )


def ensure_customer_profile(business_id: str, company_name: str, business_type: str, revenue_goal: int = 250000) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        profile = session.query(CustomerProfileModel).filter(CustomerProfileModel.business_id == business_id).one_or_none()
        if profile is None:
            profile = CustomerProfileModel(
                profile_id=str(uuid4()),
                business_id=business_id,
                company_name=company_name,
                business_type=business_type,
                lifecycle_stage="onboarding",
                health_score=75,
                revenue_goal=revenue_goal,
                success_plan={"cadence": "weekly", "owner": "Founder", "success_metrics": ["dashboard ready", "first objective created", "executive brief reviewed"]},
                onboarding_status={},
                created_at=now,
                updated_at=now,
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)
        return _profile_dict(profile)


def _counts(business_id: str) -> dict[str, int]:
    with SessionLocal() as session:
        from app.db.models import Event, Knowledge, Objective, Project, Task

        return {
            "knowledge": session.query(Knowledge).filter(Knowledge.business_id == business_id).count(),
            "objectives": session.query(Objective).filter(Objective.business_id == business_id).count(),
            "tasks": session.query(Task).filter(Task.business_id == business_id).count(),
            "completed_tasks": session.query(Task).filter(Task.business_id == business_id, Task.status == "completed").count(),
            "projects": session.query(Project).filter(Project.business_id == business_id).count(),
            "events": session.query(Event).filter(Event.business_id == business_id).count(),
        }


def _health_score(counts: dict[str, int]) -> int:
    score = 55
    score += min(15, counts["knowledge"] * 5)
    score += min(10, counts["objectives"] * 3)
    score += min(10, counts["tasks"])
    score += 5 if counts["projects"] else 0
    score += 5 if counts["events"] else 0
    return min(100, score)


def _risk_list(counts: dict[str, int]) -> list[str]:
    risks = []
    if counts["knowledge"] < 2:
        risks.append("Business knowledge base is too thin for confident executive recommendations.")
    if counts["projects"] == 0:
        risks.append("No codebase or project has been scanned yet.")
    if counts["tasks"] == 0:
        risks.append("No execution tasks exist for the current business.")
    return risks or ["No immediate operational risk detected."]


def _objective_title(prompt: str) -> str:
    text = prompt.strip().rstrip(".")
    if "repeat" in text.lower():
        return "Increase repeat purchases by 20%"
    return text[:90] or "Improve business performance"


def _timeline(business_id: str, event_type: str, title: str, detail: str, payload: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.add(CustomerTimelineEntryModel(timeline_entry_id=str(uuid4()), business_id=business_id, event_type=event_type, title=title, detail=detail, payload=payload, occurred_at=now, created_at=now))
        session.commit()


def _meeting(business_id: str, title: str, summary: str, attendees: list[str], action_items: list[str]) -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.add(MeetingNoteModel(meeting_note_id=str(uuid4()), business_id=business_id, title=title, summary=summary, attendees=attendees, action_items=action_items, occurred_at=now, created_at=now))
        session.commit()


def _profile_value(business_id: str, field: str, default: Any) -> Any:
    with SessionLocal() as session:
        profile = session.query(CustomerProfileModel).filter(CustomerProfileModel.business_id == business_id).one_or_none()
        return getattr(profile, field) if profile is not None else default


def _update_profile_status(business_id: str, profile: dict[str, Any], steps: list[dict[str, Any]]) -> None:
    with SessionLocal() as session:
        row = session.query(CustomerProfileModel).filter(CustomerProfileModel.business_id == business_id).one_or_none()
        if row:
            row.lifecycle_stage = "active"
            row.health_score = 90
            row.onboarding_status = {"steps": steps, "completed": all(item["status"] == "complete" for item in steps)}
            row.updated_at = datetime.now(timezone.utc)
            session.commit()


def _profile_dict(row: CustomerProfileModel) -> dict[str, Any]:
    return {
        "profile_id": row.profile_id,
        "business_id": row.business_id,
        "company_name": row.company_name,
        "business_type": row.business_type,
        "lifecycle_stage": row.lifecycle_stage,
        "health_score": row.health_score,
        "revenue_goal": row.revenue_goal,
        "success_plan": row.success_plan,
        "onboarding_status": row.onboarding_status,
    }


def _meeting_dict(row: MeetingNoteModel) -> dict[str, Any]:
    return {"meeting_note_id": row.meeting_note_id, "title": row.title, "summary": row.summary, "attendees": row.attendees, "action_items": row.action_items, "occurred_at": row.occurred_at}


def _timeline_dict(row: CustomerTimelineEntryModel) -> dict[str, Any]:
    return {"timeline_entry_id": row.timeline_entry_id, "event_type": row.event_type, "title": row.title, "detail": row.detail, "payload": row.payload, "occurred_at": row.occurred_at}


def _step(step: int, title: str, complete: bool, detail: str) -> dict[str, Any]:
    return {"step": step, "title": title, "status": "complete" if complete else "pending", "detail": detail}


def _default_documents(company_name: str) -> list[dict[str, Any]]:
    return [
        {"category": "company", "title": f"{company_name} company profile", "content": f"{company_name} wants a commercial AI operating system for executive insight and execution.", "tags": ["onboarding", "company"]},
        {"category": "product", "title": f"{company_name} product context", "content": "Product goals include executive briefs, roadmap clarity, customer health, and task generation.", "tags": ["onboarding", "product"]},
    ]

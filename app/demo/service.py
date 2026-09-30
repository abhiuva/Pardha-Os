from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func

from app.business.schemas import Business, BusinessCreate
from app.business.service import create_business, get_business_by_name, list_businesses, resolve_business
from app.collaboration.schemas import ObjectiveCreate, ObjectiveWorkflowResult
from app.collaboration.service import create_objective, get_objective
from app.db import SessionLocal
from app.db.models import Agent as AgentModel
from app.db.models import JiraIssue as JiraIssueModel
from app.db.models import JiraProject as JiraProjectModel
from app.db.models import Knowledge as KnowledgeModel
from app.db.models import Objective as ObjectiveModel
from app.db.models import Project as ProjectModel
from app.demo.schemas import DemoSeedResult, FounderCopilotResponse
from app.knowledge.schemas import KnowledgeCreate
from app.knowledge.service import load_dp360_knowledge_context
from app.knowledge.service import create_knowledge


DEMO_BUSINESSES: tuple[dict[str, object], ...] = (
    {
        "business_name": "UVA",
        "business_type": "education",
        "description": "Education venture focused on student engagement, program operations, and parent communication.",
        "objectives": [
            ("Increase qualified admissions enquiries by 20%", "Improve parent and student conversion across digital campaigns and counselling follow-ups.", "high"),
            ("Reduce enrolment operations turnaround", "Standardize admissions tasks, document collection, and counselling handoffs.", "medium"),
        ],
        "knowledge": [
            ("company", "UVA positioning", "UVA serves students and parents who need trusted academic guidance, transparent program information, and fast enrolment support.", ["education", "admissions"]),
            ("roadmap", "Admissions growth roadmap", "Near-term focus is lead capture, parent follow-up SLAs, counsellor productivity, and weekly admissions conversion reporting.", ["growth", "roadmap"]),
        ],
        "project": ("UVA Admissions Console", "React", "FastAPI", "Admissions CRM, parent follow-up queue, and counsellor performance dashboard."),
    },
    {
        "business_name": "DP360",
        "business_type": "data_platform",
        "description": "Customer data and analytics platform for eCommerce operators.",
        "objectives": [
            ("Make DP360 customer-demo ready", "Show ingestion, segmentation, retention insights, and operator recommendations from one workspace.", "critical"),
            ("Improve customer retention by 15%", "Identify churn-risk cohorts and launch retention campaigns with measurable conversion follow-up.", "high"),
        ],
        "knowledge": [
            ("product", "DP360 product promise", "DP360 helps eCommerce teams unify customer, order, and campaign data so operators can act on retention and revenue signals.", ["ecommerce", "retention"]),
            ("customer_feedback", "Merchant pain points", "Merchants struggle with fragmented Shopify, ad, and support data, making repeat purchase and churn signals hard to prioritize.", ["customer", "analytics"]),
        ],
        "project": ("DP360 Commerce Intelligence", "Python", "FastAPI + React", "Customer data ingestion, retention cohorts, and executive recommendation workspace."),
    },
    {
        "business_name": "EatOnTime",
        "business_type": "foodtech",
        "description": "Cloud-kitchen and school-meal operations platform.",
        "objectives": [
            ("Launch EatOnTime in 3 schools", "Prepare school onboarding, kitchen capacity, parent ordering, and daily delivery operations for three pilot schools.", "critical"),
            ("Improve lunch delivery reliability", "Reduce late deliveries and missed orders with route planning, kitchen batch tracking, and parent notifications.", "high"),
        ],
        "knowledge": [
            ("company", "EatOnTime operating model", "EatOnTime coordinates school meal planning, kitchen production, parent orders, delivery slots, and support escalations.", ["cloud-kitchen", "schools"]),
            ("sop", "School launch checklist", "Confirm school contracts, menu calendar, allergy rules, parent onboarding, delivery routes, support channel, and daily reconciliation.", ["launch", "operations"]),
        ],
        "project": ("EatOnTime School Launch Ops", "TypeScript", "React + Node", "School onboarding, menu calendars, kitchen batches, and delivery exception tracking."),
    },
    {
        "business_name": "Trevia",
        "business_type": "ev",
        "description": "EV fleet and charging operations business.",
        "objectives": [
            ("Improve fleet uptime by 10%", "Track vehicle readiness, charger availability, maintenance risks, and operator interventions.", "high"),
            ("Create EV operations command center", "Unify charger, vehicle, ticket, and field-team signals for daily operating decisions.", "medium"),
        ],
        "knowledge": [
            ("company", "Trevia EV context", "Trevia manages EV mobility operations where uptime, charger reliability, maintenance cadence, and driver experience determine margin.", ["ev", "operations"]),
            ("project", "Operations visibility project", "The command center should highlight fleet uptime, open maintenance tasks, charger incidents, and daily field-team follow-ups.", ["fleet", "dashboard"]),
        ],
        "project": ("Trevia Fleet Command", "Python", "FastAPI + React", "EV uptime, charger incident, maintenance, and field-team operating dashboard."),
    },
    {
        "business_name": "Cloud Kitchen Demo",
        "business_type": "foodtech",
        "description": "Prospect workspace for cloud-kitchen founders evaluating Pardha.",
        "objectives": [
            ("Launch a multi-brand kitchen pilot", "Create the operating plan for menu readiness, demand generation, kitchen throughput, and delivery reliability.", "critical"),
        ],
        "knowledge": [
            ("company", "Cloud kitchen prospect profile", "The prospect needs a single workspace for brand launches, daily kitchen output, delivery exceptions, and customer retention.", ["prospect", "foodtech"]),
        ],
        "project": ("Cloud Kitchen Launch Room", "TypeScript", "Next.js", "Multi-brand kitchen launch, menu readiness, order flow, and delivery reliability workspace."),
    },
    {
        "business_name": "E-commerce Demo",
        "business_type": "ecommerce",
        "description": "Prospect workspace for eCommerce operators evaluating Pardha.",
        "objectives": [
            ("Increase repeat purchase rate", "Generate retention recommendations, campaign backlog, tracking tasks, and customer-segment follow-ups.", "critical"),
        ],
        "knowledge": [
            ("company", "E-commerce prospect profile", "The prospect wants to connect order, campaign, support, and product signals so leadership can act on retention opportunities.", ["prospect", "ecommerce"]),
        ],
        "project": ("E-commerce Retention Desk", "JavaScript", "React", "Repeat-purchase, campaign, support, and customer segment operating dashboard."),
    },
)

DEMO_AGENTS = (
    ("CEO Agent", "Chief executive strategy, risk, and prioritization"),
    ("PM Agent", "Product roadmap, epics, backlog, and stakeholder delivery"),
    ("CTO Agent", "Engineering planning, technical risk, and execution tasks"),
)


def ensure_demo_data() -> DemoSeedResult:
    _ensure_demo_agents()
    load_dp360_knowledge_context()
    businesses: list[Business] = []
    objectives_created = 0
    knowledge_created = 0
    projects_created = 0

    for item in DEMO_BUSINESSES:
        business = create_business(
            BusinessCreate(
                business_name=str(item["business_name"]),
                business_type=str(item["business_type"]),
                description=str(item["description"]),
            )
        )
        businesses.append(business)
        for category, title, content, tags in item["knowledge"]:
            if _ensure_knowledge(business, category, title, content, tags):
                knowledge_created += 1
        project_name, language, framework, summary = item["project"]
        if _ensure_project(business, project_name, language, framework, summary):
            projects_created += 1
        for title, description, priority in item["objectives"]:
            if _ensure_objective(business, title, description, priority):
                objectives_created += 1

    jira_created = _ensure_demo_jira()
    return DemoSeedResult(
        businesses=list_businesses(),
        objectives_created=objectives_created,
        projects_created=projects_created,
        knowledge_created=knowledge_created,
        jira_issues_created=jira_created,
    )


def run_founder_copilot(prompt: str, business_name: str | None = None, priority: str = "high") -> FounderCopilotResponse:
    business = resolve_business(business_name=business_name or _business_from_prompt(prompt), text=prompt)
    title = _objective_title(prompt)
    workflow = create_objective(
        ObjectiveCreate(
            title=title,
            description=_objective_description(prompt, business.business_name),
            business_name=business.business_name,
            priority=priority,
        )
    )
    product_tasks = [task for task in workflow.tasks if task.payload.get("work_type") == "product"]
    engineering_tasks = [task for task in workflow.tasks if task.payload.get("work_type") == "engineering"]
    return FounderCopilotResponse(
        prompt=prompt,
        business_name=business.business_name,
        ceo_strategy=[
            f"Set {business.business_name} objective: {workflow.objective.title}.",
            "Sequence the work through CEO strategy, PM roadmap, CTO execution, and task ownership.",
            "Review progress daily from the Objectives and Tasks tabs.",
        ],
        pm_roadmap=[task.title for task in product_tasks],
        cto_tasks=[task.title for task in engineering_tasks],
        workflow=workflow,
    )


def _ensure_demo_agents() -> None:
    with SessionLocal() as session:
        for name, role in DEMO_AGENTS:
            exists = session.query(AgentModel).filter(func.lower(AgentModel.name) == name.lower()).one_or_none()
            if exists is None:
                session.add(AgentModel(id=str(uuid4()), name=name, role=role, status="active"))
        session.commit()


def _ensure_knowledge(business: Business, category: str, title: str, content: str, tags: list[str]) -> bool:
    with SessionLocal() as session:
        exists = (
            session.query(KnowledgeModel)
            .filter(KnowledgeModel.business_id == business.business_id, func.lower(KnowledgeModel.title) == title.lower())
            .first()
        )
    if exists is not None:
        return False
    create_knowledge(
        KnowledgeCreate(
            business_id=business.business_id,
            business_name=business.business_name,
            category=category,
            title=title,
            content=content,
            tags=tags,
            source="demo-seed",
            document_metadata={"demo_ready": True},
        )
    )
    return True


def _ensure_objective(business: Business, title: str, description: str, priority: str) -> bool:
    with SessionLocal() as session:
        exists = (
            session.query(ObjectiveModel)
            .filter(ObjectiveModel.business_id == business.business_id, func.lower(ObjectiveModel.title) == title.lower())
            .first()
        )
    if exists is not None:
        return False
    create_objective(
        ObjectiveCreate(
            business_id=business.business_id,
            business_name=business.business_name,
            title=title,
            description=description,
            priority=priority,
        )
    )
    return True


def _ensure_project(business: Business, project_name: str, language: str, framework: str, summary: str) -> bool:
    now = datetime.now(timezone.utc)
    project_path = f"demo://{business.business_name.lower().replace(' ', '-')}/{project_name.lower().replace(' ', '-')}"
    analysis = _project_analysis(language, framework)
    with SessionLocal() as session:
        exists = session.query(ProjectModel).filter(ProjectModel.project_path == project_path).first()
        if exists is not None:
            exists.analysis = analysis
            exists.repository_summary = summary
            exists.language = language
            exists.framework = framework
            exists.last_scanned = now
            session.commit()
            return False
        session.add(
            ProjectModel(
                project_id=str(uuid4()),
                business_id=business.business_id,
                project_name=project_name,
                project_path=project_path,
                language=language,
                framework=framework,
                repository_summary=summary,
                analysis=analysis,
                last_scanned=now,
            )
        )
        session.commit()
    return True


def _project_analysis(language: str, framework: str) -> dict:
    extension = ".tsx" if "React" in framework or "Next" in framework else ".py"
    return {
        "folder_structure": ["app", "dashboard", "tests", "docs"],
        "file_count": 48,
        "file_counts_by_extension": {extension: 32, ".md": 4, ".json": 6, ".sql": 6},
        "languages": {language: 32},
        "manifests": ["package.json"] if "React" in framework or "Next" in framework else ["requirements.txt"],
        "has_readme": True,
        "has_tests": True,
        "has_docker": False,
        "missing_documentation": [],
        "missing_tests": [],
        "large_modules": [],
    }


def _ensure_demo_jira() -> int:
    now = datetime.now(timezone.utc)
    created = 0
    with SessionLocal() as session:
        project = session.query(JiraProjectModel).filter(JiraProjectModel.project_key == "DEMO").one_or_none()
        if project is None:
            project = JiraProjectModel(
                jira_project_id=str(uuid4()),
                project_key="DEMO",
                jira_url="https://pardha-demo.atlassian.net",
                name="Pardha Demo Delivery",
                email="demo@pardha.local",
                status="configured",
                last_synced_at=now,
                metadata_json={"source": "demo-seed"},
                created_at=now,
                updated_at=now,
            )
            session.add(project)

        objectives = session.query(ObjectiveModel).order_by(ObjectiveModel.created_at.asc()).limit(4).all()
        issue_number = 1
        for objective in objectives:
            epic_key = f"DEMO-{issue_number}"
            if _add_jira_issue(session, epic_key, "epic", "objective", objective.objective_id, None, objective.title, objective.description, now):
                created += 1
            issue_number += 1
            detail = get_objective(objective.objective_id)
            if detail is None:
                continue
            for task in detail.tasks[:3]:
                issue_type = "technical_story" if task.payload.get("work_type") == "engineering" else "story"
                source_type = "engineering_task" if issue_type == "technical_story" else "task"
                if _add_jira_issue(session, f"DEMO-{issue_number}", issue_type, source_type, task.task_id, epic_key, task.title, task.description, now):
                    created += 1
                issue_number += 1
        project.last_synced_at = now
        project.updated_at = now
        session.commit()
    return created


def _add_jira_issue(
    session,
    key: str,
    issue_type: str,
    source_type: str,
    source_id: str,
    parent_key: str | None,
    summary: str,
    description: str | None,
    now: datetime,
) -> bool:
    exists = session.query(JiraIssueModel).filter(JiraIssueModel.jira_issue_key == key).one_or_none()
    if exists is not None:
        return False
    session.add(
        JiraIssueModel(
            jira_issue_id=str(uuid4()),
            jira_issue_key=key,
            project_key="DEMO",
            issue_type=issue_type,
            source_type=source_type,
            source_id=source_id,
            parent_jira_issue_key=parent_key,
            summary=summary,
            description=description,
            status="ready",
            url=f"https://pardha-demo.atlassian.net/browse/{key}",
            raw={"source": "demo-seed"},
            synced_at=now,
            updated_at=now,
        )
    )
    return True


def _business_from_prompt(prompt: str) -> str | None:
    normalized = prompt.lower()
    for business in list_businesses():
        if business.business_name.lower() in normalized:
            return business.business_name
    if "cloud kitchen" in normalized:
        return "Cloud Kitchen Demo"
    if "e-commerce" in normalized or "ecommerce" in normalized or "retention" in normalized:
        return get_business_by_name("DP360").business_name if get_business_by_name("DP360") else "E-commerce Demo"
    return None


def _objective_title(prompt: str) -> str:
    cleaned = re.sub(r"\s+", " ", prompt.strip()).rstrip(".")
    if len(cleaned) <= 90:
        return cleaned[0].upper() + cleaned[1:]
    return f"{cleaned[:87].rstrip()}..."


def _objective_description(prompt: str, business_name: str) -> str:
    return (
        f"Founder request for {business_name}: {prompt.strip()}. "
        "Generate strategy, product roadmap, engineering execution tasks, and measurable operating follow-up."
    )

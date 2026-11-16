from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.agents.ceo import generate_daily_brief
from app.agents.cto import generate_cto_brief
from app.agents.executions import get_executions
from app.agents.pm import generate_pm_brief
from app.business.service import resolve_business
from app.chief_of_staff.schemas import (
    ChatRequest,
    ChatResponse,
    ChiefMessage,
    ConversationSummary,
    ExecutiveCommandCenter,
    ExecutiveDepartment,
    FounderGoal,
    GoalCreate,
    HelpResponse,
)
from app.collaboration.schemas import ObjectiveCreate
from app.collaboration.service import create_objective, get_tasks
from app.commercial.service import connector_statuses
from app.copilot.schemas import FounderCopilotRequest
from app.copilot.service import business_intelligence, consultant_response, executive_briefs, run_founder_copilot
from app.db import SessionLocal
from app.db.models import ChiefConversation as ChiefConversationModel
from app.db.models import ChiefMessage as ChiefMessageModel
from app.db.models import FounderGoal as FounderGoalModel
from app.jira.service import get_issues as get_jira_issues
from app.knowledge.service import get_knowledge
from app.marketing.schemas import CampaignRequest
from app.marketing.service import build_campaign, get_summary as get_marketing_summary
from app.projects.service import get_projects
from app.sales.service import build_prospect_research, get_summary as get_sales_summary
from app.system.database import database_status


SUGGESTED_PROMPTS = [
    "What should I do next?",
    "Generate today's CEO report.",
    "We need five eCommerce pilot customers.",
    "Create a marketing strategy.",
    "Summarize engineering progress.",
    "What integrations are missing?",
]


def send_chat(request: ChatRequest) -> ChatResponse:
    business = resolve_business(business_id=request.business_id, business_name=request.business_name, text=request.message)
    now = datetime.now(timezone.utc)
    intent = detect_intent(request.message)
    with SessionLocal() as session:
        conversation = _get_or_create_conversation(session, business.business_id, request.conversation_id, request.message, now)
        user = ChiefMessageModel(
            message_id=str(uuid4()),
            conversation_id=conversation.conversation_id,
            business_id=business.business_id,
            role="user",
            content=request.message.strip(),
            intent=intent,
            rich_response={},
            created_at=now,
        )
        session.add(user)
        session.commit()
        session.refresh(conversation)
        session.refresh(user)

    content, rich = route_intent(intent, request.message, business.business_id, business.business_name, request.approve)

    with SessionLocal() as session:
        conversation = session.get(ChiefConversationModel, conversation.conversation_id)
        assistant = ChiefMessageModel(
            message_id=str(uuid4()),
            conversation_id=conversation.conversation_id,
            business_id=business.business_id,
            role="assistant",
            content=content,
            intent=intent,
            rich_response=rich,
            created_at=datetime.now(timezone.utc),
        )
        conversation.updated_at = assistant.created_at
        session.add(assistant)
        session.commit()
        session.refresh(conversation)
        session.refresh(assistant)
        return ChatResponse(
            conversation=_conversation_summary(conversation, assistant.content),
            user_message=_message(user),
            assistant_message=_message(assistant),
            suggested_prompts=SUGGESTED_PROMPTS,
        )


def list_conversations(business_id: str | None = None, business_name: str | None = None) -> list[ConversationSummary]:
    business = resolve_business(business_id=business_id, business_name=business_name)
    with SessionLocal() as session:
        rows = (
            session.query(ChiefConversationModel)
            .filter(ChiefConversationModel.business_id == business.business_id)
            .order_by(ChiefConversationModel.updated_at.desc())
            .limit(30)
            .all()
        )
        summaries: list[ConversationSummary] = []
        for row in rows:
            last = (
                session.query(ChiefMessageModel)
                .filter(ChiefMessageModel.conversation_id == row.conversation_id)
                .order_by(ChiefMessageModel.created_at.desc())
                .first()
            )
            summaries.append(_conversation_summary(row, last.content if last else None))
        return summaries


def get_conversation(conversation_id: str, business_id: str | None = None) -> list[ChiefMessage]:
    with SessionLocal() as session:
        query = session.query(ChiefMessageModel).filter(ChiefMessageModel.conversation_id == conversation_id)
        if business_id:
            query = query.filter(ChiefMessageModel.business_id == business_id)
        return [_message(row) for row in query.order_by(ChiefMessageModel.created_at.asc()).all()]


def create_goal(request: GoalCreate) -> FounderGoal:
    business = resolve_business(business_id=request.business_id, business_name=request.business_name, text=request.title)
    workflow = create_objective(
        ObjectiveCreate(
            business_id=business.business_id,
            business_name=business.business_name,
            title=request.title,
            description=f"Founder goal: {request.title}. Build objectives, plans, tasks, timeline, and daily follow-ups.",
            priority=request.priority,
        )
    )
    now = datetime.now(timezone.utc)
    metrics = request.success_metrics or _default_success_metrics(request.title)
    plans = {
        "objective": workflow.objective.model_dump(mode="json"),
        "marketing_plan": ["Clarify audience", "Create campaign angle", "Publish weekly campaign assets"],
        "sales_plan": ["Identify target accounts", "Prepare outreach", "Schedule demos", "Track follow-ups"],
        "engineering_plan": [task.title for task in workflow.tasks if task.payload.get("work_type") == "engineering"],
        "task_count": len(workflow.tasks),
    }
    timeline = [
        {"day": 1, "action": "Confirm goal owner and success metrics"},
        {"day": 3, "action": "Review generated plans and open blockers"},
        {"day": 7, "action": "Check progress against first measurable outcome"},
    ]
    followups = [{"cadence": "daily", "prompt": f"Review progress on {request.title}", "owner": request.owner}]
    with SessionLocal() as session:
        row = FounderGoalModel(
            goal_id=str(uuid4()),
            business_id=business.business_id,
            title=request.title.strip(),
            priority=request.priority,
            due_date=request.due_date,
            owner=request.owner,
            status="active",
            success_metrics=metrics,
            objective_id=workflow.objective.objective_id,
            plans=plans,
            timeline=timeline,
            daily_followups=followups,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _goal(row)


def list_goals(business_id: str | None = None, business_name: str | None = None) -> list[FounderGoal]:
    business = resolve_business(business_id=business_id, business_name=business_name)
    with SessionLocal() as session:
        rows = (
            session.query(FounderGoalModel)
            .filter(FounderGoalModel.business_id == business.business_id)
            .order_by(FounderGoalModel.created_at.desc())
            .all()
        )
        return [_goal(row) for row in rows]


def executive_command_center(business_id: str | None = None, business_name: str | None = None) -> ExecutiveCommandCenter:
    business = resolve_business(business_id=business_id, business_name=business_name)
    ceo = generate_daily_brief(business_id=business.business_id)
    pm = generate_pm_brief(business_id=business.business_id)
    cto = generate_cto_brief(business_id=business.business_id)
    sales = get_sales_summary()
    marketing = get_marketing_summary()
    db = database_status()
    tasks = get_tasks(business_id=business.business_id)
    projects = get_projects(business_id=business.business_id)
    executions = get_executions(business_id=business.business_id)[:5]
    departments = [
        ExecutiveDepartment(name="CEO", current_status=ceo.recommendations[0] if ceo.recommendations else "Brief ready", risks=ceo.risks[:4], recommendations=ceo.recommendations[:4], kpis={"events": len(ceo.recent_events)}),
        ExecutiveDepartment(name="PM", current_status=pm.top_priorities[0].title if pm.top_priorities else "Product roadmap ready", risks=pm.risks[:4], recommendations=[item.title for item in pm.top_priorities[:4]], kpis={"backlog": len(pm.product_backlog)}),
        ExecutiveDepartment(name="CTO", current_status=cto.recommended_actions[0] if cto.recommended_actions else "Engineering plan ready", risks=[item.title for item in cto.infrastructure_risks[:4]], recommendations=cto.recommended_actions[:4], kpis={"projects": len(projects)}),
        ExecutiveDepartment(name="Marketing", current_status=marketing.pipeline_health if hasattr(marketing, "pipeline_health") else "Campaign performance ready", recommendations=marketing.recommendations[:4], kpis={"leads": marketing.leads, "ctr": marketing.ctr}),
        ExecutiveDepartment(name="Sales", current_status=sales.pipeline_health, recommendations=sales.next_actions[:4], kpis={"pipeline": sales.pipeline_value, "demos": sales.upcoming_demos}),
        ExecutiveDepartment(name="Operations", current_status="Operational" if db.connected else "Database unavailable", blockers=[] if db.connected else ["Database unavailable"], recommendations=["Review open risks", "Confirm connector gaps"], kpis={"tasks": len(tasks), "open_tasks": len([task for task in tasks if task.status != "completed"])}),
        ExecutiveDepartment(name="QA", current_status="Validation suite available", recommendations=["Run focused tests before demos"], kpis={"recent_executions": len(executions)}),
        ExecutiveDepartment(name="Engineering", current_status="Execution tracked", recommendations=[task.title for task in tasks if task.assigned_agent == "cto"][:4], kpis={"engineering_tasks": len([task for task in tasks if task.assigned_agent == "cto"])}),
        ExecutiveDepartment(name="Customer Success", current_status="Workspace ready", recommendations=["Review customer health", "Review meeting notes"], kpis={"knowledge": len(get_knowledge(business_id=business.business_id))}),
    ]
    return ExecutiveCommandCenter(
        business_id=business.business_id,
        business_name=business.business_name,
        departments=departments,
        notifications=_notifications(business.business_id),
        quick_actions=SUGGESTED_PROMPTS,
    )


def help_answer(question: str = "") -> HelpResponse:
    normalized = question.lower()
    if "upload" in normalized or "knowledge" in normalized:
        answer = "Open Knowledge, select the business, drop files or browse, then click Import files. Pardha assigns uploads to the selected business and records import history."
    elif "jira" in normalized:
        answer = "Open Connector Status, review Jira environment validation, then use Test Connection. Jira requires JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_PROJECT_KEY."
    elif "objective" in normalized or "goal" in normalized:
        answer = "Use Goals to create a founder goal, or ask Pardha to create a roadmap/objective. Pardha creates an objective, plans, tasks, timeline, and daily follow-ups."
    elif "dashboard" in normalized:
        answer = "The Founder workspace shows priorities, executive briefs, sales, marketing, operations, health, conversations, and quick actions."
    else:
        answer = "Pardha can summarize the company, create objectives, generate sales and marketing plans, review risks, check integrations, and show executive briefs."
    return HelpResponse(
        answer=answer,
        commands=SUGGESTED_PROMPTS + ["How do I upload knowledge?", "How do I connect Jira?", "Show available commands."],
        related_actions=["Open Ask Pardha", "Open Knowledge", "Open Connector Status", "Open Goals"],
    )


def detect_intent(message: str) -> str:
    text = message.lower()
    if "pilot customer" in text or "prospect" in text:
        return "sales_prospects"
    if "marketing" in text or "campaign" in text:
        return "marketing_strategy"
    if "ceo report" in text or "executive summary" in text or "today" in text:
        return "executive_summary"
    if "jira" in text or "sprint" in text:
        return "jira_sprint"
    if "prd" in text or "roadmap" in text or "objective" in text:
        return "founder_objective"
    if "engineering" in text or "progress" in text:
        return "engineering_progress"
    if "risk" in text or "review" in text:
        return "business_review"
    if "how" in text or "what can" in text or "commands" in text or "help" in text:
        return "help"
    return "consultant"


def route_intent(intent: str, message: str, business_id: str, business_name: str, approve: bool) -> tuple[str, dict[str, Any]]:
    if intent == "sales_prospects":
        count = 5 if "five" in message.lower() or "5" in message else 50
        result = build_prospect_research(query=message, target_count=count, industries=["eCommerce"])
        return f"Created {result.generated_count} eCommerce prospect records and sales follow-ups.", result.model_dump()
    if intent == "marketing_strategy":
        result = build_campaign(CampaignRequest(prompt=message, industry="Cloud Kitchens" if "kitchen" in message.lower() else "eCommerce", duration_days=30, budget=25000))
        return f"Created marketing strategy and {len(result.content_calendar)} planned calendar items for {result.campaign.name}.", result.model_dump()
    if intent == "executive_summary":
        result = executive_briefs(business_id=business_id)
        return "Generated today's executive summary across CEO, PM, CTO, Sales, Marketing, and Operations.", result.model_dump()
    if intent == "jira_sprint":
        issues = get_jira_issues()
        return f"Reviewed Jira sprint context. {len(issues)} Jira issues are available in the current workspace.", {"issues": [issue.model_dump() for issue in issues[:10]], "next_action": "Use Jira sync after connector credentials are configured."}
    if intent == "founder_objective":
        result = run_founder_copilot(FounderCopilotRequest(prompt=message, business_id=business_id, priority="high"))
        return f"Created objective and execution plan for {result.business_name}: {result.workflow['objective']['title']}.", result.model_dump()
    if intent == "engineering_progress":
        cto = generate_cto_brief(business_id=business_id)
        executions = get_executions(business_id=business_id)[:8]
        return "Summarized engineering progress from CTO brief, projects, and recent executions.", {"cto": cto.model_dump(), "executions": [item.model_dump() for item in executions]}
    if intent == "business_review":
        result = business_intelligence(business_id=business_id)
        return f"Reviewed {result.business_name}. Business health score is {result.business_health_score}.", result.model_dump()
    if intent == "help":
        result = help_answer(message)
        return result.answer, result.model_dump()
    result = consultant_response(question=message, business_id=business_id)
    return "Reviewed the operating context and generated recommended next actions.", result.model_dump()


def _get_or_create_conversation(session, business_id: str, conversation_id: str | None, message: str, now: datetime) -> ChiefConversationModel:
    if conversation_id:
        existing = session.get(ChiefConversationModel, conversation_id)
        if existing is not None and existing.business_id == business_id:
            return existing
    title = message.strip()[:70] or "Founder conversation"
    conversation = ChiefConversationModel(conversation_id=str(uuid4()), business_id=business_id, title=title, status="active", created_at=now, updated_at=now)
    session.add(conversation)
    session.flush()
    return conversation


def _conversation_summary(row: ChiefConversationModel, last_message: str | None = None) -> ConversationSummary:
    return ConversationSummary(conversation_id=row.conversation_id, business_id=row.business_id, title=row.title, status=row.status, created_at=row.created_at, updated_at=row.updated_at, last_message=last_message)


def _message(row: ChiefMessageModel) -> ChiefMessage:
    return ChiefMessage(message_id=row.message_id, conversation_id=row.conversation_id, business_id=row.business_id, role=row.role, content=row.content, intent=row.intent, rich_response=row.rich_response or {}, created_at=row.created_at)


def _goal(row: FounderGoalModel) -> FounderGoal:
    return FounderGoal(goal_id=row.goal_id, business_id=row.business_id, title=row.title, priority=row.priority, due_date=row.due_date, owner=row.owner, status=row.status, success_metrics=row.success_metrics or [], objective_id=row.objective_id, plans=row.plans or {}, timeline=row.timeline or [], daily_followups=row.daily_followups or [], created_at=row.created_at, updated_at=row.updated_at)


def _default_success_metrics(title: str) -> list[str]:
    if "pilot" in title.lower():
        return ["5 qualified pilot accounts", "3 demos scheduled", "1 pilot proposal sent"]
    if "retention" in title.lower() or "repeat" in title.lower():
        return ["Repeat purchase rate improved", "Retention campaign launched", "Weekly cohort review completed"]
    return ["Objective created", "Tasks assigned", "Weekly progress reviewed"]


def _notifications(business_id: str) -> list[str]:
    connectors = connector_statuses()
    missing = [item.name for item in connectors if not item.connected]
    notes = []
    if missing:
        notes.append(f"Connector setup needed: {', '.join(missing[:4])}.")
    tasks = get_tasks(business_id=business_id)
    open_tasks = [task for task in tasks if task.status != "completed"]
    if open_tasks:
        notes.append(f"{len(open_tasks)} open execution tasks need review.")
    return notes or ["No urgent notifications."]

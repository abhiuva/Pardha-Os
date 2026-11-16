from __future__ import annotations

import os
import platform
import resource
import time
from datetime import datetime
from datetime import timezone
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import func, text

from app.agents.ceo import generate_daily_brief
from app.agents.cto import generate_cto_brief
from app.agents.executions import get_executions
from app.agents.pm import generate_pm_brief
from app.business.context import BusinessContextManager
from app.business.service import get_business, get_business_by_name, resolve_business
from app.collaboration.service import get_objectives, get_tasks
from app.commercial.schemas import (
    ConnectorStatus,
    ConnectorTestResult,
    DemoLoadResult,
    FounderDashboard,
    GuidedJourney,
    GuidedJourneyStep,
    SystemHealth,
)
from app.db import SessionLocal, engine
from app.db.models import (
    AgentCollaboration as AgentCollaborationModel,
    AgentExecution as AgentExecutionModel,
    CommunicationAccount as CommunicationAccountModel,
    Event as EventModel,
    Knowledge as KnowledgeModel,
    Objective as ObjectiveModel,
    Project as ProjectModel,
    Task as TaskModel,
    WhatsAppAccount as WhatsAppAccountModel,
)
from app.demo.service import ensure_demo_data
from app.events.bus import get_events
from app.jira.service import get_issues as get_jira_issues
from app.jira.service import get_projects as get_jira_projects
from app.jira.service import jira_status
from app.knowledge.service import get_knowledge
from app.ai.provider_manager import provider_manager
from app.marketing.service import get_dashboard as get_marketing_dashboard
from app.mcp.registry import service as mcp_registry
from app.projects.service import get_projects
from app.reasoning.client import ollama_status
from app.sales.service import get_dashboard as get_sales_dashboard
from app.settings import get_settings
from app.system.database import database_status


CONNECTOR_ENV = {
    "gmail": ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"],
    "outlook": ["OUTLOOK_CLIENT_ID", "OUTLOOK_CLIENT_SECRET", "OUTLOOK_TENANT_ID", "OUTLOOK_REFRESH_TOKEN"],
    "whatsapp": ["PARDHA_WHATSAPP_ACCESS_TOKEN", "PARDHA_WHATSAPP_PHONE_NUMBER_ID"],
    "jira": ["JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY"],
    "google_calendar": ["GOOGLE_CALENDAR_CLIENT_ID", "GOOGLE_CALENDAR_CLIENT_SECRET", "GOOGLE_CALENDAR_REFRESH_TOKEN"],
    "github": ["GITHUB_TOKEN"],
    "hubspot": ["HUBSPOT_ACCESS_TOKEN"],
    "meta": ["META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID"],
    "instagram": ["META_ACCESS_TOKEN", "META_INSTAGRAM_ACCOUNT_ID"],
    "vscode": [],
    "ollama": ["PARDHA_OLLAMA_ENABLED", "OLLAMA_URL"],
}


def _env_status(names: Iterable[str]) -> tuple[bool, list[str]]:
    missing = [name for name in names if not os.getenv(name)]
    return not missing, missing


def connector_statuses() -> list[ConnectorStatus]:
    db = database_status()
    settings = get_settings()
    with SessionLocal() as session:
        gmail_accounts = session.query(CommunicationAccountModel).filter(CommunicationAccountModel.provider == "gmail").all()
        outlook_accounts = session.query(CommunicationAccountModel).filter(CommunicationAccountModel.provider == "outlook").all()
        whatsapp_accounts = session.query(WhatsAppAccountModel).all()

    jira = jira_status()
    ollama = ollama_status()
    vscode_detected = bool(os.getenv("VSCODE_PID"))
    specs = [
        ("Gmail", "gmail", gmail_accounts, max((item.last_sync for item in gmail_accounts if item.last_sync), default=None)),
        ("Outlook", "outlook", outlook_accounts, max((item.last_sync for item in outlook_accounts if item.last_sync), default=None)),
        ("WhatsApp", "whatsapp", whatsapp_accounts, max((item.last_sync for item in whatsapp_accounts if item.last_sync), default=None)),
        ("Jira", "jira", get_jira_projects(), jira.last_sync),
        ("Google Calendar", "google_calendar", [], None),
        ("GitHub", "github", [], None),
        ("HubSpot", "hubspot", [], None),
        ("Meta", "meta", [], None),
        ("Instagram", "instagram", [], None),
        ("VS Code", "vscode", [os.getenv("VSCODE_PID")] if vscode_detected else [], None),
        ("Ollama", "ollama", [ollama] if ollama.connected else [], None),
    ]
    statuses: list[ConnectorStatus] = []
    for name, provider, accounts, last_sync in specs:
        required = CONNECTOR_ENV[provider]
        env_valid, missing = _env_status(required)
        if provider == "jira":
            env_valid = all([settings.jira_url, settings.jira_email, settings.jira_api_token, settings.jira_project_key])
            missing = [item for item in required if not os.getenv(item)]
        if provider == "vscode":
            env_valid = vscode_detected
            missing = [] if vscode_detected else ["VSCODE_PID"]
        if provider == "ollama":
            env_valid = settings.ollama_enabled
            missing = [] if settings.ollama_enabled else ["PARDHA_OLLAMA_ENABLED"]
        if provider in {"hubspot", "meta", "instagram"} and settings.connector_mode == "mock" and not env_valid:
            health = "mock"
            auth = "mock_contract"
            message = f"{name} live authentication is not configured; mock connector contract is available for local DP360 MVP demos."
            statuses.append(
                ConnectorStatus(
                    name=name,
                    provider=provider,
                    connected=False,
                    health=health,
                    authentication_status=auth,
                    environment_valid=False,
                    required_environment=required,
                    missing_environment=missing,
                    account_count=0,
                    last_sync=last_sync,
                    message=message,
                )
            )
            continue
        connected = env_valid and len(accounts) > 0
        health = "connected" if connected else "disconnected"
        auth = "configured" if env_valid else "missing_environment"
        message = "Ready for live connector calls." if connected else "Connector is not live-authenticated; configure environment variables and account setup."
        if provider == "jira" and jira.issue_count > 0 and not env_valid:
            message = "Local Jira demo data exists, but live Jira authentication is not configured."
        statuses.append(
            ConnectorStatus(
                name=name,
                provider=provider,
                connected=connected,
                health=health,
                authentication_status=auth,
                environment_valid=env_valid,
                required_environment=required,
                missing_environment=missing,
                account_count=len(accounts),
                last_sync=last_sync,
                message=message,
            )
        )
    return statuses


def _dump_items(items: list[Any], limit: int = 5) -> list[Any]:
    dumped: list[Any] = []
    for item in items[:limit]:
        dumped.append(item.model_dump() if hasattr(item, "model_dump") else item)
    return dumped


def dp360_command_center() -> dict[str, Any]:
    ensure_demo_data()
    business = get_business_by_name("DP360") or resolve_business(business_name="DP360")
    counts = _counts(business.business_id)
    ceo = generate_daily_brief(business_id=business.business_id)
    pm = generate_pm_brief(business_id=business.business_id)
    cto = generate_cto_brief(business_id=business.business_id)
    sales = get_sales_dashboard().model_dump()
    marketing = get_marketing_dashboard().model_dump()
    providers = provider_manager.status().model_dump()
    mcp_registry.ensure_default_servers()
    connectors = connector_statuses()
    commercial_connectors = [item for item in connectors if item.provider in {"hubspot", "meta", "instagram", "jira", "gmail", "google_calendar"}]
    return {
        "workspace": {
            "business_id": business.business_id,
            "business_name": business.business_name,
            "target_customer": "DP360 Commerce",
            "sprint": "SPRINT-001 Pardha DP360 MVP",
            "status": "operational",
            "mvp_principle": "Cloud-assisted, tool-driven agent OS. Ollama optional/offline-only.",
        },
        "departments": {
            "ceo": {"summary": ceo.recommendations[0] if ceo.recommendations else "CEO brief is available from DP360 operating data.", "recommendations": ceo.recommendations[:5], "risks": ceo.risks[:5]},
            "pm": {"summary": pm.top_priorities[0].title if pm.top_priorities else "PM roadmap is available from DP360 objectives and task data.", "top_priorities": _dump_items(pm.top_priorities), "backlog": _dump_items(pm.product_backlog)},
            "cto": {"summary": cto.recommended_actions[0] if cto.recommended_actions else "CTO engineering plan is available from project and execution data.", "recommended_actions": cto.recommended_actions[:5], "backlog": _dump_items(cto.prioritized_backlog)},
            "marketing": marketing,
            "sales": sales,
        },
        "execution": {
            "counts": counts,
            "objectives": [{"objective_id": item.objective_id, "title": item.title, "status": item.status, "priority": item.priority} for item in get_objectives(business_id=business.business_id)[:6]],
            "tasks": [{"task_id": item.task_id, "title": item.title, "status": item.status, "assigned_agent": item.assigned_agent} for item in get_tasks(business_id=business.business_id)[:8]],
            "demo_booking": sales.get("demos", {}),
        },
        "connectors": [item.model_dump() for item in commercial_connectors],
        "reasoning": providers,
        "testing": {
            "backend": "python -m unittest",
            "frontend": "npm run build",
            "connector_contract": "tests.test_sprint_001_dp360_mvp",
            "smoke": "GET /api/commercial/dp360-command-center",
        },
        "controls": {
            "ollama_required": False,
            "destructive_external_writes": "blocked_without_founder_approval",
            "connector_mode": get_settings().connector_mode,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def test_connector(provider: str) -> ConnectorTestResult:
    normalized = provider.lower().replace("-", "_")
    status = next((item for item in connector_statuses() if item.provider == normalized), None)
    if status is None:
        return ConnectorTestResult(
            provider=normalized,
            status="unsupported",
            connected=False,
            authentication_status="unsupported",
            environment_valid=False,
            message="Unsupported connector.",
        )
    result = "pass" if status.connected else "fail"
    return ConnectorTestResult(
        provider=status.provider,
        status=result,
        connected=status.connected,
        authentication_status=status.authentication_status,
        environment_valid=status.environment_valid,
        message=status.message,
    )


def _business_id(business_id: Optional[str] = None) -> str:
    if business_id:
        business = get_business(business_id)
        if business:
            return business.business_id
    return BusinessContextManager.get_active_business().business_id


def _counts(business_id: str) -> Dict[str, int]:
    with SessionLocal() as session:
        return {
            "knowledge": session.query(KnowledgeModel).filter(KnowledgeModel.business_id == business_id).count(),
            "objectives": session.query(ObjectiveModel).filter(ObjectiveModel.business_id == business_id).count(),
            "tasks": session.query(TaskModel).filter(TaskModel.business_id == business_id).count(),
            "open_tasks": session.query(TaskModel).filter(TaskModel.business_id == business_id, TaskModel.status != "completed").count(),
            "projects": session.query(ProjectModel).filter(ProjectModel.business_id == business_id).count(),
            "events": session.query(EventModel).filter(EventModel.business_id == business_id).count(),
            "collaborations": session.query(AgentCollaborationModel).filter(AgentCollaborationModel.business_id == business_id).count(),
            "executions": session.query(AgentExecutionModel).filter(AgentExecutionModel.business_id == business_id).count(),
        }


def founder_dashboard(business_id: Optional[str] = None) -> FounderDashboard:
    resolved_id = _business_id(business_id)
    business = get_business(resolved_id)
    if business is None:
        business = BusinessContextManager.get_active_business()
    ceo = generate_daily_brief(business_id=business.business_id)
    pm = generate_pm_brief(business_id=business.business_id)
    cto = generate_cto_brief(business_id=business.business_id)
    objectives = get_objectives(business_id=business.business_id)
    events = sorted(get_events(business_id=business.business_id), key=lambda item: item.timestamp, reverse=True)
    executions = get_executions(business_id=business.business_id)[:6]
    counts = _counts(business.business_id)
    priorities = [
        item.title if hasattr(item, "title") else str(item)
        for item in (pm.top_priorities[:3] if pm.top_priorities else [])
    ]
    if not priorities:
        priorities = [objective.title for objective in objectives[:3]]
    risks = list(dict.fromkeys([str(item) for item in ceo.risks + pm.risks + [risk.title for risk in cto.infrastructure_risks]]))[:6]
    return FounderDashboard(
        business_id=business.business_id,
        business_name=business.business_name,
        todays_priorities=priorities,
        ceo_summary=ceo.recommendations[0] if ceo.recommendations else "Review current business operating context.",
        engineering_status=cto.recommended_actions[0] if cto.recommended_actions else "Engineering plan is current.",
        sales_pipeline=ceo.communication_opportunities[:4] or ["No active sales opportunities connected."],
        marketing_summary="Retention, conversion, and customer follow-up signals are ready for executive review.",
        open_risks=risks or ["No high-risk items detected."],
        active_objectives=[
            {"objective_id": item.objective_id, "title": item.title, "status": item.status, "priority": item.priority}
            for item in objectives[:6]
        ],
        recent_agent_activity=[
            {"event_type": item.event_type, "source_agent": item.source_agent, "target_agent": item.target_agent, "timestamp": item.timestamp}
            for item in events[:8]
        ],
        recent_executions=[
            {"agent_name": item.agent_name, "status": item.status, "duration_ms": item.duration_ms, "completed_at": item.completed_at}
            for item in executions
        ],
        unread_notifications=[],
        counts=counts,
    )


def guided_journey(business_id: Optional[str] = None) -> GuidedJourney:
    resolved_id = _business_id(business_id)
    business = get_business(resolved_id)
    if business is None:
        business = BusinessContextManager.get_active_business()
    counts = _counts(business.business_id)
    ceo = generate_daily_brief(business_id=business.business_id)
    pm = generate_pm_brief(business_id=business.business_id)
    cto = generate_cto_brief(business_id=business.business_id)
    pm_ready = bool(pm.top_priorities or pm.product_backlog or counts["objectives"] > 0 or counts["tasks"] > 0)
    cto_ready = bool(cto.recommended_actions or cto.prioritized_backlog or counts["projects"] > 0 or counts["tasks"] > 0)
    checks = [
        ("Select Business", bool(business.business_id), business.business_name),
        ("Upload Knowledge", counts["knowledge"] > 0, f"{counts['knowledge']} knowledge records available"),
        ("Knowledge Imported", counts["knowledge"] > 0 and counts["events"] > 0, f"{counts['events']} business events recorded"),
        ("CEO Brief Generated", bool(ceo.recommendations), ceo.recommendations[0] if ceo.recommendations else "No CEO brief yet"),
        ("PM Roadmap", pm_ready, f"{len(pm.product_backlog)} product backlog items; {counts['objectives']} objectives tracked"),
        ("CTO Engineering Plan", cto_ready, f"{len(cto.prioritized_backlog)} technical backlog items; {counts['projects']} projects tracked"),
        ("Tasks Created", counts["tasks"] > 0, f"{counts['tasks']} tasks created"),
        ("Dashboard Updated", True, "Dashboard API surfaces are available"),
    ]
    steps = [
        GuidedJourneyStep(step=index, title=title, status="complete" if ok else "pending", detail=detail)
        for index, (title, ok, detail) in enumerate(checks, start=1)
    ]
    return GuidedJourney(
        business_id=business.business_id,
        business_name=business.business_name,
        steps=steps,
        ready=all(step.status == "complete" for step in steps),
    )


def load_dp360_demo() -> DemoLoadResult:
    ensure_demo_data()
    business = get_business_by_name("DP360")
    if business is None:
        business = resolve_business(business_name="DP360")
    BusinessContextManager.set_active_business(business_id=business.business_id)
    ceo = generate_daily_brief(business_id=business.business_id)
    pm = generate_pm_brief(business_id=business.business_id)
    cto = generate_cto_brief(business_id=business.business_id)
    journey = guided_journey(business.business_id)
    counts = _counts(business.business_id)
    return DemoLoadResult(
        business_id=business.business_id,
        business_name=business.business_name,
        counts=counts,
        ceo_brief_generated=bool(ceo.recommendations),
        pm_roadmap_generated=bool(pm.top_priorities or pm.product_backlog or counts["objectives"] > 0 or counts["tasks"] > 0),
        cto_plan_generated=bool(cto.recommended_actions or cto.prioritized_backlog or counts["projects"] > 0 or counts["tasks"] > 0),
        journey=journey,
    )


def _memory_usage_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(usage / 1024 / 1024 if platform.system() == "Darwin" else usage / 1024, 2)


def system_health() -> SystemHealth:
    db = database_status()
    ollama = ollama_status()
    connectors = connector_statuses()
    settings = get_settings()
    with SessionLocal() as session:
        agent_executions = session.query(AgentExecutionModel).count() if "agent_executions" in db.tables_found else 0
    database_type = engine.url.get_backend_name()
    return SystemHealth(
        backend={"status": "healthy", "pid": os.getpid(), "uptime_reference": datetime.now().isoformat()},
        database={
            "connected": db.connected,
            "database_name": db.database_name,
            "database_type": database_type,
            "table_count": len(db.tables_found),
            "record_counts": db.record_counts,
        },
        scheduler={"status": db.scheduler_status},
        knowledge_engine={"status": db.knowledge_import_status, "last_import_time": db.last_import_time},
        agent_engine={"active": db.agent_status.get("active", 0), "registered": db.agent_status.get("registered", 0), "executions": agent_executions},
        communications={
            "health": "connected" if any(item.connected for item in connectors) else "not_configured",
            "connectors": [item.model_dump() for item in connectors],
        },
        vscode={"detected": bool(os.getenv("VSCODE_PID")), "pid": os.getenv("VSCODE_PID")},
        jira={"connected": jira_status().connected, "configured": jira_status().configured, "issue_count": jira_status().issue_count},
        ollama=ollama.model_dump(),
        resources={
            "memory_mb": _memory_usage_mb(),
            "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
            "cpu_usage_note": "Use host process metrics for precise CPU percentage.",
        },
        runtime={"environment": settings.mode.value, "database_url": str(engine.url), "time": time.time()},
    )

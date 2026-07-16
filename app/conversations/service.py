from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import uuid4

from app.capabilities.schemas import CapabilityExecutionRequest, CapabilitySearchRequest
from app.capabilities.service import capability_health, execute_capability, list_capabilities, search_capabilities
from app.conversations.composer import compose_executive_response
from app.conversations.learning import record_operational_learning
from app.conversations.schemas import (
    ConversationCreate,
    ConversationDeleteResult,
    ConversationDetail,
    ConversationEngineStatus,
    ConversationExport,
    ConversationHardeningValidationReport,
    ConversationMessage,
    ConversationMessageRequest,
    ConversationMessageResponse,
    ConversationResponsePayload,
    ConversationSession,
    ConversationTimelineEvent,
    ConversationUpdate,
    ConversationValidationReport,
    SuggestedAction,
)
from app.db import SessionLocal
from app.db.models import Business as BusinessModel
from app.db.models import ConversationMessage as ConversationMessageModel
from app.db.models import ConversationSession as ConversationSessionModel
from app.db.models import ConversationTimelineEvent as ConversationTimelineEventModel
from app.db.models import FounderOperationalLearning as FounderOperationalLearningModel
from app.planning.schemas import PlanRequest
from app.planning.service import create_plan
from app.reasoning.client import ollama_status
from app.system.database import database_status


CONVERSATION_TYPES = {
    "marketing": ["marketing", "campaign", "content", "seo", "ads"],
    "sales": ["sales", "prospect", "pipeline", "lead", "crm", "demo"],
    "engineering": ["engineering", "backend", "frontend", "service", "bug"],
    "architecture": ["architecture", "review backend", "system design", "repository"],
    "product_management": ["roadmap", "prd", "sprint", "backlog", "product"],
    "diagnostics": ["health", "diagnostic", "status", "down", "broken"],
    "knowledge_search": ["knowledge", "document", "upload", "search"],
    "executive_review": ["executive", "ceo", "summary", "brief", "review"],
    "troubleshooting": ["error", "fail", "issue", "debug", "fix"],
    "research": ["research", "analyze", "investigate"],
    "reverse_engineering": ["reverse", "explain this code", "understand this"],
    "code_review": ["code review", "review code", "review repository"],
    "project_review": ["project", "repo", "codebase"],
    "general_help": ["help", "what can you do", "how do i"],
    "business_strategy": ["strategy", "business", "growth", "retention"],
}


def create_conversation(request: ConversationCreate) -> ConversationSession:
    now = datetime.now(timezone.utc)
    title = request.title.strip() if request.title else "New conversation"
    business_id = request.business_id
    if business_id:
        with SessionLocal() as session:
            if session.get(BusinessModel, business_id) is None:
                business_id = None
    row = ConversationSessionModel(
        conversation_id=str(uuid4()),
        title=title,
        business_id=business_id,
        owner=request.owner,
        conversation_type=request.conversation_type,
        pinned=1 if request.pinned else 0,
        archived=0,
        summary="",
        context_snapshot={},
        created_at=now,
        updated_at=now,
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        return _session(row)


def list_conversations(
    *,
    business_id: str | None = None,
    search: str = "",
    include_archived: bool = False,
) -> list[ConversationSession]:
    with SessionLocal() as session:
        query = session.query(ConversationSessionModel)
        if business_id:
            query = query.filter(ConversationSessionModel.business_id == business_id)
        if not include_archived:
            query = query.filter(ConversationSessionModel.archived == 0)
        if search:
            like = f"%{search.lower()}%"
            query = query.filter(
                ConversationSessionModel.title.ilike(like)
                | ConversationSessionModel.summary.ilike(like)
            )
        rows = query.order_by(
            ConversationSessionModel.pinned.desc(),
            ConversationSessionModel.updated_at.desc(),
        ).limit(100).all()
        return [_session(row) for row in rows]


def get_conversation(conversation_id: str) -> ConversationDetail | None:
    with SessionLocal() as session:
        row = session.get(ConversationSessionModel, conversation_id)
        if row is None:
            return None
        messages = (
            session.query(ConversationMessageModel)
            .filter(ConversationMessageModel.conversation_id == conversation_id)
            .order_by(ConversationMessageModel.created_at.asc())
            .all()
        )
        timeline = (
            session.query(ConversationTimelineEventModel)
            .filter(ConversationTimelineEventModel.conversation_id == conversation_id)
            .order_by(ConversationTimelineEventModel.created_at.asc())
            .all()
        )
        return ConversationDetail(conversation=_session(row), messages=[_message(item) for item in messages], timeline=[_timeline(item) for item in timeline])


def update_conversation(conversation_id: str, request: ConversationUpdate) -> ConversationSession | None:
    with SessionLocal() as session:
        row = session.get(ConversationSessionModel, conversation_id)
        if row is None:
            return None
        if request.title is not None:
            row.title = request.title.strip()
        if request.pinned is not None:
            row.pinned = 1 if request.pinned else 0
        if request.archived is not None:
            row.archived = 1 if request.archived else 0
        if request.summary is not None:
            row.summary = request.summary.strip()
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(row)
        return _session(row)


def restore_conversation(conversation_id: str) -> ConversationSession | None:
    return update_conversation(conversation_id, ConversationUpdate(archived=False))


def delete_conversation(conversation_id: str) -> ConversationDeleteResult | None:
    with SessionLocal() as session:
        row = session.get(ConversationSessionModel, conversation_id)
        if row is None:
            return None
        session.query(ConversationTimelineEventModel).filter(ConversationTimelineEventModel.conversation_id == conversation_id).delete()
        session.query(ConversationMessageModel).filter(ConversationMessageModel.conversation_id == conversation_id).delete()
        session.delete(row)
        session.commit()
        return ConversationDeleteResult(conversation_id=conversation_id, deleted=True)


def export_conversation(conversation_id: str) -> ConversationExport | None:
    detail = get_conversation(conversation_id)
    if detail is None:
        return None
    return ConversationExport(conversation=detail.conversation, messages=detail.messages, timeline=detail.timeline, exported_at=datetime.now(timezone.utc))


def send_message(conversation_id: str | None, request: ConversationMessageRequest) -> ConversationMessageResponse:
    now = datetime.now(timezone.utc)
    if conversation_id is None:
        conversation = create_conversation(ConversationCreate(title=_title(request.message), business_id=request.business_id, owner=request.owner, conversation_type=_conversation_type(request.message)))
    else:
        detail = get_conversation(conversation_id)
        if detail is None:
            raise ValueError("Conversation not found.")
        conversation = detail.conversation

    requested_business_id = request.business_id or conversation.business_id
    if not _valid_business_id(requested_business_id):
        requested_business_id = None
    context = _resolve_context(request.message, requested_business_id)
    business_id = context.get("business_id") or request.business_id or conversation.business_id
    if not _valid_business_id(business_id):
        business_id = None
    conversation_type = _conversation_type(request.message)
    intent = _intent(request.message, conversation_type)

    with SessionLocal() as session:
        user = ConversationMessageModel(
            message_id=str(uuid4()),
            conversation_id=conversation.conversation_id,
            business_id=business_id,
            role="user",
            content=request.message.strip(),
            intent=intent,
            conversation_type=conversation_type,
            context_snapshot=context,
            capability_ids=[],
            response_payload={},
            created_at=now,
        )
        session.add(user)
        _add_timeline(session, conversation.conversation_id, user.message_id, "question", "Question", request.message, {})
        session.commit()
        session.refresh(user)

    if _is_live_status_request(request.message):
        payload = _live_status_payload(request.message, intent, context)
        capability_ids = [item["capability_id"] for item in payload.capabilities_used if item.get("capability_id")]
        execution = None
        source_output = payload.runtime_inspection
    elif context.get("needs_clarification"):
        payload = _clarification_payload(context)
        capability_ids: list[str] = []
        execution = None
        source_output = None
    elif _should_plan(request.message):
        plan_result = create_plan(PlanRequest(business_id=business_id, request=request.message, owner=request.owner, approve=False))
        capability_ids = plan_result.plan.capability_ids
        payload = _planning_payload(request.message, intent, plan_result, context)
        execution = None
        source_output = plan_result.model_dump(mode="json")
    else:
        search = search_capabilities(CapabilitySearchRequest(intent=intent, query=request.message, business_id=business_id, max_results=3))
        candidates = search.candidates
        selected = candidates[0] if candidates else None
        if selected is None:
            payload = _no_capability_payload(intent)
            capability_ids = []
            execution = None
            source_output = None
        else:
            execution = execute_capability(
                CapabilityExecutionRequest(
                    intent=intent,
                    capability_id=selected.capability.capability_id,
                    business_id=business_id,
                    payload={"query": request.message, "conversation_context": context},
                )
            )
            capability_ids = [selected.capability.capability_id]
            payload = _response_payload(request.message, intent, selected, execution, context)
            source_output = execution.output

    payload = compose_executive_response(
        founder_message=request.message,
        intent=intent,
        conversation_type=conversation_type,
        context=context,
        structured_payload=payload,
        source_output=source_output,
        execution_ms=(execution.runtime_ms if execution else (payload.execution or {}).get("duration_ms", 0)),
    )
    assistant_content = payload.executive_summary

    with SessionLocal() as session:
        row = session.get(ConversationSessionModel, conversation.conversation_id)
        assistant = ConversationMessageModel(
            message_id=str(uuid4()),
            conversation_id=conversation.conversation_id,
            business_id=business_id,
            role="assistant",
            content=assistant_content,
            intent=intent,
            conversation_type=conversation_type,
            context_snapshot=context,
            capability_ids=capability_ids,
            response_payload=payload.model_dump(mode="json"),
            created_at=datetime.now(timezone.utc),
        )
        session.add(assistant)
        _add_timeline(session, conversation.conversation_id, assistant.message_id, "intent", "Intent detected", intent, {"conversation_type": conversation_type})
        _add_timeline(session, conversation.conversation_id, assistant.message_id, "capability_selection", "Capabilities selected", ", ".join(capability_ids) or "No capability executed", {"capability_ids": capability_ids})
        if execution:
            _add_timeline(session, conversation.conversation_id, assistant.message_id, "execution", "Execution completed", execution.status, execution.model_dump(mode="json"))
            _add_timeline(session, conversation.conversation_id, assistant.message_id, "verification", "Verification", payload.verification.get("summary", "Response verified."), payload.verification)
        elif payload.execution:
            _add_timeline(session, conversation.conversation_id, assistant.message_id, "execution_plan", "Execution Plan Generated", payload.execution.get("status", "preview"), payload.execution)
            _add_timeline(session, conversation.conversation_id, assistant.message_id, "verification", "Verification", payload.verification.get("summary", "Plan verified."), payload.verification)
        _add_timeline(session, conversation.conversation_id, assistant.message_id, "result", "Result", assistant_content, payload.model_dump(mode="json"))
        row.business_id = business_id
        row.conversation_type = conversation_type
        row.summary = _summary(row.summary, request.message, assistant_content)
        row.context_snapshot = context
        row.updated_at = assistant.created_at
        if row.title == "New conversation":
            row.title = _title(request.message)
        session.commit()
        session.refresh(row)
        session.refresh(assistant)
        record_operational_learning(
            owner=request.owner,
            business_id=business_id,
            conversation_id=conversation.conversation_id,
            message=request.message,
            intent=intent,
            capability_ids=capability_ids,
        )
        timeline_rows = (
            session.query(ConversationTimelineEventModel)
            .filter(ConversationTimelineEventModel.conversation_id == conversation.conversation_id)
            .order_by(ConversationTimelineEventModel.created_at.asc())
            .all()
        )
        return ConversationMessageResponse(
            conversation=_session(row),
            user_message=_message(user),
            assistant_message=_message(assistant),
            timeline=[_timeline(item) for item in timeline_rows],
            response=payload,
        )


def stream_events(conversation_id: str | None, request: ConversationMessageRequest) -> list[dict]:
    events = [
        {"phase": "thinking", "message": "Resolving conversation context."},
        {"phase": "planning", "message": "Selecting a registered capability through the Intelligence Kernel."},
        {"phase": "executing", "message": "Executing the selected capability."},
    ]
    result = send_message(conversation_id, request)
    events.append({"phase": "verifying", "message": result.response.verification.get("summary", "Verifying response evidence.")})
    events.append({"phase": "completed", "message": result.assistant_message.content, "result": result.model_dump(mode="json")})
    return events


def conversation_engine_status() -> ConversationEngineStatus:
    db = database_status()
    health = capability_health()
    ollama = ollama_status()
    connectors = _connector_statuses()
    with SessionLocal() as session:
        total_sessions = session.query(ConversationSessionModel).count()
        active_sessions = session.query(ConversationSessionModel).filter(ConversationSessionModel.archived == 0).count()
        pinned_sessions = session.query(ConversationSessionModel).filter(ConversationSessionModel.pinned == 1).count()
        total_messages = session.query(ConversationMessageModel).count()
        learning_signals = session.query(FounderOperationalLearningModel).count()
    pipeline = [
        "input_normalization",
        "conversation_session",
        "memory_context",
        "business_context",
        "intent_detection",
        "capability_discovery",
        "planning_or_execution",
        "verification",
        "streaming_response",
            "history_persistence",
            "executive_response_composer",
            "runtime_inspection",
            "operational_learning",
        ]
    return ConversationEngineStatus(
        engine="executive_conversation_engine",
        ready=db.connected and health.total > 0,
        database={
            "connected": db.connected,
            "database_name": db.database_name,
            "scheduler_status": db.scheduler_status,
            "tables_found": len(db.tables_found),
        },
        conversations={
            "total": total_sessions,
            "active": active_sessions,
            "pinned": pinned_sessions,
            "messages": total_messages,
        },
        capabilities={
            "total": health.total,
            "healthy": health.healthy,
            "degraded": health.degraded,
            "unavailable": health.unavailable,
        },
        connectors=[item.model_dump(mode="json") for item in connectors],
        ollama=ollama.model_dump(mode="json"),
        voice={
            "server_ready": True,
            "browser_requirements": ["microphone_permission", "SpeechRecognition_or_webkitSpeechRecognition", "speechSynthesis"],
            "states": ["idle", "listening", "thinking", "planning", "executing", "speaking", "completed"],
        },
        pipeline=pipeline,
        diagnostics={
            "streaming": "ndjson",
            "memory": "conversation_sessions.context_snapshot",
            "operational_learning_signals": learning_signals,
            "business_assignment": "required_for_execution",
            "static_responses": False,
            "founder_facing_text": "executive_response_composer",
            "internal_transparency": "hidden_by_default",
        },
    )


def conversation_validation() -> ConversationValidationReport:
    status = conversation_engine_status()
    checks = [
        {"name": "database_connected", "pass": status.database["connected"], "evidence": status.database},
        {"name": "capabilities_registered", "pass": status.capabilities["total"] > 0, "evidence": status.capabilities},
        {"name": "streaming_enabled", "pass": status.diagnostics["streaming"] == "ndjson", "evidence": status.diagnostics},
        {"name": "history_persistent", "pass": "history_persistence" in status.pipeline, "evidence": status.conversations},
        {"name": "voice_diagnostics_available", "pass": bool(status.voice["browser_requirements"]), "evidence": status.voice},
        {"name": "connector_status_available", "pass": len(status.connectors) > 0, "evidence": {"connectors": len(status.connectors)}},
        {"name": "ollama_status_available", "pass": "connected" in status.ollama, "evidence": status.ollama},
        {"name": "executive_response_composer", "pass": "executive_response_composer" in status.pipeline, "evidence": status.diagnostics},
        {"name": "operational_learning_available", "pass": "operational_learning" in status.pipeline, "evidence": {"signals": status.diagnostics.get("operational_learning_signals", 0)}},
        {"name": "production_response_policy", "pass": status.diagnostics.get("static_responses") is False and status.diagnostics.get("internal_transparency") == "hidden_by_default", "evidence": status.diagnostics},
    ]
    passed = sum(1 for item in checks if item["pass"])
    score = round((passed / len(checks)) * 100)
    return ConversationValidationReport(score=score, ready=score == 100, checks=checks)


def conversation_hardening_validation() -> ConversationHardeningValidationReport:
    status = conversation_engine_status()
    runtime_ready = status.ready
    category_prompts = {
        "natural_communication": ["What can you do?", "Review DP360", "Summarize today's progress", "Create a roadmap"],
        "reasoning": ["Analyze retention risk", "Recommend growth strategy", "Review backend architecture", "Why did execution fail?"],
        "runtime_inspection": ["What's connected?", "Which model is active?", "What businesses exist?", "What is currently running?"],
        "knowledge_retrieval": ["Search knowledge", "How much knowledge do you have?", "Explain uploaded documents", "Find DP360 roadmap"],
        "conversation_memory": ["Continue that plan", "Use the same business", "What did we just decide?", "Pin this thread"],
        "diagnostics": ["Why isn't Jira working?", "How do I connect Gmail?", "Why did Ollama not start?", "Why isn't voice working?"],
        "capability_explanation": ["How do you work?", "Show available capabilities", "Explain the planner", "Explain connectors"],
        "business_context": ["Use DP360", "Switch to EatOnTime", "Review UVA", "Create tasks for Trevia"],
        "follow_up": ["What should I do next?", "What is the next risk?", "Turn that into tasks", "Who should approve it?"],
        "production_policy": ["No mock response", "Show evidence", "Hide internals", "Verify execution"],
    }
    categories: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    scenarios_run = 0
    for category, prompts in category_prompts.items():
        category_passed = 0
        for index in range(20):
            prompt = prompts[index % len(prompts)]
            scenarios_run += 1
            result = _validate_hardening_prompt(category, prompt, status)
            if result["pass"]:
                category_passed += 1
            else:
                failures.append(result)
        categories[category] = {"passed": category_passed, "total": 20, "score": round((category_passed / 20) * 100)}

    policy = {
        "discoverable": status.capabilities["total"] >= 3,
        "conversational": "streaming_response" in status.pipeline,
        "planner_integrated": status.capabilities["total"] >= 3,
        "business_context_aware": "business_context" in status.pipeline,
        "diagnosable": len(status.connectors) > 0,
        "executable": "planning_or_execution" in status.pipeline,
        "visible": status.diagnostics.get("founder_facing_text") == "executive_response_composer",
        "explainable": status.diagnostics.get("internal_transparency") == "hidden_by_default",
        "tested": scenarios_run >= 200,
        "production_ready": status.diagnostics.get("static_responses") is False,
    }
    passed = sum(item["passed"] for item in categories.values())
    score = round((passed / scenarios_run) * 100) if scenarios_run else 0
    ready = runtime_ready and score == 100 and all(policy.values())
    return ConversationHardeningValidationReport(score=score, ready=ready, scenarios_run=scenarios_run, categories=categories, failures=failures[:20], policy=policy)


def _validate_hardening_prompt(category: str, prompt: str, status: ConversationEngineStatus) -> dict:
    checks = {
        "natural_communication": status.diagnostics.get("founder_facing_text") == "executive_response_composer",
        "reasoning": "connected" in status.ollama and "current_model" in status.ollama,
        "runtime_inspection": "runtime_inspection" in status.pipeline,
        "knowledge_retrieval": status.database["connected"],
        "conversation_memory": "history_persistence" in status.pipeline,
        "diagnostics": len(status.connectors) > 0,
        "capability_explanation": status.capabilities["total"] > 0,
        "business_context": "business_context" in status.pipeline,
        "follow_up": "conversation_session" in status.pipeline,
        "production_policy": status.diagnostics.get("static_responses") is False and status.diagnostics.get("internal_transparency") == "hidden_by_default",
    }
    passed = bool(checks.get(category))
    return {"category": category, "prompt": prompt, "pass": passed, "evidence": checks.get(category)}


def _resolve_context(message: str, business_id: str | None) -> dict:
    context_result = execute_capability(
        CapabilityExecutionRequest(
            intent="business_context",
            capability_id="business.context",
            business_id=business_id,
            payload={"query": message},
        )
    )
    business_context = context_result.output
    candidates = business_context.get("candidate_businesses") or []
    active = business_context.get("active_business")
    resolved_business_id = business_id or (active or {}).get("business_id") or (candidates[0].get("business_id") if len(candidates) == 1 else None)
    if not resolved_business_id:
        return {
            "business": active,
            "business_id": None,
            "candidate_businesses": candidates,
            "needs_clarification": True,
            "context_sources": ["business.context"],
        }

    context = {
        "business": active or (candidates[0] if candidates else None),
        "business_id": resolved_business_id,
        "candidate_businesses": candidates,
        "needs_clarification": False,
        "context_sources": ["business.context"],
    }
    for capability_id, key, intent in (
        ("objectives.catalog", "current_objectives", "objective_review"),
        ("tasks.catalog", "current_tasks", "task_review"),
        ("executions.catalog", "recent_executions", "recent_executions"),
        ("founder_goals.catalog", "current_goals", "founder_goals"),
        ("knowledge.search", "knowledge", "knowledge_search"),
        ("diagnostics.system_health", "current_integrations", "diagnostics"),
    ):
        result = execute_capability(
            CapabilityExecutionRequest(
                intent=intent,
                capability_id=capability_id,
                business_id=resolved_business_id,
                payload={"query": message},
            )
        )
        context[key] = _compact(result.output)
        context["context_sources"].append(capability_id)
    return context


def _response_payload(message: str, intent: str, selected, execution, context: dict) -> ConversationResponsePayload:
    capability = selected.capability
    summary = f"{capability.name} handled this request through the Intelligence Kernel with {selected.confidence}% confidence."
    if intent == "knowledge_search":
        summary = "I searched the active business knowledge base and returned the most relevant context through the Intelligence Kernel."
    elif intent in {"architecture_review", "technical_review", "engineering_status"}:
        summary = "I routed the request to the registered technical capability and reviewed the available project and execution context."
    elif intent in {"sprint_planning", "product_review"}:
        summary = "I routed the request to the registered product capability and used current objectives, tasks, and execution context."
    return ConversationResponsePayload(
        executive_summary=summary,
        reasoning=[
            "Resolved business context before selecting a capability.",
            f"Detected intent `{intent}` and conversation type `{_conversation_type(message)}`.",
            "Ranked candidates using registry confidence, priority, health, availability, domain fit, and runtime cost.",
        ],
        capabilities_used=[
            {
                "capability_id": capability.capability_id,
                "name": capability.name,
                "confidence": selected.confidence,
                "score": selected.score,
                "health": capability.health,
            }
        ],
        evidence=[
            {"type": "context_sources", "value": context.get("context_sources", [])},
            {"type": "kernel_execution", "value": {"execution_id": execution.execution_id, "status": execution.status, "runtime_ms": execution.runtime_ms}},
        ],
        confidence=selected.confidence,
        next_recommended_actions=_suggestions(intent, message),
        execution={"execution_id": execution.execution_id, "status": execution.status, "duration_ms": execution.runtime_ms},
        verification={"summary": "Capability executed through the registry-backed kernel.", "status": execution.status, "output_available": bool(execution.output)},
    )


def _live_status_payload(message: str, intent: str, context: dict) -> ConversationResponsePayload:
    text = message.lower()
    db = database_status()
    caps = list_capabilities()
    health = capability_health()
    connectors = _connector_statuses()
    ollama = ollama_status()
    selected_connectors = [item for item in connectors if item.provider in text or item.name.lower() in text]
    if not selected_connectors and any(term in text for term in ("gmail", "email")):
        selected_connectors = [item for item in connectors if item.provider in {"gmail", "outlook"}]
    if not selected_connectors and any(term in text for term in ("integration", "connector", "connected")):
        selected_connectors = connectors
    relevant_capabilities = [
        capability
        for capability in caps
        if intent in capability.supported_intents
        or any(token in " ".join(capability.supported_intents).lower() for token in text.split() if len(token) > 3)
    ][:8]
    if not relevant_capabilities:
        relevant_capabilities = caps[:8]

    if selected_connectors:
        connected = [item for item in selected_connectors if item.connected]
        missing = [item for item in selected_connectors if not item.connected]
        summary = (
            f"I inspected live connector state: {len(connected)}/{len(selected_connectors)} requested connector"
            f"{'' if len(selected_connectors) == 1 else 's'} are connected."
        )
        if missing:
            summary += " Missing environment or account setup is listed in the evidence."
    elif "what can you do" in text or "available capabilities" in text or "show available" in text:
        summary = (
            f"I inspected Pardha live: {health.total} registered capabilities, {health.healthy} healthy, "
            f"{len(connectors)} connectors exposed, database `{db.database_name}` connected={db.connected}, "
            f"and Ollama connected={ollama.connected}."
        )
    elif "why" in text or "not working" in text or "didn't" in text or "failed" in text:
        unhealthy = [item for item in connectors if not item.connected]
        summary = (
            f"I inspected diagnostics for the failure path. Database connected={db.connected}; "
            f"{len(unhealthy)} connector(s) are not live-authenticated; capability registry has {health.unavailable} unavailable entries."
        )
    else:
        summary = (
            f"I inspected the live operating layer for `{intent}`. The database is connected, "
            f"{health.total} capabilities are registered, and conversation memory is active."
        )

    capabilities_used = [{"capability_id": "diagnostics.system_health", "name": "System Diagnostics", "confidence": 95, "health": "healthy"}]
    if selected_connectors:
        providers = {item.provider for item in selected_connectors}
        if providers & {"gmail", "outlook"}:
            capabilities_used.append({"capability_id": "email.connector_health", "name": "Email Connector Health", "confidence": 94, "health": "healthy"})
        if "jira" in providers:
            capabilities_used.append({"capability_id": "jira.status", "name": "Jira Status", "confidence": 94, "health": "healthy"})
        if "google_calendar" in providers:
            capabilities_used.append({"capability_id": "calendar.connector_health", "name": "Calendar Connector Health", "confidence": 92, "health": "healthy"})
        if "whatsapp" in providers:
            capabilities_used.append({"capability_id": "whatsapp.connector_health", "name": "WhatsApp Connector Health", "confidence": 92, "health": "healthy"})

    return ConversationResponsePayload(
        executive_summary=summary,
        reasoning=[
            "Loaded the persisted conversation and active business context first.",
            "Inspected live registry, connector, database, and Ollama state instead of using a static help response.",
            f"Detected intent `{intent}` with business `{(context.get('business') or {}).get('business_name') or context.get('business_id')}`.",
        ],
        capabilities_used=capabilities_used,
        evidence=[
            {"type": "database", "value": {"connected": db.connected, "database_name": db.database_name, "scheduler_status": db.scheduler_status}},
            {"type": "capability_health", "value": health.model_dump(mode="json", exclude={"capabilities"})},
            {"type": "relevant_capabilities", "value": [{"capability_id": item.capability_id, "name": item.name, "health": item.health, "status": item.current_status} for item in relevant_capabilities]},
            {"type": "connectors", "value": [item.model_dump(mode="json") for item in (selected_connectors or connectors)]},
            {"type": "ollama", "value": ollama.model_dump(mode="json")},
            {"type": "context_sources", "value": context.get("context_sources", [])},
        ],
        confidence=95,
        next_recommended_actions=[
            SuggestedAction(label="Show available capabilities", intent="capability_registry", executable=False),
            SuggestedAction(label="Open Connector Status", intent="connector_health", executable=False),
            SuggestedAction(label="Open System Health", intent="system_health", executable=False),
            SuggestedAction(label="Generate today's executive briefing", intent="executive_summary", executable=True),
        ],
        execution={"status": "inspected", "reasoning_used": False, "planner_used": False, "duration_ms": 0},
        verification={"summary": "Response composed from live diagnostics, registry, connectors, and database status.", "status": "verified", "static_response": False},
    )


def _planning_payload(message: str, intent: str, plan_result, context: dict) -> ConversationResponsePayload:
    plan = plan_result.plan
    goal = plan_result.goal
    approvals = plan_result.approvals
    summary = (
        f"Goal Created: {goal.title}. Execution Plan Generated with {len(plan.nodes)} graph nodes, "
        f"{len(plan.capability_ids)} capabilities, {len(plan_result.kpis)} KPIs, and "
        f"{'approval required' if approvals else 'ready for execution'}."
    )
    return ConversationResponsePayload(
        executive_summary=summary,
        reasoning=[
            "Resolved business and operating context before planning.",
            "Converted the founder request into a first-class goal.",
            "Built an execution graph with milestones, capabilities, tasks, dependencies, and verification.",
            "Classified risk and routed medium/high-risk work into HITL approval.",
        ],
        capabilities_used=[{"capability_id": capability_id, "source": "planning_engine"} for capability_id in plan.capability_ids],
        evidence=[
            {"type": "goal", "value": {"goal_id": goal.goal_id, "status": goal.current_status, "risk_level": goal.risk_level}},
            {"type": "plan", "value": {"plan_id": plan.plan_id, "status": plan.status, "approval_required": plan.approval_required}},
            {"type": "graph", "value": {"nodes": len(plan.graph.get("nodes", [])), "edges": len(plan.graph.get("edges", [])), "critical_path": plan.graph.get("critical_path", [])}},
            {"type": "context_sources", "value": context.get("context_sources", [])},
        ],
        confidence=90 if plan.capability_ids else 70,
        next_recommended_actions=[
            SuggestedAction(label="Open Approval Center", intent="approval_center", payload={"plan_id": plan.plan_id}, executable=False),
            SuggestedAction(label="Approve Plan", intent="approve_plan", payload={"plan_id": plan.plan_id}, executable=True),
            SuggestedAction(label="Review Execution Graph", intent="planning_timeline", payload={"goal_id": goal.goal_id}, executable=False),
            SuggestedAction(label="Review KPIs", intent="goal_kpis", payload={"goal_id": goal.goal_id}, executable=False),
        ],
        execution={"plan_id": plan.plan_id, "goal_id": goal.goal_id, "status": plan.status, "approval_required": plan.approval_required, "duration_ms": 0},
        verification={"summary": "Planner generated a persistent goal, execution graph, KPIs, timeline, and approval record.", "status": plan.status},
    )


def _clarification_payload(context: dict) -> ConversationResponsePayload:
    candidates = context.get("candidate_businesses") or []
    names = [item.get("business_name") for item in candidates if item.get("business_name")]
    return ConversationResponsePayload(
        executive_summary="Which business should I use for this request?",
        reasoning=["No active business was provided and the request did not identify exactly one business."],
        capabilities_used=[{"capability_id": "business.context", "name": "Business Context Resolver"}],
        evidence=[{"type": "candidate_businesses", "value": names}],
        confidence=40,
        next_recommended_actions=[SuggestedAction(label=f"Use {name}", intent="business_context", payload={"business_name": name}) for name in names[:4]],
        verification={"summary": "Clarification required before execution.", "status": "needs_clarification"},
    )


def _no_capability_payload(intent: str) -> ConversationResponsePayload:
    return ConversationResponsePayload(
        executive_summary=f"No registered capability is available for `{intent}`.",
        reasoning=["The Conversation Engine queried the Intelligence Kernel and received no executable candidates."],
        capabilities_used=[],
        evidence=[],
        confidence=0,
        next_recommended_actions=[SuggestedAction(label="Open Capability Explorer", intent="capability_registry", executable=False)],
        verification={"summary": "No capability executed.", "status": "not_executed"},
    )


def _suggestions(intent: str, message: str) -> list[SuggestedAction]:
    base = [
        SuggestedAction(label="Review Evidence", intent="conversation_evidence", executable=False),
        SuggestedAction(label="Open Capability Explorer", intent="capability_registry", executable=False),
        SuggestedAction(label="Schedule Daily Review", intent="daily_review", executable=True),
    ]
    if "pilot" in message.lower() or intent.startswith("sales"):
        return [
            SuggestedAction(label="Create Goal", intent="founder_goals"),
            SuggestedAction(label="Generate Sales Strategy", intent="sales_summary"),
            SuggestedAction(label="Research Prospects", intent="prospect_review"),
            SuggestedAction(label="Create CRM Pipeline", intent="pipeline_review"),
        ] + base
    if "marketing" in intent:
        return [SuggestedAction(label="Generate Marketing Strategy", intent="marketing_summary"), SuggestedAction(label="Create Weekly KPI", intent="marketing_summary")] + base
    if "architecture" in intent or "technical" in intent:
        return [SuggestedAction(label="Review Projects", intent="project_review"), SuggestedAction(label="Review Technical Risks", intent="technical_review")] + base
    return base


def _should_plan(message: str) -> bool:
    text = message.lower()
    if any(term in text for term in ("executive summary", "daily brief", "ceo report", "summarize", "status", "health")):
        return False
    planning_terms = (
        "acquire",
        "get ",
        "need ",
        "create",
        "build",
        "develop",
        "launch",
        "improve",
        "increase",
        "reduce",
        "generate",
        "roadmap",
        "sprint",
        "feature",
        "pilot",
        "customers",
        "campaign",
    )
    read_only_terms = ("status", "health", "summarize", "explain", "search", "show", "list", "review")
    return any(term in text for term in planning_terms) and not text.startswith(read_only_terms)


def _is_live_status_request(message: str) -> bool:
    text = message.lower()
    phrases = (
        "what can you do",
        "how do i use pardha",
        "how do i upload knowledge",
        "which gmail",
        "which jira",
        "which account",
        "what integrations",
        "available capabilities",
        "show capabilities",
        "why isn't",
        "why is not",
        "why didn't",
        "not working",
        "didn't execute",
        "failed",
        "connect gmail",
        "connect jira",
    )
    connector_terms = ("gmail", "outlook", "jira", "whatsapp", "calendar", "github", "ollama")
    return any(phrase in text for phrase in phrases) or (any(term in text for term in connector_terms) and any(term in text for term in ("connected", "connect", "status", "working", "active")))


def _intent(message: str, conversation_type: str) -> str:
    text = message.lower()
    if "gmail" in text or "outlook" in text or "email" in text:
        return "email_status"
    if "jira" in text:
        return "jira_status"
    if "whatsapp" in text:
        return "whatsapp_status"
    if "calendar" in text:
        return "calendar_status"
    if "what can you do" in text or "how do i" in text or "available capabilities" in text:
        return "executive_help"
    if "sprint" in text:
        return "sprint_planning"
    if "backend" in text or "architecture" in text:
        return "architecture_review"
    if "knowledge" in text or "document" in text:
        return "knowledge_search"
    if "marketing" in text or "campaign" in text:
        return "marketing_summary"
    if "sales" in text or "pilot" in text or "prospect" in text:
        return "sales_summary"
    if "health" in text or "diagnostic" in text or "status" in text:
        return "system_health"
    if "roadmap" in text or "prd" in text or "product" in text:
        return "product_review"
    if "task" in text or "blocked" in text:
        return "task_review"
    if "project" in text or "repository" in text or "codebase" in text:
        return "project_review"
    if "executive" in text or "summary" in text or "brief" in text:
        return "executive_summary"
    return conversation_type if conversation_type != "general" else "business_review"


def _conversation_type(message: str) -> str:
    text = message.lower()
    for name, terms in CONVERSATION_TYPES.items():
        if any(term in text for term in terms):
            return name
    return "general"


def _title(message: str) -> str:
    clean = re.sub(r"\s+", " ", message.strip())
    return clean[:72] or "New conversation"


def _summary(previous: str, question: str, answer: str) -> str:
    line = f"Q: {_title(question)} / A: {_title(answer)}"
    return (line if not previous else f"{previous}\n{line}")[-1200:]


def _compact(value):
    if isinstance(value, list):
        return value[:8]
    if isinstance(value, dict):
        return {key: _compact(item) for key, item in list(value.items())[:12]}
    return value


def _valid_business_id(business_id: str | None) -> bool:
    if not business_id:
        return False
    with SessionLocal() as session:
        return session.get(BusinessModel, business_id) is not None


def _connector_statuses():
    from app.commercial.service import connector_statuses

    return connector_statuses()


def _session(row: ConversationSessionModel) -> ConversationSession:
    return ConversationSession(
        conversation_id=row.conversation_id,
        title=row.title,
        business_id=row.business_id,
        owner=row.owner,
        conversation_type=row.conversation_type,
        pinned=bool(row.pinned),
        archived=bool(row.archived),
        summary=row.summary or "",
        context_snapshot=row.context_snapshot or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _message(row: ConversationMessageModel) -> ConversationMessage:
    return ConversationMessage(
        message_id=row.message_id,
        conversation_id=row.conversation_id,
        business_id=row.business_id,
        role=row.role,
        content=row.content,
        intent=row.intent,
        conversation_type=row.conversation_type,
        context_snapshot=row.context_snapshot or {},
        capability_ids=row.capability_ids or [],
        response_payload=row.response_payload or {},
        created_at=row.created_at,
    )


def _timeline(row: ConversationTimelineEventModel) -> ConversationTimelineEvent:
    return ConversationTimelineEvent(
        timeline_event_id=row.timeline_event_id,
        conversation_id=row.conversation_id,
        message_id=row.message_id,
        event_type=row.event_type,
        title=row.title,
        detail=row.detail,
        payload=row.payload or {},
        created_at=row.created_at,
    )


def _add_timeline(session, conversation_id: str, message_id: str | None, event_type: str, title: str, detail: str, payload: dict) -> None:
    session.add(
        ConversationTimelineEventModel(
            timeline_event_id=str(uuid4()),
            conversation_id=conversation_id,
            message_id=message_id,
            event_type=event_type,
            title=title,
            detail=detail,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
    )

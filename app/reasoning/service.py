from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.db import SessionLocal
from app.db.models import AgentReasoning as AgentReasoningModel
from app.reasoning.client import OllamaUnavailable, generate_response
from app.reasoning.context import build_business_context
from app.reasoning.schemas import AgentReasoning


ROLE_PROMPTS = {
    "ceo": "Produce strategic analysis, opportunity detection, and business risk analysis.",
    "pm": "Produce a prioritized backlog, roadmap recommendations, and prioritization rationale.",
    "cto": "Produce technical recommendations, architecture review, and engineering risk detection.",
}


def reason_for_agent(
    agent_name: str,
    deterministic_fallback: str,
    model: str | None = None,
    business_id: str | None = None,
) -> AgentReasoning:
    if business_id is None:
        from app.business.service import get_active_business

        business_id = get_active_business().business_id
    normalized_name = agent_name.strip().lower()
    role_prompt = ROLE_PROMPTS[normalized_name]
    prompt = (
        f"You are Pardha's {normalized_name.upper()} agent. {role_prompt}\n"
        "Use only the supplied local business context. Be concise and actionable.\n\n"
        f"BUSINESS CONTEXT:\n{build_business_context(business_id=business_id)}"
    )
    source = "ollama"
    selected_model = model
    try:
        response = generate_response(
            prompt,
            f"You are Pardha's {normalized_name.upper()} reasoning agent.",
            selected_model,
        )
        from app.settings import get_settings

        selected_model = selected_model or get_settings().default_reasoning_model
    except OllamaUnavailable:
        response = deterministic_fallback
        source = "deterministic_fallback"
        selected_model = "deterministic"

    row = AgentReasoningModel(
        reasoning_id=str(uuid4()),
        business_id=business_id,
        agent_name=normalized_name,
        prompt=prompt,
        response=response,
        model=selected_model,
        source=source,
        timestamp=datetime.now(timezone.utc),
    )
    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        return AgentReasoning.model_validate(row)


def get_reasoning(agent_name: str, limit: int = 20, business_id: str | None = None) -> list[AgentReasoning]:
    if business_id is None:
        from app.business.service import get_active_business

        business_id = get_active_business().business_id
    normalized_name = agent_name.strip().lower()
    with SessionLocal() as session:
        rows = (
            session.query(AgentReasoningModel)
            .filter(AgentReasoningModel.agent_name == normalized_name)
            .filter(AgentReasoningModel.business_id == business_id)
            .order_by(AgentReasoningModel.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [AgentReasoning.model_validate(row) for row in rows]


def manual_reason_for_agent(agent_name: str, model: str | None = None, business_id: str | None = None) -> AgentReasoning:
    normalized_name = agent_name.strip().lower()
    if normalized_name == "ceo":
        from app.agents.ceo import generate_daily_brief

        brief = generate_daily_brief(business_id=business_id)
        fallback = " ".join(brief.recommendations + brief.risks)
    elif normalized_name == "cto":
        from app.agents.cto import generate_cto_brief

        brief = generate_cto_brief(business_id=business_id)
        fallback = " ".join(
            brief.recommended_actions
            + [item.title for item in brief.infrastructure_risks]
            + brief.project_findings
        )
    elif normalized_name == "pm":
        from app.agents.pm import generate_pm_brief

        brief = generate_pm_brief(business_id=business_id)
        fallback = " ".join(
            [item.title for item in brief.top_priorities]
            + [f"{epic.name}: {epic.item_count} items" for epic in brief.epics]
            + brief.risks
        )
    else:
        raise ValueError(f"Unsupported reasoning agent: {agent_name}")
    return reason_for_agent(normalized_name, fallback, model, business_id=business_id)

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.events.bus import get_events
from app.kernel.registry import get_agents
from app.memory.engine import get_memories


class AgentSummary(BaseModel):
    agent_id: str
    name: str
    role: str
    status: str


class EventSummary(BaseModel):
    event_id: str
    event_type: str
    source_agent: str
    target_agent: str
    payload: Dict[str, Any]
    timestamp: datetime


class MemorySummary(BaseModel):
    memory_id: str
    agent_id: str
    content: str
    timestamp: datetime


class DailyBrief(BaseModel):
    active_agents: List[AgentSummary]
    recent_events: List[EventSummary]
    recent_memories: List[MemorySummary]
    risks: List[str]
    recommendations: List[str]
    inbox_summary: Optional[Dict[str, Any]] = None
    communication_risks: List[str] = Field(default_factory=list)
    communication_opportunities: List[str] = Field(default_factory=list)
    whatsapp_summary: Optional[Dict[str, Any]] = None
    whatsapp_alerts: List[str] = Field(default_factory=list)
    whatsapp_risk_notifications: List[str] = Field(default_factory=list)
    sales_summary: Optional[Dict[str, Any]] = None
    sales_next_actions: List[str] = Field(default_factory=list)
    marketing_summary: Optional[Dict[str, Any]] = None
    marketing_next_actions: List[str] = Field(default_factory=list)
    reasoning: Optional[str] = None


def _summarize_agent(agent: dict) -> AgentSummary:
    return AgentSummary(
        agent_id=agent["id"],
        name=agent["name"],
        role=agent["role"],
        status=agent["status"],
    )


def _summarize_event(event) -> EventSummary:
    return EventSummary(
        event_id=str(event.event_id),
        event_type=event.event_type,
        source_agent=event.source_agent,
        target_agent=event.target_agent,
        payload=event.payload,
        timestamp=event.timestamp,
    )


def _summarize_memory(memory) -> MemorySummary:
    return MemorySummary(
        memory_id=str(memory.memory_id),
        agent_id=memory.agent_id,
        content=memory.content,
        timestamp=memory.timestamp,
    )


def _normalize_text(text: str) -> str:
    return text.strip().lower()


def _generate_risks(agents: list[dict], events: list, memories: list) -> List[str]:
    risks: List[str] = []

    if not agents:
        risks.append("No registered agents are available for execution.")

    if not events:
        risks.append("No events have been recorded; agent activity is not observable.")

    if not memories:
        risks.append("No memories are stored; the system has limited recall.")

    if events and len(agents) > 0:
        source_counts: dict[str, int] = {}
        for event in events:
            source_counts[event.source_agent] = source_counts.get(event.source_agent, 0) + 1
        top_source_count = max(source_counts.values(), default=0)
        if top_source_count > len(events) * 0.75:
            risks.append("Event activity is concentrated in a single agent, which may indicate imbalanced workloads.")

    for memory in memories:
        content = _normalize_text(memory.content)
        if any(keyword in content for keyword in ("error", "fail", "warning", "exception", "problem")):
            risks.append("Memory content contains warnings or failures that should be reviewed.")
            break

    return risks


def _generate_recommendations(agents: list[dict], events: list, memories: list) -> List[str]:
    recommendations: List[str] = []

    if not agents:
        recommendations.append("Register agents to begin operating the system.")
    else:
        recommendations.append("Review active agents and make sure roles are aligned with goals.")

    if not events:
        recommendations.append("Trigger or simulate events so the CEO can monitor agent behavior.")
    else:
        recommendations.append("Inspect recent events for unexpected agent interactions.")

    if not memories:
        recommendations.append("Capture key memory items to improve context and recall.")
    else:
        recommendations.append("Review the latest memories to ensure knowledge is up to date.")

    if len(agents) >= 2 and events:
        recommendations.append("Encourage collaboration across agents based on available event and memory patterns.")

    recommendations.append("Use this executive brief regularly to keep the team aligned.")
    return recommendations


def generate_daily_brief(business_id: Optional[str] = None) -> DailyBrief:
    agents = get_agents()
    events = get_events(business_id=business_id)
    memories = get_memories(business_id=business_id)
    from app.communications.service import summarize_inbox
    from app.marketing.service import get_summary as get_marketing_summary
    from app.sales.service import get_summary
    from app.whatsapp.service import summarize_whatsapp

    inbox = summarize_inbox(business_id=business_id)
    whatsapp = summarize_whatsapp(business_id=business_id)
    sales = get_summary()
    marketing = get_marketing_summary()

    sorted_events = sorted(events, key=lambda event: event.timestamp, reverse=True)
    sorted_memories = sorted(memories, key=lambda memory: memory.timestamp, reverse=True)

    return DailyBrief(
        active_agents=[_summarize_agent(agent) for agent in agents],
        recent_events=[_summarize_event(event) for event in sorted_events[:5]],
        recent_memories=[_summarize_memory(memory) for memory in sorted_memories[:5]],
        risks=_generate_risks(agents, events, memories),
        recommendations=_generate_recommendations(agents, events, memories),
        inbox_summary=inbox.model_dump(),
        communication_risks=inbox.risks,
        communication_opportunities=inbox.opportunities,
        whatsapp_summary=whatsapp.model_dump(),
        whatsapp_alerts=whatsapp.executive_alerts,
        whatsapp_risk_notifications=whatsapp.risk_notifications,
        sales_summary=sales.model_dump(),
        sales_next_actions=sales.next_actions,
        marketing_summary=marketing.model_dump(),
        marketing_next_actions=marketing.next_actions,
    )

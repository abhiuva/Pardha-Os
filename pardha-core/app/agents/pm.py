from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.agents.ceo import generate_daily_brief
from app.agents.cto import TechnicalItem, generate_cto_brief
from app.events.bus import get_events
from app.memory.engine import get_memories


PRIORITY_SCORES = {"critical": 100, "high": 80, "medium": 50, "low": 20}
PRODUCT_KEYWORDS = {
    "customer",
    "feature",
    "launch",
    "market",
    "mvp",
    "product",
    "requirement",
    "roadmap",
    "user story",
}
MVP_KEYWORDS = {"core", "essential", "launch blocker", "minimum viable", "must have", "mvp"}
CUSTOMER_KEYWORDS = {"customer", "user", "user story"}
BUSINESS_KEYWORDS = {"growth", "market", "revenue", "sales"}
RISK_KEYWORDS = {"blocked", "critical", "dependency", "failure", "risk", "security"}

EPIC_BY_CATEGORY = {
    "bug": "Reliability",
    "infrastructure": "Platform & Infrastructure",
    "engineering_task": "Engineering Enablement",
    "product_request": "Product Experience",
    "roadmap_item": "Strategy & Discovery",
}


class ProductBacklogItem(BaseModel):
    title: str
    category: str
    priority: str
    priority_score: int
    epic: str
    roadmap_stage: str
    is_mvp: bool
    source_type: str
    source_id: str


class Epic(BaseModel):
    name: str
    priority: str
    item_count: int
    items: List[str]


class PMBrief(BaseModel):
    top_priorities: List[ProductBacklogItem]
    product_backlog: List[ProductBacklogItem]
    epics: List[Epic]
    risks: List[str]
    recommended_next_sprint: List[ProductBacklogItem]
    customer_followups: List[str] = Field(default_factory=list)
    stakeholder_updates: List[str] = Field(default_factory=list)
    sprint_reports: List[str] = Field(default_factory=list)
    whatsapp_project_updates: List[str] = Field(default_factory=list)
    whatsapp_sprint_summaries: List[str] = Field(default_factory=list)
    whatsapp_stakeholder_notifications: List[str] = Field(default_factory=list)
    reasoning: Optional[str] = None


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _flatten_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(f"{key} {_flatten_value(item)}" for key, item in sorted(value.items()))
    if isinstance(value, set):
        return " ".join(_flatten_value(item) for item in sorted(value, key=str))
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten_value(item) for item in value)
    return str(value)


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _event_title(event) -> str:
    for key in ("title", "summary", "description", "message", "task", "request"):
        value = event.payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return event.event_type.replace(".", " ").replace("_", " ").strip().title()


def _memory_title(memory) -> str:
    content = memory.content.strip()
    return content if len(content) <= 120 else f"{content[:117].rstrip()}..."


def _is_mvp(text: str) -> bool:
    return _contains_any(text, MVP_KEYWORDS)


def _priority_score(priority: str, text: str, category: str) -> int:
    score = PRIORITY_SCORES[priority]
    if _is_mvp(text):
        score += 15
    if _contains_any(text, CUSTOMER_KEYWORDS):
        score += 10
    if _contains_any(text, BUSINESS_KEYWORDS):
        score += 10
    if category == "bug":
        score += 10
    if _contains_any(text, RISK_KEYWORDS):
        score += 5
    return score


def _roadmap_stage(priority: str, is_mvp: bool) -> str:
    if is_mvp or priority in {"critical", "high"}:
        return "now"
    if priority == "medium":
        return "next"
    return "later"


def _make_item(
    *,
    title: str,
    category: str,
    priority: str,
    text: str,
    source_type: str,
    source_id: str,
) -> ProductBacklogItem:
    is_mvp = _is_mvp(text)
    return ProductBacklogItem(
        title=title,
        category=category,
        priority=priority,
        priority_score=_priority_score(priority, text, category),
        epic=EPIC_BY_CATEGORY.get(category, "Strategy & Discovery"),
        roadmap_stage=_roadmap_stage(priority, is_mvp),
        is_mvp=is_mvp,
        source_type=source_type,
        source_id=source_id,
    )


def _from_technical_item(item: TechnicalItem) -> ProductBacklogItem:
    text = _normalize_text(f"{item.title} {item.category} {item.priority}")
    return _make_item(
        title=item.title,
        category=item.category,
        priority=item.priority,
        text=text,
        source_type=f"cto_{item.source_type}",
        source_id=item.source_id,
    )


def _raw_product_items(events: list, memories: list) -> List[ProductBacklogItem]:
    items: List[ProductBacklogItem] = []
    for event in events:
        text = _normalize_text(f"{event.event_type} {_flatten_value(event.payload)}")
        if _contains_any(text, PRODUCT_KEYWORDS):
            priority = "high" if _contains_any(text, MVP_KEYWORDS | RISK_KEYWORDS) else "medium"
            items.append(
                _make_item(
                    title=_event_title(event),
                    category="roadmap_item",
                    priority=priority,
                    text=text,
                    source_type="event",
                    source_id=str(event.event_id),
                )
            )

    for memory in memories:
        text = _normalize_text(f"{memory.content} {_flatten_value(memory.metadata)}")
        if _contains_any(text, PRODUCT_KEYWORDS):
            priority = "high" if _contains_any(text, MVP_KEYWORDS | RISK_KEYWORDS) else "medium"
            items.append(
                _make_item(
                    title=_memory_title(memory),
                    category="roadmap_item",
                    priority=priority,
                    text=text,
                    source_type="memory",
                    source_id=str(memory.memory_id),
                )
            )
    return items


def _sort_and_deduplicate(items: List[ProductBacklogItem]) -> List[ProductBacklogItem]:
    unique: Dict[str, ProductBacklogItem] = {}
    for item in items:
        key = _normalize_text(item.title)
        current = unique.get(key)
        if (
            current is None
            or item.priority_score > current.priority_score
            or (item.priority_score == current.priority_score and item.source_id < current.source_id)
        ):
            unique[key] = item
    return sorted(
        unique.values(),
        key=lambda item: (-item.priority_score, _normalize_text(item.title), item.source_id),
    )


def _build_epics(backlog: List[ProductBacklogItem]) -> List[Epic]:
    grouped: Dict[str, List[ProductBacklogItem]] = {}
    for item in backlog:
        grouped.setdefault(item.epic, []).append(item)

    epics = [
        Epic(
            name=name,
            priority=items[0].priority,
            item_count=len(items),
            items=[item.title for item in items],
        )
        for name, items in grouped.items()
    ]
    return sorted(
        epics,
        key=lambda epic: (-max(item.priority_score for item in grouped[epic.name]), epic.name),
    )


def _build_risks(ceo_brief, cto_brief, backlog: List[ProductBacklogItem]) -> List[str]:
    risks: List[str] = []
    risks.extend(ceo_brief.risks)
    risks.extend(item.title for item in cto_brief.infrastructure_risks)
    if not backlog:
        risks.append("No product backlog could be generated from available business context.")
    if backlog and not any(item.is_mvp for item in backlog):
        risks.append("No MVP features are explicitly identified in the available context.")
    if len([item for item in backlog if item.roadmap_stage == "now"]) > 5:
        risks.append("The immediate roadmap contains more than five items and may exceed sprint capacity.")
    return list(dict.fromkeys(risks))


def _next_sprint(backlog: List[ProductBacklogItem]) -> List[ProductBacklogItem]:
    now_items = [item for item in backlog if item.roadmap_stage == "now"]
    selected = now_items[:5]
    if len(selected) < 5:
        selected_ids = {item.source_id for item in selected}
        selected.extend(item for item in backlog if item.source_id not in selected_ids)
    return selected[:5]


def generate_pm_brief(business_id: Optional[str] = None) -> PMBrief:
    ceo_brief = generate_daily_brief(business_id=business_id)
    cto_brief = generate_cto_brief(business_id=business_id)
    events = get_events(business_id=business_id)
    memories = get_memories(business_id=business_id)
    from app.communications.service import summarize_inbox
    from app.whatsapp.service import summarize_whatsapp

    inbox = summarize_inbox(business_id=business_id)
    whatsapp = summarize_whatsapp(business_id=business_id)

    cto_items = [_from_technical_item(item) for item in cto_brief.prioritized_backlog]
    backlog = _sort_and_deduplicate(cto_items + _raw_product_items(events, memories))

    return PMBrief(
        top_priorities=backlog[:5],
        product_backlog=backlog,
        epics=_build_epics(backlog),
        risks=_build_risks(ceo_brief, cto_brief, backlog),
        recommended_next_sprint=_next_sprint(backlog),
        customer_followups=inbox.followups,
        stakeholder_updates=[
            f"Draft stakeholder update for {item.title}"
            for item in backlog[:3]
        ],
        sprint_reports=[
            f"{epic.name}: {epic.item_count} scoped item{'s' if epic.item_count != 1 else ''}"
            for epic in _build_epics(backlog)[:3]
        ],
        whatsapp_project_updates=whatsapp.operations_updates,
        whatsapp_sprint_summaries=[
            f"WhatsApp sprint summary: {item.title}"
            for item in backlog[:3]
        ],
        whatsapp_stakeholder_notifications=whatsapp.executive_alerts,
    )


def create_jira_epic(summary: str, description: str = "", *, client=None) -> dict:
    from app.jira.service import create_pm_epic

    return create_pm_epic(summary, description, client=client)


def create_jira_story(summary: str, description: str = "", *, parent_key: str | None = None, client=None) -> dict:
    from app.jira.service import create_pm_story

    return create_pm_story(summary, description, parent_key=parent_key, client=client)


def create_jira_sprint_backlog(stories: list[dict], *, epic_key: str | None = None, client=None) -> list[dict]:
    from app.jira.service import create_pm_sprint_backlog

    return create_pm_sprint_backlog(stories, epic_key=epic_key, client=client)

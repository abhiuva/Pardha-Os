from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel

from app.events.bus import get_events
from app.kernel.registry import get_agents
from app.memory.engine import get_memories
from app.projects.service import get_projects


PRODUCT_KEYWORDS = {
    "feature",
    "feature request",
    "product request",
    "enhancement",
    "requirement",
    "user story",
    "customer request",
    "new product",
}
BUG_KEYWORDS = {
    "bug",
    "broken",
    "defect",
    "error",
    "exception",
    "fail",
    "failure",
    "incident",
    "regression",
}
INFRASTRUCTURE_KEYWORDS = {
    "ci/cd",
    "cloud",
    "database",
    "deploy",
    "deployment",
    "docker",
    "infrastructure",
    "kubernetes",
    "latency",
    "monitoring",
    "network",
    "postgres",
    "scaling",
    "server",
}
TASK_KEYWORDS = {
    "action item",
    "build",
    "fix",
    "implement",
    "migrate",
    "refactor",
    "task",
    "technical debt",
    "todo",
    "upgrade",
}
CRITICAL_KEYWORDS = {
    "critical",
    "data loss",
    "outage",
    "production down",
    "security",
    "sev1",
}
HIGH_KEYWORDS = {
    "blocked",
    "blocking",
    "high priority",
    "production",
    "urgent",
}

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class TechnicalItem(BaseModel):
    title: str
    category: str
    priority: str
    source_type: str
    source_id: str
    source_agent: str


class AgentActivity(BaseModel):
    agent_id: str
    name: str
    role: str
    status: str
    event_count: int
    memory_count: int


class ProjectInventory(BaseModel):
    project_id: str
    project_name: str
    project_path: str
    language: str
    framework: str
    file_count: int
    last_scanned: str


class CTOBrief(BaseModel):
    open_engineering_tasks: List[TechnicalItem]
    product_requests: List[TechnicalItem]
    infrastructure_risks: List[TechnicalItem]
    recommended_actions: List[str]
    prioritized_backlog: List[TechnicalItem]
    agent_activity: List[AgentActivity]
    project_inventory: List[ProjectInventory]
    project_findings: List[str]
    reasoning: Optional[str] = None


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _contains_any(text: str, keywords: Set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


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


def _event_text(event) -> str:
    return _normalize_text(f"{event.event_type} {_flatten_value(event.payload)}")


def _memory_text(memory) -> str:
    return _normalize_text(f"{memory.content} {_flatten_value(memory.metadata)}")


def _event_title(event) -> str:
    for key in ("title", "summary", "description", "message", "task", "request"):
        value = event.payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return event.event_type.replace(".", " ").replace("_", " ").strip().title()


def _memory_title(memory) -> str:
    content = memory.content.strip()
    return content if len(content) <= 120 else f"{content[:117].rstrip()}..."


def _priority(text: str, category: str) -> str:
    if _contains_any(text, CRITICAL_KEYWORDS):
        return "critical"
    if category in {"bug", "infrastructure"} or _contains_any(text, HIGH_KEYWORDS):
        return "high"
    if category in {"product_request", "engineering_task"}:
        return "medium"
    return "low"


def _categories(text: str) -> Set[str]:
    categories: Set[str] = set()
    if _contains_any(text, PRODUCT_KEYWORDS):
        categories.add("product_request")
    if _contains_any(text, BUG_KEYWORDS):
        categories.add("bug")
    if _contains_any(text, INFRASTRUCTURE_KEYWORDS):
        categories.add("infrastructure")
    if _contains_any(text, TASK_KEYWORDS):
        categories.add("engineering_task")
    return categories


def _make_item(
    *,
    title: str,
    category: str,
    text: str,
    source_type: str,
    source_id: str,
    source_agent: str,
) -> TechnicalItem:
    return TechnicalItem(
        title=title,
        category=category,
        priority=_priority(text, category),
        source_type=source_type,
        source_id=source_id,
        source_agent=source_agent,
    )


def _deduplicate(items: List[TechnicalItem]) -> List[TechnicalItem]:
    unique: Dict[tuple[str, str], TechnicalItem] = {}
    for item in items:
        key = (item.category, _normalize_text(item.title))
        current = unique.get(key)
        if (
            current is None
            or PRIORITY_ORDER[item.priority] < PRIORITY_ORDER[current.priority]
            or (
                item.priority == current.priority
                and item.source_id < current.source_id
            )
        ):
            unique[key] = item
    return list(unique.values())


def _sort_items(items: List[TechnicalItem]) -> List[TechnicalItem]:
    return sorted(
        _deduplicate(items),
        key=lambda item: (
            PRIORITY_ORDER[item.priority],
            item.category,
            _normalize_text(item.title),
            item.source_id,
        ),
    )


def _build_activity(agents: list[dict], events: list, memories: list) -> List[AgentActivity]:
    event_counts: Dict[str, int] = {}
    memory_counts: Dict[str, int] = {}

    for event in events:
        event_counts[event.source_agent] = event_counts.get(event.source_agent, 0) + 1
        if event.target_agent != event.source_agent:
            event_counts[event.target_agent] = event_counts.get(event.target_agent, 0) + 1

    for memory in memories:
        memory_counts[memory.agent_id] = memory_counts.get(memory.agent_id, 0) + 1

    return [
        AgentActivity(
            agent_id=agent["id"],
            name=agent["name"],
            role=agent["role"],
            status=agent["status"],
            event_count=event_counts.get(agent["id"], 0),
            memory_count=memory_counts.get(agent["id"], 0),
        )
        for agent in sorted(agents, key=lambda item: (item["name"].lower(), item["id"]))
    ]


def _synthetic_risk(title: str, category: str, priority: str) -> TechnicalItem:
    return TechnicalItem(
        title=title,
        category=category,
        priority=priority,
        source_type="system",
        source_id=f"system:{category}:{_normalize_text(title).replace(' ', '-')}",
        source_agent="cto",
    )


def _recommend_actions(
    bugs: List[TechnicalItem],
    product_requests: List[TechnicalItem],
    infrastructure: List[TechnicalItem],
    activity: List[AgentActivity],
) -> List[str]:
    actions: List[str] = []
    if any(item.priority == "critical" for item in bugs + infrastructure):
        actions.append("Triage critical technical risks before starting new engineering work.")
    if bugs:
        actions.append("Assign owners and reproduction steps for detected bugs.")
    if product_requests:
        actions.append("Validate product requests and convert approved requests into scoped engineering tasks.")
    if infrastructure:
        actions.append("Review infrastructure risks and define mitigation owners.")
    if activity and any(item.event_count == 0 and item.memory_count == 0 for item in activity):
        actions.append("Review registered agents with no recorded events or memories.")
    if not actions:
        actions.append("No technical work was detected; continue monitoring persisted events and memories.")
    return actions


def _project_inventory(projects: list) -> List[ProjectInventory]:
    return [
        ProjectInventory(
            project_id=project.project_id,
            project_name=project.project_name,
            project_path=project.project_path,
            language=project.language,
            framework=project.framework,
            file_count=project.analysis.file_count,
            last_scanned=project.last_scanned.isoformat(),
        )
        for project in projects
    ]


def _project_findings(projects: list) -> List[str]:
    findings: List[str] = []
    for project in projects:
        if project.analysis.missing_documentation:
            findings.append(
                f"{project.project_name}: missing documentation: "
                f"{', '.join(project.analysis.missing_documentation)}."
            )
        if project.analysis.missing_tests:
            findings.append(f"{project.project_name}: no tests were detected.")
        for module in project.analysis.large_modules[:3]:
            findings.append(
                f"{project.project_name}: large module {module.path} has {module.lines} lines."
            )
    return findings


def generate_cto_brief(business_id: Optional[str] = None) -> CTOBrief:
    agents = get_agents()
    events = get_events(business_id=business_id)
    memories = get_memories(business_id=business_id)
    projects = get_projects(business_id=business_id)

    bugs: List[TechnicalItem] = []
    product_requests: List[TechnicalItem] = []
    infrastructure: List[TechnicalItem] = []
    engineering_tasks: List[TechnicalItem] = []

    for event in events:
        text = _event_text(event)
        for category in sorted(_categories(text)):
            item = _make_item(
                title=_event_title(event),
                category=category,
                text=text,
                source_type="event",
                source_id=str(event.event_id),
                source_agent=event.source_agent,
            )
            {"bug": bugs, "product_request": product_requests, "infrastructure": infrastructure}.get(
                category, engineering_tasks
            ).append(item)

    for memory in memories:
        text = _memory_text(memory)
        for category in sorted(_categories(text)):
            item = _make_item(
                title=_memory_title(memory),
                category=category,
                text=text,
                source_type="memory",
                source_id=str(memory.memory_id),
                source_agent=memory.agent_id,
            )
            {"bug": bugs, "product_request": product_requests, "infrastructure": infrastructure}.get(
                category, engineering_tasks
            ).append(item)

    activity = _build_activity(agents, events, memories)
    infrastructure_risks = list(infrastructure)
    if not events:
        infrastructure_risks.append(
            _synthetic_risk("No events are available for technical monitoring.", "observability", "high")
        )
    if not memories:
        infrastructure_risks.append(
            _synthetic_risk("No memories are available for technical context.", "knowledge", "medium")
        )
    if not agents:
        infrastructure_risks.append(
            _synthetic_risk("No agents are registered for engineering execution.", "capacity", "high")
        )

    open_tasks = _sort_items(bugs + infrastructure + engineering_tasks)
    product_requests = _sort_items(product_requests)
    infrastructure_risks = _sort_items(infrastructure_risks)
    backlog = _sort_items(open_tasks + product_requests)

    return CTOBrief(
        open_engineering_tasks=open_tasks,
        product_requests=product_requests,
        infrastructure_risks=infrastructure_risks,
        recommended_actions=_recommend_actions(bugs, product_requests, infrastructure_risks, activity),
        prioritized_backlog=backlog,
        agent_activity=activity,
        project_inventory=_project_inventory(projects),
        project_findings=_project_findings(projects),
    )


def create_jira_engineering_task(summary: str, description: str = "", *, parent_key: str | None = None, client=None) -> dict:
    from app.jira.service import create_engineering_task

    return create_engineering_task(summary, description, parent_key=parent_key, client=client)


def update_jira_task_status(issue_key: str, status: str, *, client=None) -> dict:
    from app.jira.service import update_engineering_task_status

    return update_engineering_task_status(issue_key, status, client=client)


def link_jira_technical_task(issue_key: str, parent_key: str, *, client=None) -> dict:
    from app.jira.service import link_technical_task

    return link_technical_task(issue_key, parent_key, client=client)

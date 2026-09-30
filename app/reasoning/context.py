from __future__ import annotations

import json

from app.db import SessionLocal
from app.db.models import Event, Knowledge, Objective, Project, Task
from app.knowledge.service import get_knowledge_summary


CONTEXT_LIMIT = 10
TEXT_LIMIT = 500
SERIALIZED_CONTEXT_LIMIT = 16000


def _short(value: str | None) -> str:
    return (value or "")[:TEXT_LIMIT]


def _dump_context(context: dict) -> str:
    serialized = json.dumps(context, default=str, indent=2)
    if len(serialized) <= SERIALIZED_CONTEXT_LIMIT:
        return serialized

    for item in context.get("business_knowledge", []):
        item["content"] = _short(item.get("content"))[:160]
    for item in context.get("recent_events", []):
        item["payload"] = _short(json.dumps(item.get("payload"), default=str))
    for item in context.get("tasks", []):
        item["description"] = _short(item.get("description"))[:160]
    for item in context.get("project_inventory", []):
        item["summary"] = _short(item.get("summary"))[:160]
    for item in context.get("active_objectives", []):
        item["description"] = _short(item.get("description"))[:160]

    serialized = json.dumps(context, default=str, indent=2)
    if len(serialized) <= SERIALIZED_CONTEXT_LIMIT:
        return serialized

    for key in ["business_knowledge", "recent_events", "tasks", "project_inventory", "active_objectives"]:
        context[key] = context.get(key, [])[:5]
    return json.dumps(context, default=str, indent=2)


def build_business_context(business_id: str | None = None) -> str:
    if business_id is None:
        from app.business.service import get_active_business

        business_id = get_active_business().business_id
    summary = get_knowledge_summary(business_id=business_id)
    with SessionLocal() as session:
        knowledge = session.query(Knowledge).filter(Knowledge.business_id == business_id).order_by(Knowledge.created_at.desc()).limit(CONTEXT_LIMIT).all()
        events = session.query(Event).filter(Event.business_id == business_id).order_by(Event.timestamp.desc()).limit(CONTEXT_LIMIT).all()
        tasks = session.query(Task).filter(Task.business_id == business_id).order_by(Task.updated_at.desc()).limit(CONTEXT_LIMIT).all()
        projects = session.query(Project).filter(Project.business_id == business_id).order_by(Project.last_scanned.desc()).limit(CONTEXT_LIMIT).all()
        objectives = (
            session.query(Objective)
            .filter(Objective.business_id == business_id)
            .filter(Objective.status.in_(["NEW", "IN_PROGRESS", "BLOCKED"]))
            .order_by(Objective.created_at.desc())
            .limit(CONTEXT_LIMIT)
            .all()
        )

        context = {
            "knowledge_context": {
                "business_id": summary.business_id,
                "business_name": summary.business_name,
                "source": "postgresql_knowledge_store",
                "total_records": summary.total_records,
                "categories": summary.categories,
                "sources": [source.model_dump() for source in summary.sources[:CONTEXT_LIMIT]],
                "expected_sources": summary.expected_sources,
                "missing_expected_sources": summary.missing_expected_sources,
                "context_ready": summary.context_ready,
                "generated_at": summary.generated_at.isoformat(),
            },
            "business_knowledge": [
                {
                    "business_name": item.business_name,
                    "category": item.category,
                    "title": item.title,
                    "content": _short(item.content),
                    "source": item.source,
                    "source_uri": item.source_uri,
                    "version": (item.document_metadata_json or {}).get("version"),
                }
                for item in knowledge
            ],
            "recent_events": [
                {"event_type": item.event_type, "source": item.source_agent, "payload": item.payload}
                for item in events
            ],
            "tasks": [
                {
                    "title": item.title,
                    "status": item.status,
                    "assigned_agent": item.assigned_agent,
                    "description": _short(item.description),
                }
                for item in tasks
            ],
            "project_inventory": [
                {
                    "project_name": item.project_name,
                    "language": item.language,
                    "framework": item.framework,
                    "summary": _short(item.repository_summary),
                }
                for item in projects
            ],
            "active_objectives": [
                {
                    "title": item.title,
                    "description": _short(item.description),
                    "business_name": item.business_name,
                    "priority": item.priority,
                    "status": item.status,
                }
                for item in objectives
            ],
        }
    return _dump_context(context)

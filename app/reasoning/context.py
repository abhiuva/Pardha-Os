from __future__ import annotations

import json

from app.db import SessionLocal
from app.db.models import Event, Knowledge, Objective, Project, Task


CONTEXT_LIMIT = 10
TEXT_LIMIT = 500


def _short(value: str | None) -> str:
    return (value or "")[:TEXT_LIMIT]


def build_business_context(business_id: str | None = None) -> str:
    if business_id is None:
        from app.business.service import get_active_business

        business_id = get_active_business().business_id
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
            "business_knowledge": [
                {
                    "business_name": item.business_name,
                    "category": item.category,
                    "title": item.title,
                    "content": _short(item.content),
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
    return json.dumps(context, default=str, indent=2)[:16000]

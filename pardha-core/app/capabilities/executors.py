from __future__ import annotations

from typing import Any, Callable


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_dump(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump(item) for key, item in value.items()}
    return value


def execute_adapter(adapter: str | None, *, business_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    if not adapter:
        return {"message": "Capability registered for discovery only; no execution adapter is attached."}
    handler = ADAPTERS.get(adapter)
    if handler is None:
        raise ValueError(f"No execution adapter registered for {adapter}.")
    return _dump(handler(business_id, payload))


def _ceo_daily_brief(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.agents.ceo import generate_daily_brief

    return generate_daily_brief(business_id=business_id)


def _business_context(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.business.service import list_businesses

    query = str(payload.get("query", "")).lower()
    businesses = list_businesses()
    candidates = [
        business
        for business in businesses
        if business.business_name.lower() in query or business.business_type.lower() in query
    ]
    active = next((business for business in businesses if business.business_id == business_id), None)
    return {
        "active_business": _dump(active) if active else None,
        "businesses": [_dump(business) for business in businesses],
        "candidate_businesses": [_dump(business) for business in candidates],
        "ambiguous": not active and len(candidates) != 1,
    }


def _pm_daily_brief(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.agents.pm import generate_pm_brief

    return generate_pm_brief(business_id=business_id)


def _cto_technical_brief(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.agents.cto import generate_cto_brief

    return generate_cto_brief(business_id=business_id)


def _knowledge_search(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.knowledge.service import search_knowledge

    return search_knowledge(query=payload.get("query", ""), business_id=business_id)


def _sales_summary(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.sales.service import get_summary

    return get_summary()


def _marketing_summary(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.marketing.service import get_summary

    return get_summary()


def _projects_catalog(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.projects.service import get_projects

    return get_projects(business_id=business_id)


def _tasks_catalog(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.collaboration.service import get_tasks

    return get_tasks(business_id=business_id)


def _objectives_catalog(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.collaboration.service import get_objectives

    return get_objectives(business_id=business_id)


def _executions_catalog(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.agents.executions import get_executions

    return get_executions(business_id=business_id)[:20]


def _founder_goals_catalog(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.chief_of_staff.service import list_goals

    return list_goals(business_id=business_id)


def _jira_status(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.jira.service import jira_status

    return jira_status()


def _system_health(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.commercial.service import system_health

    return system_health()


def _connector_status(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.commercial.service import connector_statuses

    return connector_statuses()


def _conversation_runtime_inspector(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.conversations.runtime_inspector import inspect_runtime

    return inspect_runtime(str(payload.get("query", "")), {"business_id": business_id})


def _executive_response_composer(business_id: str | None, payload: dict[str, Any]) -> Any:
    return {
        "status": "available",
        "description": "The Executive Response Composer is the only component that creates founder-facing conversation text.",
        "business_id": business_id,
        "guarantees": ["natural_executive_language", "hidden_transparency", "evidence_based", "runtime_inspected"],
    }


def _operational_learning_status(business_id: str | None, payload: dict[str, Any]) -> Any:
    from app.conversations.runtime_inspector import inspect_runtime

    runtime = inspect_runtime(str(payload.get("query", "")), {"business_id": business_id})
    return {"status": "available", "learning": runtime.get("learning", [])}


ADAPTERS: dict[str, Callable[[str | None, dict[str, Any]], Any]] = {
    "business.context": _business_context,
    "ceo.daily_brief": _ceo_daily_brief,
    "pm.daily_brief": _pm_daily_brief,
    "cto.technical_brief": _cto_technical_brief,
    "knowledge.search": _knowledge_search,
    "sales.summary": _sales_summary,
    "marketing.summary": _marketing_summary,
    "projects.catalog": _projects_catalog,
    "tasks.catalog": _tasks_catalog,
    "objectives.catalog": _objectives_catalog,
    "executions.catalog": _executions_catalog,
    "founder_goals.catalog": _founder_goals_catalog,
    "jira.status": _jira_status,
    "diagnostics.system_health": _system_health,
    "connectors.status": _connector_status,
    "conversation.runtime_inspector": _conversation_runtime_inspector,
    "conversation.response_composer": _executive_response_composer,
    "conversation.operational_learning": _operational_learning_status,
}

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional, Protocol
from uuid import uuid4

from app.collaboration.schemas import ObjectiveCreate
from app.collaboration.service import create_objective
from app.db import SessionLocal
from app.db.models import JiraIssue as JiraIssueModel
from app.db.models import JiraProject as JiraProjectModel
from app.db.models import JiraSyncHistory as JiraSyncHistoryModel
from app.db.models import Objective as ObjectiveModel
from app.db.models import Task as TaskModel
from app.jira.client import JiraClient, JiraConfigurationError
from app.jira.schemas import JiraIssue, JiraStatus, JiraSyncHistory, JiraSyncRequest, JiraSyncResult
from app.settings import get_settings


class JiraClientProtocol(Protocol):
    project_key: str
    jira_url: str
    email: str

    def create_epic(self, summary: str, description: str = "") -> dict: ...

    def create_story(
        self,
        summary: str,
        description: str = "",
        *,
        parent_key: Optional[str] = None,
        technical: bool = False,
    ) -> dict: ...

    def update_issue(self, issue_key: str, fields: dict) -> dict: ...

    def get_issue(self, issue_key: str) -> dict: ...

    def search_issues(self, jql: str, max_results: int = 50) -> dict: ...


def get_jira_client() -> JiraClient:
    return JiraClient.from_settings()


def jira_status() -> JiraStatus:
    settings = get_settings()
    configured = all([settings.jira_url, settings.jira_email, settings.jira_api_token, settings.jira_project_key])
    with SessionLocal() as session:
        project_count = session.query(JiraProjectModel).count()
        issue_count = session.query(JiraIssueModel).count()
        epic_count = session.query(JiraIssueModel).filter(JiraIssueModel.issue_type == "epic").count()
        story_count = session.query(JiraIssueModel).filter(JiraIssueModel.issue_type.in_(["story", "technical_story"])).count()
        last_sync = (
            session.query(JiraSyncHistoryModel)
            .order_by(JiraSyncHistoryModel.completed_at.desc())
            .first()
        )
    return JiraStatus(
        connected=True,
        project_count=project_count,
        issue_count=issue_count,
        configured=configured,
        enabled=settings.jira_enabled,
        project_key=settings.jira_project_key or None,
        jira_url=settings.jira_url or None,
        epic_count=epic_count,
        story_count=story_count,
        last_sync=last_sync.completed_at if last_sync else None,
        message="configured" if configured else "Missing Jira environment variables.",
    )


def get_projects() -> List:
    with SessionLocal() as session:
        rows = session.query(JiraProjectModel).order_by(JiraProjectModel.updated_at.desc()).all()
        return [_project_to_schema(row) for row in rows]


def get_issues() -> List[JiraIssue]:
    with SessionLocal() as session:
        rows = session.query(JiraIssueModel).order_by(JiraIssueModel.synced_at.desc(), JiraIssueModel.summary).all()
        return [JiraIssue.model_validate(row) for row in rows]


def create_pm_epic(summary: str, description: str = "", *, client: Optional[JiraClientProtocol] = None) -> dict:
    return (client or get_jira_client()).create_epic(summary, description)


def create_pm_story(
    summary: str,
    description: str = "",
    *,
    parent_key: Optional[str] = None,
    client: Optional[JiraClientProtocol] = None,
) -> dict:
    return (client or get_jira_client()).create_story(summary, description, parent_key=parent_key)


def create_pm_sprint_backlog(
    stories: Iterable[dict],
    *,
    epic_key: Optional[str] = None,
    client: Optional[JiraClientProtocol] = None,
) -> list[dict]:
    jira_client = client or get_jira_client()
    return [
        jira_client.create_story(
            story["summary"],
            story.get("description", ""),
            parent_key=story.get("parent_key") or epic_key,
        )
        for story in stories
    ]


def create_engineering_task(
    summary: str,
    description: str = "",
    *,
    parent_key: Optional[str] = None,
    client: Optional[JiraClientProtocol] = None,
) -> dict:
    return (client or get_jira_client()).create_story(
        summary,
        description,
        parent_key=parent_key,
        technical=True,
    )


def update_engineering_task_status(
    issue_key: str,
    status: str,
    *,
    client: Optional[JiraClientProtocol] = None,
) -> dict:
    jira_client = client or get_jira_client()
    if hasattr(jira_client, "transition_issue"):
        return jira_client.transition_issue(issue_key, status)
    return jira_client.update_issue(issue_key, {"status": {"name": status}})


def link_technical_task(
    issue_key: str,
    parent_key: str,
    *,
    client: Optional[JiraClientProtocol] = None,
) -> dict:
    return (client or get_jira_client()).update_issue(issue_key, {"parent": {"key": parent_key}})


def sync_jira(request: JiraSyncRequest, *, client: Optional[JiraClientProtocol] = None) -> JiraSyncResult:
    jira_client = client or get_jira_client()
    objective_id = _ensure_objective(request)
    started_at = datetime.now(timezone.utc)
    history_id = str(uuid4())
    issue_keys: list[str] = []

    with SessionLocal() as session:
        _upsert_project(session, jira_client, started_at)
        objective = session.get(ObjectiveModel, objective_id)
        if objective is None:
            raise ValueError("Objective not found.")
        tasks = _objective_tasks(session, objective_id)
        objective_summary = _epic_summary(objective)
        objective_description = objective.description
        product_tasks = [_task_snapshot(task) for task in tasks if task.payload.get("work_type") == "product"]
        engineering_tasks = [_task_snapshot(task) for task in tasks if task.payload.get("work_type") == "engineering"]
        history = JiraSyncHistoryModel(
            jira_sync_id=history_id,
            project_key=jira_client.project_key,
            objective_id=objective_id,
            status="running",
            action="objective_sync",
            summary=f"Sync objective {objective.title} to Jira",
            issue_count=0,
            error=None,
            payload={"dry_run": request.dry_run},
            started_at=started_at,
            completed_at=started_at,
        )
        session.add(history)
        session.commit()

    try:
        epic_response = _dry_issue(jira_client.project_key, "Epic", objective_summary, objective_id) if request.dry_run else jira_client.create_epic(
            objective_summary,
            objective_description,
        )
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            epic_row = _record_issue(
                session,
                jira_client=jira_client,
                response=epic_response,
                issue_type="epic",
                source_type="objective",
                source_id=objective_id,
                summary=objective_summary,
                description=objective_description,
                parent_key=None,
                synced_at=now,
            )
            epic_key = epic_row.jira_issue_key
            issue_keys.append(epic_key)
            session.commit()

        for task in product_tasks:
            response = _dry_issue(jira_client.project_key, "Story", task["title"], task["task_id"]) if request.dry_run else jira_client.create_story(
                task["title"],
                task["description"] or "",
                parent_key=epic_key,
            )
            with SessionLocal() as session:
                row = _record_issue(
                    session,
                    jira_client=jira_client,
                    response=response,
                    issue_type="story",
                    source_type="task",
                    source_id=task["task_id"],
                    summary=task["title"],
                    description=task["description"],
                    parent_key=epic_key,
                    synced_at=datetime.now(timezone.utc),
                )
                issue_keys.append(row.jira_issue_key)
                session.commit()

        for task in engineering_tasks:
            response = _dry_issue(jira_client.project_key, "Story", task["title"], task["task_id"]) if request.dry_run else jira_client.create_story(
                task["title"],
                task["description"] or "",
                parent_key=epic_key,
                technical=True,
            )
            with SessionLocal() as session:
                row = _record_issue(
                    session,
                    jira_client=jira_client,
                    response=response,
                    issue_type="technical_story",
                    source_type="engineering_task",
                    source_id=task["task_id"],
                    summary=task["title"],
                    description=task["description"],
                    parent_key=epic_key,
                    synced_at=datetime.now(timezone.utc),
                )
                issue_keys.append(row.jira_issue_key)
                session.commit()

        completed_at = datetime.now(timezone.utc)
        with SessionLocal() as session:
            history = session.get(JiraSyncHistoryModel, history_id)
            history.status = "succeeded"
            history.issue_count = len(issue_keys)
            history.completed_at = completed_at
            history.payload = {"dry_run": request.dry_run, "jira_issue_keys": issue_keys}
            project = session.query(JiraProjectModel).filter(JiraProjectModel.project_key == jira_client.project_key).one()
            project.last_synced_at = completed_at
            project.updated_at = completed_at
            session.commit()
            return _sync_result(session, history_id)
    except Exception as exc:
        completed_at = datetime.now(timezone.utc)
        with SessionLocal() as session:
            history = session.get(JiraSyncHistoryModel, history_id)
            if history:
                history.status = "failed"
                history.error = str(exc)
                history.completed_at = completed_at
                session.commit()
        raise


def _ensure_objective(request: JiraSyncRequest) -> str:
    if request.objective_id:
        return request.objective_id
    if not all([request.title, request.description, request.business_name]):
        raise ValueError("Provide objective_id or title, description, and business_name.")
    result = create_objective(
        ObjectiveCreate(
            title=request.title,
            description=request.description,
            business_name=request.business_name,
            priority=request.priority,
        )
    )
    return result.objective.objective_id


def _objective_tasks(session, objective_id: str) -> list[TaskModel]:
    return [
        task
        for task in session.query(TaskModel).order_by(TaskModel.created_at, TaskModel.task_id).all()
        if task.payload.get("objective_id") == objective_id
    ]


def _task_snapshot(task: TaskModel) -> dict:
    return {
        "task_id": task.task_id,
        "title": task.title,
        "description": task.description,
    }


def _epic_summary(objective: ObjectiveModel) -> str:
    return f"{objective.business_name}: {objective.title}"


def _record_issue(
    session,
    *,
    jira_client: JiraClientProtocol,
    response: dict,
    issue_type: str,
    source_type: str,
    source_id: str,
    summary: str,
    description: Optional[str],
    parent_key: Optional[str],
    synced_at: datetime,
) -> JiraIssueModel:
    issue_key = response["key"]
    row = session.query(JiraIssueModel).filter(JiraIssueModel.source_type == source_type, JiraIssueModel.source_id == source_id).first()
    if row is None:
        row = JiraIssueModel(jira_issue_id=str(uuid4()), jira_issue_key=issue_key)
        session.add(row)
    row.jira_issue_key = issue_key
    row.project_key = jira_client.project_key
    row.issue_type = issue_type
    row.source_type = source_type
    row.source_id = source_id
    row.parent_jira_issue_key = parent_key
    row.summary = summary
    row.description = description
    row.status = response.get("fields", {}).get("status", {}).get("name", "created")
    row.url = f"{jira_client.jira_url}/browse/{issue_key}"
    row.raw = response
    row.synced_at = synced_at
    row.updated_at = synced_at
    return row


def _upsert_project(session, jira_client: JiraClientProtocol, now: datetime) -> JiraProjectModel:
    row = session.query(JiraProjectModel).filter(JiraProjectModel.project_key == jira_client.project_key).first()
    if row is None:
        row = JiraProjectModel(
            jira_project_id=str(uuid4()),
            project_key=jira_client.project_key,
            created_at=now,
            last_synced_at=None,
        )
        session.add(row)
    row.jira_url = jira_client.jira_url
    row.name = jira_client.project_key
    row.email = jira_client.email
    row.status = "configured"
    row.metadata_json = {"source": "environment"}
    row.updated_at = now
    return row


def _project_to_schema(row: JiraProjectModel):
    values = {
        "jira_project_id": row.jira_project_id,
        "project_key": row.project_key,
        "jira_url": row.jira_url,
        "name": row.name,
        "email": row.email,
        "status": row.status,
        "last_synced_at": row.last_synced_at,
        "metadata": row.metadata_json,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    from app.jira.schemas import JiraProject

    return JiraProject.model_validate(values)


def _sync_result(session, history_id: str) -> JiraSyncResult:
    history = session.get(JiraSyncHistoryModel, history_id)
    issue_keys = set(history.payload.get("jira_issue_keys", []))
    query = session.query(JiraIssueModel).filter(JiraIssueModel.project_key == history.project_key)
    if issue_keys:
        query = query.filter(JiraIssueModel.jira_issue_key.in_(issue_keys))
    scoped = query.order_by(JiraIssueModel.synced_at, JiraIssueModel.summary).all()
    epic = next((issue for issue in scoped if issue.issue_type == "epic"), None)
    stories = [issue for issue in scoped if issue.issue_type == "story"]
    technical_stories = [issue for issue in scoped if issue.issue_type == "technical_story"]
    return JiraSyncResult(
        status=history.status,
        project_key=history.project_key,
        objective_id=history.objective_id,
        epic=JiraIssue.model_validate(epic) if epic else None,
        stories=[JiraIssue.model_validate(issue) for issue in stories],
        technical_stories=[JiraIssue.model_validate(issue) for issue in technical_stories],
        history=JiraSyncHistory.model_validate(history),
    )


def _dry_issue(project_key: str, issue_type: str, summary: str, source_id: str) -> dict:
    prefix = "EPIC" if issue_type == "Epic" else "STORY"
    return {
        "id": source_id,
        "key": f"{project_key}-{prefix}-{source_id[:8]}",
        "self": "",
        "fields": {"summary": summary, "status": {"name": "dry_run"}},
    }

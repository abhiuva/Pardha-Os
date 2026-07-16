from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from app.collaboration.schemas import (
    AgentCollaboration,
    Objective,
    ObjectiveCreate,
    ObjectiveDetail,
    ObjectiveWorkflowResult,
    Task,
)
from app.db import SessionLocal
from app.db.models import AgentCollaboration as AgentCollaborationModel
from app.db.models import Event as EventModel
from app.db.models import Knowledge as KnowledgeModel
from app.db.models import Objective as ObjectiveModel
from app.db.models import Project as ProjectModel
from app.db.models import Task as TaskModel


EVENT_OBJECTIVE_CREATED = "OBJECTIVE_CREATED"
EVENT_EPIC_CREATED = "EPIC_CREATED"
EVENT_TASK_CREATED = "TASK_CREATED"
EVENT_TASK_ASSIGNED = "TASK_ASSIGNED"
EVENT_COLLABORATION_COMPLETED = "COLLABORATION_COMPLETED"


def _event(source: str, target: str, event_type: str, payload: dict, timestamp: datetime, business_id: str) -> EventModel:
    return EventModel(
        event_id=str(uuid4()),
        business_id=business_id,
        source_agent=source,
        target_agent=target,
        event_type=event_type,
        payload=payload,
        timestamp=timestamp,
    )


def _collaboration(
    business_id: str,
    objective_id: str,
    source: str,
    target: str,
    event_type: str,
    step_order: int,
    payload: dict,
    timestamp: datetime,
) -> AgentCollaborationModel:
    return AgentCollaborationModel(
        collaboration_id=str(uuid4()),
        business_id=business_id,
        objective_id=objective_id,
        source_agent=source,
        target_agent=target,
        action=event_type.lower(),
        event_type=event_type,
        step_order=step_order,
        status="completed",
        payload=payload,
        created_at=timestamp,
    )


def _epics_for(objective: ObjectiveCreate) -> List[str]:
    business_name = objective.business_name or "Business"
    return [
        f"{business_name}: Define {objective.title} product scope",
        f"{business_name}: Deliver {objective.title} experience",
        f"{business_name}: Validate {objective.title} outcomes",
    ]


def _context_snapshot(session, business_id: str, business_name: str) -> dict:
    return {
        "business_name": business_name,
        "business_id": business_id,
        "knowledge_count": session.query(KnowledgeModel).filter(
            KnowledgeModel.business_id == business_id
        ).count(),
        "event_count": session.query(EventModel).filter(EventModel.business_id == business_id).count(),
        "project_count": session.query(ProjectModel).filter(ProjectModel.business_id == business_id).count(),
    }


def _pm_handle_objective_created(
    session,
    objective: ObjectiveCreate,
    business_id: str,
    business_name: str,
    objective_id: str,
    epics: List[str],
    now: datetime,
) -> List[TaskModel]:
    product_tasks: List[TaskModel] = []
    for epic_index, epic in enumerate(epics, start=1):
        epic_id = str(uuid4())
        epic_payload = {
            "objective_id": objective_id,
            "business_id": business_id,
            "business_name": business_name,
            "epic_id": epic_id,
            "title": epic,
            "features": [
                f"Define requirements for {epic}",
                f"Validate user value for {epic}",
            ],
        }
        session.add(_event("pm", "cto", EVENT_EPIC_CREATED, epic_payload, now, business_id))
        epic_step = 2 + ((epic_index - 1) * 2)
        session.add(_collaboration(business_id, objective_id, "pm", "cto", EVENT_EPIC_CREATED, epic_step, epic_payload, now))

        task = TaskModel(
            task_id=str(uuid4()),
            business_id=business_id,
            title=f"Product: {epic}",
            description=f"Define product requirements, features, and acceptance criteria for {epic}.",
            status="completed",
            assigned_agent="pm",
            payload={
                **epic_payload,
                "priority": objective.priority,
                "work_type": "product",
                "created_by": "pm",
            },
            created_at=now,
            updated_at=now,
        )
        product_tasks.append(task)
        session.add(task)
        task_payload = {**epic_payload, "task_id": task.task_id, "work_type": "product"}
        session.add(_event("pm", "cto", EVENT_TASK_CREATED, task_payload, now, business_id))
        session.add(_collaboration(business_id, objective_id, "pm", "cto", EVENT_TASK_CREATED, epic_step + 1, task_payload, now))
    return product_tasks


def _cto_handle_task_created(
    session,
    objective: ObjectiveCreate,
    business_id: str,
    business_name: str,
    objective_id: str,
    product_tasks: List[TaskModel],
    now: datetime,
) -> List[TaskModel]:
    engineering_tasks: List[TaskModel] = []
    for task_index, product_task in enumerate(product_tasks, start=1):
        engineering_task = TaskModel(
            task_id=str(uuid4()),
            business_id=business_id,
            title=product_task.title.replace("Product:", "Engineering:", 1),
            description=f"Implement and validate engineering delivery for {product_task.title}.",
            status="pending",
            assigned_agent="cto",
            payload={
                "objective_id": objective_id,
                "business_id": business_id,
                "business_name": business_name,
                "epic_id": product_task.payload["epic_id"],
                "parent_task_id": product_task.task_id,
                "priority": objective.priority,
                "work_type": "engineering",
                "technical_risks": ["Integration risk", "Delivery capacity risk"],
                "architecture_actions": ["Review architecture impact", "Define implementation boundaries"],
                "created_by": "cto",
            },
            created_at=now,
            updated_at=now,
        )
        engineering_tasks.append(engineering_task)
        session.add(engineering_task)
        engineering_payload = {
            "objective_id": objective_id,
            "task_id": engineering_task.task_id,
            "work_type": "engineering",
            "title": engineering_task.title,
        }
        assigned_payload = {
            "objective_id": objective_id,
            "task_id": engineering_task.task_id,
            "assigned_agent": "cto",
        }
        engineering_step = 8 + ((task_index - 1) * 2)
        engineering_payload["business_id"] = business_id
        engineering_payload["business_name"] = business_name
        assigned_payload["business_id"] = business_id
        assigned_payload["business_name"] = business_name
        session.add(_event("cto", "execution-engine", EVENT_TASK_CREATED, engineering_payload, now, business_id))
        session.add(
            _collaboration(
                business_id,
                objective_id,
                "cto",
                "execution-engine",
                EVENT_TASK_CREATED,
                engineering_step,
                engineering_payload,
                now,
            )
        )
        session.add(_event("execution-engine", "cto", EVENT_TASK_ASSIGNED, assigned_payload, now, business_id))
        session.add(
            _collaboration(
                business_id,
                objective_id,
                "execution-engine",
                "cto",
                EVENT_TASK_ASSIGNED,
                engineering_step + 1,
                assigned_payload,
                now,
            )
        )
    return engineering_tasks


def create_objective(objective_data: ObjectiveCreate | dict) -> ObjectiveWorkflowResult:
    objective = ObjectiveCreate.model_validate(objective_data)
    from app.business.service import resolve_business

    business = resolve_business(
        business_id=objective.business_id,
        business_name=objective.business_name,
        text=f"{objective.title} {objective.description}",
    )
    objective.business_id = business.business_id
    objective.business_name = business.business_name
    now = datetime.now(timezone.utc)
    objective_id = str(uuid4())
    epics = _epics_for(objective)

    with SessionLocal() as session:
        context = _context_snapshot(session, business.business_id, business.business_name)
        objective_row = ObjectiveModel(
            objective_id=objective_id,
            business_id=business.business_id,
            title=objective.title.strip(),
            description=objective.description.strip(),
            business_name=business.business_name,
            priority=objective.priority,
            status="NEW",
            created_at=now,
        )
        session.add(objective_row)
        objective_payload = {
            "objective_id": objective_id,
            "title": objective.title,
            "business_id": business.business_id,
            "business_name": business.business_name,
            "priority": objective.priority,
            "context": context,
        }
        session.add(_event("ceo", "pm", EVENT_OBJECTIVE_CREATED, objective_payload, now, business.business_id))
        session.add(_collaboration(business.business_id, objective_id, "ceo", "pm", EVENT_OBJECTIVE_CREATED, 1, objective_payload, now))

        product_tasks = _pm_handle_objective_created(session, objective, business.business_id, business.business_name, objective_id, epics, now)
        engineering_tasks = _cto_handle_task_created(session, objective, business.business_id, business.business_name, objective_id, product_tasks, now)
        completed_payload = {
            "objective_id": objective_id,
            "business_id": business.business_id,
            "business_name": business.business_name,
            "product_task_count": len(product_tasks),
            "engineering_task_count": len(engineering_tasks),
        }
        session.add(
            _collaboration(
                business.business_id,
                objective_id,
                "cto",
                "ceo",
                EVENT_COLLABORATION_COMPLETED,
                14,
                completed_payload,
                now,
            )
        )
        session.add(_event("cto", "ceo", EVENT_COLLABORATION_COMPLETED, completed_payload, now, business.business_id))
        objective_row.status = "IN_PROGRESS"
        session.commit()
        result = _objective_detail(session, objective_id)

    return result


def _objective_detail(session, objective_id: str) -> ObjectiveDetail:
    objective_row = session.get(ObjectiveModel, objective_id)
    if objective_row is None:
        raise ValueError("Objective not found.")
    collaborations = (
        session.query(AgentCollaborationModel)
        .filter(AgentCollaborationModel.objective_id == objective_id)
        .order_by(AgentCollaborationModel.step_order)
        .all()
    )
    tasks = [
        row
        for row in session.query(TaskModel).order_by(TaskModel.created_at, TaskModel.task_id).all()
        if row.payload.get("objective_id") == objective_id
    ]
    epics = [
        collaboration.payload["title"]
        for collaboration in collaborations
        if collaboration.event_type == EVENT_EPIC_CREATED
    ]
    return ObjectiveDetail(
        objective=Objective.model_validate(objective_row),
        epics=epics,
        tasks=[Task.model_validate(task) for task in tasks],
        collaborations=[AgentCollaboration.model_validate(item) for item in collaborations],
    )


def get_objective(objective_id: str) -> Optional[ObjectiveDetail]:
    with SessionLocal() as session:
        try:
            return _objective_detail(session, objective_id)
        except ValueError:
            return None


def get_objectives(business_id: Optional[str] = None) -> List[Objective]:
    if business_id is None:
        from app.business.service import get_active_business

        business_id = get_active_business().business_id
    with SessionLocal() as session:
        rows = (
            session.query(ObjectiveModel)
            .filter(ObjectiveModel.business_id == business_id)
            .order_by(ObjectiveModel.created_at.desc())
            .all()
        )
        return [Objective.model_validate(row) for row in rows]


def get_collaborations(objective_id: Optional[str] = None, business_id: Optional[str] = None) -> List[AgentCollaboration]:
    if business_id is None:
        from app.business.service import get_active_business

        business_id = get_active_business().business_id
    with SessionLocal() as session:
        query = session.query(AgentCollaborationModel).filter(AgentCollaborationModel.business_id == business_id)
        if objective_id:
            query = query.filter(AgentCollaborationModel.objective_id == objective_id)
        rows = query.order_by(AgentCollaborationModel.created_at.desc(), AgentCollaborationModel.step_order).all()
        return [AgentCollaboration.model_validate(row) for row in rows]


def get_tasks(business_id: Optional[str] = None) -> List[Task]:
    if business_id is None:
        from app.business.service import get_active_business

        business_id = get_active_business().business_id
    with SessionLocal() as session:
        rows = (
            session.query(TaskModel)
            .filter(TaskModel.business_id == business_id)
            .order_by(TaskModel.created_at.desc(), TaskModel.task_id)
            .all()
        )
        return [Task.model_validate(row) for row in rows]

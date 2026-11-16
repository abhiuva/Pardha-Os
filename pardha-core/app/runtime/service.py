from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from app.capabilities.schemas import CapabilityExecutionRequest
from app.capabilities.service import execute_capability, list_capabilities
from app.db import SessionLocal
from app.db.models import (
    AutomationRule as AutomationRuleModel,
    BusinessTimelineEvent as BusinessTimelineEventModel,
    DepartmentRuntime as DepartmentRuntimeModel,
    ExecutionPlan as ExecutionPlanModel,
    ExecutionPlanNode as ExecutionPlanNodeModel,
    RuntimeExecution as RuntimeExecutionModel,
    RuntimeNotification as RuntimeNotificationModel,
    RuntimeQueueItem as RuntimeQueueItemModel,
    ToolRuntimeInvocation as ToolRuntimeInvocationModel,
)
from app.planning.service import list_approvals
from app.runtime.schemas import (
    AutomationRule,
    AutomationRuleCreate,
    BusinessTimelineEvent,
    DepartmentRuntime,
    QueueRequest,
    RuntimeDashboard,
    RuntimeExecution,
    RuntimeNotification,
    RuntimeQueueItem,
    RuntimeStartRequest,
    ToolRuntimeInvocation,
)


DEPARTMENTS = {
    "CEO": ["ceo.daily_brief", "diagnostics.system_health"],
    "CTO": ["cto.technical_brief", "projects.catalog", "jira.status"],
    "PM": ["pm.daily_brief", "tasks.catalog", "objectives.catalog"],
    "Marketing": ["marketing.summary"],
    "Sales": ["sales.summary"],
    "QA": ["qa.validation"],
    "Operations": ["diagnostics.system_health", "connectors.status"],
    "Customer Success": ["knowledge.search", "business.context"],
    "Engineering": ["cto.technical_brief", "projects.catalog", "executions.catalog"],
}


def ensure_departments(business_id: str) -> list[DepartmentRuntime]:
    now = datetime.now(timezone.utc)
    capabilities = {capability.capability_id for capability in list_capabilities()}
    with SessionLocal() as session:
        rows = []
        for name, capability_ids in DEPARTMENTS.items():
            department_id = f"{business_id}:{name.lower().replace(' ', '_')}"
            row = session.get(DepartmentRuntimeModel, department_id)
            if row is None:
                row = DepartmentRuntimeModel(department_id=department_id, business_id=business_id, name=name)
                session.add(row)
            usable = [capability_id for capability_id in capability_ids if capability_id in capabilities]
            row.owner = "Founder"
            row.objectives = []
            row.capabilities = usable
            row.current_work = []
            row.queue = []
            row.kpis = {"capabilities": len(usable), "success_rate": 100}
            row.health = "healthy" if usable else "degraded"
            row.current_load = 0
            row.dependencies = []
            row.updated_at = now
            rows.append(row)
        session.commit()
        return [_department(row) for row in rows]


def start_execution(request: RuntimeStartRequest) -> RuntimeExecution:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        plan = session.get(ExecutionPlanModel, request.plan_id)
        if plan is None:
            raise ValueError("Plan not found.")
        execution = RuntimeExecutionModel(
            execution_id=str(uuid4()),
            business_id=request.business_id,
            goal_id=plan.goal_id,
            plan_id=plan.plan_id,
            execution_graph=plan.graph or {},
            current_stage="queued",
            current_capability=None,
            logs=[{"event": "execution_created", "plan_id": plan.plan_id}],
            retries=0,
            progress=0,
            duration_ms=0,
            dependencies=[],
            rollback={"strategy": "mark_failed_nodes_for_retry", "safe": True},
            status="queued",
            started_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        )
        session.add(execution)
        session.add(_queue_row(request.business_id, execution.execution_id, plan.plan_id, None, request.priority, {"type": "plan_execution"}))
        _notify(session, request.business_id, "medium", "execution", "Execution Queued", f"Plan {plan.title} queued for runtime execution.", {"execution_id": execution.execution_id, "plan_id": plan.plan_id})
        _timeline(session, request.business_id, "execution_queued", "Execution Queued", plan.title, {"execution_id": execution.execution_id, "plan_id": plan.plan_id})
        _run_automation(session, request.business_id, "Execution Queued", {"execution_id": execution.execution_id, "plan_id": plan.plan_id})
        session.commit()
        session.refresh(execution)
        return _execution(execution)


def enqueue(request: QueueRequest) -> RuntimeQueueItem:
    with SessionLocal() as session:
        row = _queue_row(request.business_id, None, request.plan_id, request.capability_id, request.priority, request.payload, request.dependencies)
        session.add(row)
        _timeline(session, request.business_id, "queue_item_created", "Queue Item Created", request.capability_id or request.plan_id or "Runtime work", {"queue_id": row.queue_id})
        session.commit()
        session.refresh(row)
        return _queue(row)


def process_queue(business_id: str) -> list[RuntimeExecution]:
    with SessionLocal() as session:
        rows = (
            session.query(RuntimeQueueItemModel)
            .filter(RuntimeQueueItemModel.business_id == business_id, RuntimeQueueItemModel.status == "queued")
            .order_by(RuntimeQueueItemModel.priority.desc(), RuntimeQueueItemModel.created_at.asc())
            .all()
        )
    results = []
    for row in rows:
        if row.execution_id:
            results.append(run_execution(row.execution_id))
        elif row.capability_id:
            results.append(_run_single_capability(row))
        with SessionLocal() as session:
            fresh = session.get(RuntimeQueueItemModel, row.queue_id)
            if fresh is not None:
                fresh.status = "completed"
                fresh.updated_at = datetime.now(timezone.utc)
                session.commit()
    return results


def run_execution(execution_id: str) -> RuntimeExecution:
    started = perf_counter()
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        execution = session.get(RuntimeExecutionModel, execution_id)
        if execution is None:
            raise ValueError("Execution not found.")
        plan = session.get(ExecutionPlanModel, execution.plan_id)
        nodes = session.query(ExecutionPlanNodeModel).filter(ExecutionPlanNodeModel.plan_id == execution.plan_id).order_by(ExecutionPlanNodeModel.created_at.asc()).all()
        execution.status = "running"
        execution.current_stage = "running"
        execution.started_at = execution.started_at or now
        logs = list(execution.logs or [])
        completed = 0
        for node in nodes:
            if node.approval_required and node.status not in {"completed", "approved"}:
                node.status = "waiting"
                logs.append({"event": "waiting_approval", "node_id": node.node_id, "title": node.title})
                continue
            if node.capability_id:
                execution.current_capability = node.capability_id
                execution.current_stage = node.title
                result = execute_capability(CapabilityExecutionRequest(intent=node.node_type, capability_id=node.capability_id, business_id=execution.business_id, payload={"runtime_execution_id": execution.execution_id, "plan_id": execution.plan_id, "node_id": node.node_id}))
                session.add(ToolRuntimeInvocationModel(invocation_id=str(uuid4()), business_id=execution.business_id, tool_name=_tool_name(node.capability_id), capability_id=node.capability_id, execution_id=execution.execution_id, status=result.status, input_payload={"node_id": node.node_id}, output_payload=result.output, error=result.error, duration_ms=result.runtime_ms, created_at=datetime.now(timezone.utc)))
                node.output = {"runtime_execution_id": execution.execution_id, "capability_execution_id": result.execution_id, "status": result.status}
                node.status = "completed" if result.status == "succeeded" else "failed"
                logs.append({"event": "tool_executed", "capability_id": node.capability_id, "status": result.status})
            else:
                node.status = "completed"
                logs.append({"event": "node_completed", "node_id": node.node_id})
            node.updated_at = datetime.now(timezone.utc)
            completed += 1 if node.status == "completed" else 0
        total = max(1, len(nodes))
        execution.progress = int(completed / total * 100)
        execution.logs = logs
        execution.duration_ms = max(1, int((perf_counter() - started) * 1000))
        execution.status = "completed" if completed == total else "waiting"
        execution.current_stage = "completed" if execution.status == "completed" else "waiting"
        execution.completed_at = datetime.now(timezone.utc) if execution.status == "completed" else None
        execution.updated_at = datetime.now(timezone.utc)
        if plan is not None:
            plan.status = execution.status
            plan.progress = execution.progress
            plan.updated_at = execution.updated_at
        _notify(session, execution.business_id, "high" if execution.status == "failed" else "medium", "execution", f"Execution {execution.status.title()}", f"Runtime execution {execution.execution_id} is {execution.status}.", {"execution_id": execution.execution_id})
        _timeline(session, execution.business_id, f"execution_{execution.status}", f"Execution {execution.status.title()}", execution.execution_id, {"progress": execution.progress})
        _run_automation(session, execution.business_id, f"Execution {execution.status.title()}", {"execution_id": execution.execution_id, "status": execution.status})
        session.commit()
        session.refresh(execution)
        return _execution(execution)


def retry_execution(execution_id: str) -> RuntimeExecution:
    with SessionLocal() as session:
        execution = session.get(RuntimeExecutionModel, execution_id)
        if execution is None:
            raise ValueError("Execution not found.")
        execution.retries += 1
        execution.status = "queued"
        execution.current_stage = "retry_queued"
        logs = list(execution.logs or [])
        logs.append({"event": "retry_queued", "retry": execution.retries})
        execution.logs = logs
        execution.updated_at = datetime.now(timezone.utc)
        session.add(_queue_row(execution.business_id, execution.execution_id, execution.plan_id, None, 80, {"type": "retry"}))
        _notify(session, execution.business_id, "medium", "recovery", "Retry Queued", f"Retry queued for execution {execution.execution_id}.", {"execution_id": execution.execution_id})
        session.commit()
    return run_execution(execution_id)


def rollback_execution(execution_id: str) -> RuntimeExecution:
    with SessionLocal() as session:
        execution = session.get(RuntimeExecutionModel, execution_id)
        if execution is None:
            raise ValueError("Execution not found.")
        execution.status = "cancelled"
        execution.current_stage = "rolled_back"
        execution.rollback = {"completed": True, "strategy": "mark_execution_cancelled", "rolled_back_at": datetime.now(timezone.utc).isoformat()}
        logs = list(execution.logs or [])
        logs.append({"event": "rollback_completed", "strategy": execution.rollback["strategy"]})
        execution.logs = logs
        execution.updated_at = datetime.now(timezone.utc)
        _notify(session, execution.business_id, "high", "rollback", "Rollback Completed", f"Execution {execution.execution_id} was rolled back.", {"execution_id": execution.execution_id})
        _timeline(session, execution.business_id, "rollback_completed", "Rollback Completed", execution.execution_id, execution.rollback)
        session.commit()
        session.refresh(execution)
        return _execution(execution)


def list_executions(business_id: str | None = None) -> list[RuntimeExecution]:
    with SessionLocal() as session:
        query = session.query(RuntimeExecutionModel)
        if business_id:
            query = query.filter(RuntimeExecutionModel.business_id == business_id)
        return [_execution(row) for row in query.order_by(RuntimeExecutionModel.created_at.desc()).limit(100).all()]


def departments(business_id: str) -> list[DepartmentRuntime]:
    return ensure_departments(business_id)


def queue_items(business_id: str | None = None) -> list[RuntimeQueueItem]:
    with SessionLocal() as session:
        query = session.query(RuntimeQueueItemModel)
        if business_id:
            query = query.filter(RuntimeQueueItemModel.business_id == business_id)
        return [_queue(row) for row in query.order_by(RuntimeQueueItemModel.priority.desc(), RuntimeQueueItemModel.created_at.desc()).limit(100).all()]


def notifications(business_id: str | None = None, status: str | None = None) -> list[RuntimeNotification]:
    with SessionLocal() as session:
        query = session.query(RuntimeNotificationModel)
        if business_id:
            query = query.filter(RuntimeNotificationModel.business_id == business_id)
        if status:
            query = query.filter(RuntimeNotificationModel.status == status)
        return [_notification(row) for row in query.order_by(RuntimeNotificationModel.created_at.desc()).limit(100).all()]


def mark_notification(notification_id: str, action: str) -> RuntimeNotification:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = session.get(RuntimeNotificationModel, notification_id)
        if row is None:
            raise ValueError("Notification not found.")
        if action == "read":
            row.status = "read"
            row.read_at = now
        elif action == "archive":
            row.status = "archived"
            row.archived_at = now
        row.payload = row.payload or {}
        session.commit()
        session.refresh(row)
        return _notification(row)


def create_rule(request: AutomationRuleCreate) -> AutomationRule:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = AutomationRuleModel(rule_id=str(uuid4()), business_id=request.business_id, name=request.name, trigger_event=request.trigger_event, action=request.action, enabled=1, priority=request.priority, payload=request.payload, created_at=now, updated_at=now)
        session.add(row)
        session.commit()
        session.refresh(row)
        return _rule(row)


def rules(business_id: str | None = None) -> list[AutomationRule]:
    with SessionLocal() as session:
        query = session.query(AutomationRuleModel)
        if business_id:
            query = query.filter((AutomationRuleModel.business_id == business_id) | (AutomationRuleModel.business_id.is_(None)))
        return [_rule(row) for row in query.order_by(AutomationRuleModel.priority.desc()).all()]


def timeline(business_id: str) -> list[BusinessTimelineEvent]:
    with SessionLocal() as session:
        rows = session.query(BusinessTimelineEventModel).filter(BusinessTimelineEventModel.business_id == business_id).order_by(BusinessTimelineEventModel.created_at.desc()).limit(100).all()
        return [_timeline_schema(row) for row in rows]


def dashboard(business_id: str) -> RuntimeDashboard:
    execs = list_executions(business_id)
    invocations = _tool_usage(business_id)
    failures = len([item for item in execs if item.status == "failed"])
    completed = len([item for item in execs if item.status == "completed"])
    return RuntimeDashboard(
        departments=departments(business_id),
        executions=execs,
        queue=queue_items(business_id),
        approvals=[item.model_dump(mode="json") for item in list_approvals(business_id=business_id, status=None)],
        notifications=notifications(business_id),
        business_timeline=timeline(business_id),
        observability={"executions": len(execs), "success_rate": int(completed / max(1, len(execs)) * 100), "failures": failures, "tool_usage": invocations, "department_load": {item.name: item.current_load for item in departments(business_id)}},
    )


def _run_single_capability(row: RuntimeQueueItemModel) -> RuntimeExecution:
    request = RuntimeStartRequest(business_id=row.business_id, plan_id=row.plan_id or "", priority=row.priority)
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        execution = RuntimeExecutionModel(execution_id=str(uuid4()), business_id=row.business_id, goal_id=None, plan_id=row.plan_id, execution_graph={"nodes": [{"capability_id": row.capability_id}]}, current_stage="running", current_capability=row.capability_id, logs=[], retries=row.retry_count, progress=0, duration_ms=0, dependencies=row.dependencies or [], rollback={"strategy": "cancel"}, status="running", started_at=now, completed_at=None, created_at=now, updated_at=now)
        session.add(execution)
        session.commit()
        execution_id = execution.execution_id
    result = execute_capability(CapabilityExecutionRequest(intent="tool_runtime", capability_id=row.capability_id, business_id=row.business_id, payload=row.payload or {}))
    with SessionLocal() as session:
        execution = session.get(RuntimeExecutionModel, execution_id)
        execution.status = "completed" if result.status == "succeeded" else "failed"
        execution.progress = 100 if result.status == "succeeded" else 0
        execution.duration_ms = result.runtime_ms
        execution.completed_at = datetime.now(timezone.utc)
        execution.updated_at = execution.completed_at
        execution.logs = [{"event": "capability_executed", "capability_id": row.capability_id, "status": result.status}]
        session.add(ToolRuntimeInvocationModel(invocation_id=str(uuid4()), business_id=row.business_id, tool_name=_tool_name(row.capability_id or ""), capability_id=row.capability_id, execution_id=execution.execution_id, status=result.status, input_payload=row.payload or {}, output_payload=result.output, error=result.error, duration_ms=result.runtime_ms, created_at=datetime.now(timezone.utc)))
        session.commit()
        session.refresh(execution)
        return _execution(execution)


def _run_automation(session, business_id: str, trigger_event: str, payload: dict) -> None:
    rows = session.query(AutomationRuleModel).filter(AutomationRuleModel.enabled == 1).all()
    for row in rows:
        if row.business_id not in {None, business_id}:
            continue
        if row.trigger_event.lower() not in trigger_event.lower():
            continue
        if row.action == "notify_founder":
            _notify(session, business_id, "medium", "automation", row.name, f"Automation fired: {row.name}", payload)


def _queue_row(business_id: str, execution_id: str | None, plan_id: str | None, capability_id: str | None, priority: int, payload: dict, dependencies: list[str] | None = None) -> RuntimeQueueItemModel:
    now = datetime.now(timezone.utc)
    return RuntimeQueueItemModel(queue_id=str(uuid4()), business_id=business_id, execution_id=execution_id, plan_id=plan_id, capability_id=capability_id, priority=priority, dependencies=dependencies or [], retry_count=0, timeout_ms=30000, scheduled_for=None, recurring=0, delay_until=None, status="queued", payload=payload, created_at=now, updated_at=now)


def _notify(session, business_id: str, priority: str, category: str, title: str, message: str, payload: dict) -> None:
    session.add(RuntimeNotificationModel(notification_id=str(uuid4()), business_id=business_id, priority=priority, category=category, title=title, message=message, status="unread", payload=payload, created_at=datetime.now(timezone.utc)))


def _timeline(session, business_id: str, event_type: str, title: str, detail: str, payload: dict) -> None:
    session.add(BusinessTimelineEventModel(timeline_event_id=str(uuid4()), business_id=business_id, event_type=event_type, title=title, detail=detail, source="runtime", payload=payload, created_at=datetime.now(timezone.utc)))


def _tool_usage(business_id: str) -> dict:
    with SessionLocal() as session:
        rows = session.query(ToolRuntimeInvocationModel).filter(ToolRuntimeInvocationModel.business_id == business_id).all()
        usage = {}
        for row in rows:
            usage[row.tool_name] = usage.get(row.tool_name, 0) + 1
        return usage


def _tool_name(capability_id: str) -> str:
    if "jira" in capability_id:
        return "Jira"
    if "email" in capability_id or "gmail" in capability_id or "outlook" in capability_id:
        return "Email"
    if "whatsapp" in capability_id:
        return "WhatsApp"
    if "calendar" in capability_id:
        return "Calendar"
    if "projects" in capability_id or "vscode" in capability_id or "cto" in capability_id:
        return "Developer Tools"
    if "diagnostics" in capability_id:
        return "Diagnostics"
    return "Capability"


def _execution(row: RuntimeExecutionModel) -> RuntimeExecution:
    return RuntimeExecution(execution_id=row.execution_id, business_id=row.business_id, goal_id=row.goal_id, plan_id=row.plan_id, execution_graph=row.execution_graph or {}, current_stage=row.current_stage, current_capability=row.current_capability, logs=row.logs or [], retries=row.retries, progress=row.progress, duration_ms=row.duration_ms, dependencies=row.dependencies or [], rollback=row.rollback or {}, status=row.status, started_at=row.started_at, completed_at=row.completed_at, created_at=row.created_at, updated_at=row.updated_at)


def _department(row: DepartmentRuntimeModel) -> DepartmentRuntime:
    return DepartmentRuntime(department_id=row.department_id, business_id=row.business_id, name=row.name, owner=row.owner, objectives=row.objectives or [], capabilities=row.capabilities or [], current_work=row.current_work or [], queue=row.queue or [], kpis=row.kpis or {}, health=row.health, current_load=row.current_load, dependencies=row.dependencies or [], updated_at=row.updated_at)


def _queue(row: RuntimeQueueItemModel) -> RuntimeQueueItem:
    return RuntimeQueueItem(queue_id=row.queue_id, business_id=row.business_id, execution_id=row.execution_id, plan_id=row.plan_id, capability_id=row.capability_id, priority=row.priority, dependencies=row.dependencies or [], retry_count=row.retry_count, timeout_ms=row.timeout_ms, scheduled_for=row.scheduled_for, recurring=bool(row.recurring), delay_until=row.delay_until, status=row.status, payload=row.payload or {}, created_at=row.created_at, updated_at=row.updated_at)


def _notification(row: RuntimeNotificationModel) -> RuntimeNotification:
    return RuntimeNotification(notification_id=row.notification_id, business_id=row.business_id, priority=row.priority, category=row.category, title=row.title, message=row.message, status=row.status, payload=row.payload or {}, created_at=row.created_at, read_at=row.read_at, archived_at=row.archived_at)


def _rule(row: AutomationRuleModel) -> AutomationRule:
    return AutomationRule(rule_id=row.rule_id, business_id=row.business_id, name=row.name, trigger_event=row.trigger_event, action=row.action, enabled=bool(row.enabled), priority=row.priority, payload=row.payload or {}, created_at=row.created_at, updated_at=row.updated_at)


def _timeline_schema(row: BusinessTimelineEventModel) -> BusinessTimelineEvent:
    return BusinessTimelineEvent(timeline_event_id=row.timeline_event_id, business_id=row.business_id, event_type=row.event_type, title=row.title, detail=row.detail, source=row.source, payload=row.payload or {}, created_at=row.created_at)

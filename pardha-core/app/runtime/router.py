from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

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
)
from app.runtime.service import (
    create_rule,
    dashboard,
    departments,
    enqueue,
    list_executions,
    mark_notification,
    notifications,
    process_queue,
    queue_items,
    retry_execution,
    rollback_execution,
    rules,
    run_execution,
    start_execution,
    timeline,
)

router = APIRouter(prefix="/runtime", tags=["universal-execution-runtime"])


@router.post("/executions", response_model=RuntimeExecution, status_code=status.HTTP_201_CREATED)
def start_execution_route(request: RuntimeStartRequest):
    try:
        return start_execution(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/executions", response_model=list[RuntimeExecution])
def executions_route(business_id: str | None = Query(default=None)):
    return list_executions(business_id=business_id)


@router.post("/executions/{execution_id}/run", response_model=RuntimeExecution)
def run_execution_route(execution_id: str):
    try:
        return run_execution(execution_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/executions/{execution_id}/retry", response_model=RuntimeExecution)
def retry_execution_route(execution_id: str):
    try:
        return retry_execution(execution_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/executions/{execution_id}/rollback", response_model=RuntimeExecution)
def rollback_execution_route(execution_id: str):
    try:
        return rollback_execution(execution_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/queue", response_model=RuntimeQueueItem, status_code=status.HTTP_201_CREATED)
def enqueue_route(request: QueueRequest):
    return enqueue(request)


@router.get("/queue", response_model=list[RuntimeQueueItem])
def queue_route(business_id: str | None = Query(default=None)):
    return queue_items(business_id=business_id)


@router.post("/queue/process", response_model=list[RuntimeExecution])
def process_queue_route(business_id: str = Query(...)):
    return process_queue(business_id)


@router.get("/departments", response_model=list[DepartmentRuntime])
def departments_route(business_id: str = Query(...)):
    return departments(business_id)


@router.get("/notifications", response_model=list[RuntimeNotification])
def notifications_route(business_id: str | None = Query(default=None), status_filter: str | None = Query(default=None, alias="status")):
    return notifications(business_id=business_id, status=status_filter)


@router.post("/notifications/{notification_id}/read", response_model=RuntimeNotification)
def read_notification_route(notification_id: str):
    try:
        return mark_notification(notification_id, "read")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/notifications/{notification_id}/archive", response_model=RuntimeNotification)
def archive_notification_route(notification_id: str):
    try:
        return mark_notification(notification_id, "archive")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/automation/rules", response_model=AutomationRule, status_code=status.HTTP_201_CREATED)
def create_rule_route(request: AutomationRuleCreate):
    return create_rule(request)


@router.get("/automation/rules", response_model=list[AutomationRule])
def rules_route(business_id: str | None = Query(default=None)):
    return rules(business_id=business_id)


@router.get("/timeline", response_model=list[BusinessTimelineEvent])
def timeline_route(business_id: str = Query(...)):
    return timeline(business_id)


@router.get("/dashboard", response_model=RuntimeDashboard)
def dashboard_route(business_id: str = Query(...)):
    return dashboard(business_id)

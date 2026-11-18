from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.planning.schemas import (
    ApprovalDecision,
    DailyExecutivePlan,
    ExecutionPlan,
    GoalKPI,
    PlanApproval,
    PlanExecution,
    PlanRequest,
    PlanningGoal,
    PlanningResult,
    PlanningTimelineEvent,
)
from app.planning.service import (
    PlanStateConflict,
    approve_plan,
    create_plan,
    daily_executive_plan,
    execute_plan,
    get_plan,
    goal_kpis,
    list_approvals,
    list_goals,
    list_plans,
    plan_timeline,
    reject_plan,
)

router = APIRouter(prefix="/planning", tags=["autonomous-planning"])


@router.post("/plan", response_model=PlanningResult, status_code=status.HTTP_201_CREATED)
def create_plan_route(request: PlanRequest):
    return create_plan(request)


@router.get("/goals", response_model=list[PlanningGoal])
def goals_route(business_id: str | None = Query(default=None)):
    return list_goals(business_id=business_id)


@router.get("/plans", response_model=list[ExecutionPlan])
def plans_route(business_id: str | None = Query(default=None)):
    return list_plans(business_id=business_id)


@router.get("/plans/{plan_id}", response_model=PlanningResult)
def plan_route(plan_id: str):
    try:
        return get_plan(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/approve", response_model=PlanningResult)
def approve_plan_route(plan_id: str, decision: ApprovalDecision):
    try:
        return approve_plan(plan_id, decision)
    except PlanStateConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/reject", response_model=PlanningResult)
def reject_plan_route(plan_id: str, decision: ApprovalDecision):
    try:
        return reject_plan(plan_id, decision)
    except PlanStateConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/plans/{plan_id}/execute", response_model=PlanExecution, status_code=status.HTTP_201_CREATED)
def execute_plan_route(plan_id: str):
    try:
        return execute_plan(plan_id)
    except PlanStateConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/approvals", response_model=list[PlanApproval])
def approvals_route(business_id: str | None = Query(default=None), status_filter: str | None = Query(default="pending", alias="status")):
    return list_approvals(business_id=business_id, status=status_filter)


@router.get("/daily", response_model=DailyExecutivePlan)
def daily_route(business_id: str = Query(...)):
    return daily_executive_plan(business_id)


@router.get("/goals/{goal_id}/timeline", response_model=list[PlanningTimelineEvent])
def timeline_route(goal_id: str):
    return plan_timeline(goal_id)


@router.get("/goals/{goal_id}/kpis", response_model=list[GoalKPI])
def kpis_route(goal_id: str):
    return goal_kpis(goal_id)

from typing import Optional

from fastapi import APIRouter, Query, status

from app.collaboration.schemas import AgentCollaboration, Objective, ObjectiveCreate, ObjectiveDetail, ObjectiveWorkflowResult, Task
from app.collaboration.service import create_objective, get_collaborations, get_objective, get_objectives, get_tasks


router = APIRouter(tags=["collaboration"])


@router.post("/objectives", response_model=ObjectiveWorkflowResult, status_code=status.HTTP_201_CREATED)
def create_objective_route(objective: ObjectiveCreate):
    return create_objective(objective)


@router.get("/objectives", response_model=list[Objective])
def get_objectives_route(business_id: Optional[str] = Query(default=None)):
    return get_objectives(business_id=business_id)


@router.get("/objectives/{objective_id}", response_model=ObjectiveDetail)
def get_objective_route(objective_id: str):
    objective = get_objective(objective_id)
    if objective is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objective not found.")
    return objective


@router.get("/collaborations", response_model=list[AgentCollaboration])
def get_collaborations_route(
    objective_id: Optional[str] = Query(default=None),
    business_id: Optional[str] = Query(default=None),
):
    return get_collaborations(objective_id=objective_id, business_id=business_id)


@router.get("/tasks", response_model=list[Task])
def get_tasks_route(business_id: Optional[str] = Query(default=None)):
    return get_tasks(business_id=business_id)

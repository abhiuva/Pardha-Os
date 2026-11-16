from fastapi import APIRouter
from typing import Optional

from app.agents.executions import AgentExecution, get_executions


router = APIRouter(prefix="/agents/executions", tags=["agent-executions"])


@router.get("", response_model=list[AgentExecution])
def list_agent_executions(business_id: Optional[str] = None):
    return get_executions(business_id=business_id)


@router.get("/{agent_name}", response_model=list[AgentExecution])
def list_agent_executions_by_name(agent_name: str, business_id: Optional[str] = None):
    return get_executions(agent_name=agent_name, business_id=business_id)

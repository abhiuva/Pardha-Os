from fastapi import APIRouter

from app.reasoning.schemas import AgentReasoning, ReasoningRequest
from app.reasoning.gateway import reasoning_gateway
from app.reasoning.service import get_reasoning, manual_reason_for_agent


router = APIRouter(prefix="/agents", tags=["reasoning"])
health_router = APIRouter(tags=["reasoning"])


@health_router.get("/reasoning/health")
def get_reasoning_health():
    return reasoning_gateway.health()


@router.get("/ceo/reasoning", response_model=list[AgentReasoning])
def get_ceo_reasoning(business_id: str | None = None):
    return get_reasoning("ceo", business_id=business_id)


@router.get("/cto/reasoning", response_model=list[AgentReasoning])
def get_cto_reasoning(business_id: str | None = None):
    return get_reasoning("cto", business_id=business_id)


@router.get("/pm/reasoning", response_model=list[AgentReasoning])
def get_pm_reasoning(business_id: str | None = None):
    return get_reasoning("pm", business_id=business_id)


@router.post("/ceo/reason", response_model=AgentReasoning)
def reason_as_ceo(request: ReasoningRequest = ReasoningRequest()):
    return manual_reason_for_agent("ceo", request.model, business_id=request.business_id)


@router.post("/cto/reason", response_model=AgentReasoning)
def reason_as_cto(request: ReasoningRequest = ReasoningRequest()):
    return manual_reason_for_agent("cto", request.model, business_id=request.business_id)


@router.post("/pm/reason", response_model=AgentReasoning)
def reason_as_pm(request: ReasoningRequest = ReasoningRequest()):
    return manual_reason_for_agent("pm", request.model, business_id=request.business_id)

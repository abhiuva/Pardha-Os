from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.capabilities.schemas import (
    Capability,
    CapabilityExecutionRequest,
    CapabilityExecutionResult,
    CapabilityGraph,
    CapabilityHealth,
    CapabilityRegistration,
    CapabilitySearchRequest,
    CapabilitySearchResponse,
    RegistryValidationReport,
)
from app.capabilities.service import (
    capability_graph,
    capability_health,
    execute_capability,
    get_capability,
    list_capabilities,
    register_capability,
    search_capabilities,
    unregister_capability,
    validation_report,
)

router = APIRouter(tags=["intelligence-kernel"])


@router.get("/capabilities", response_model=list[Capability])
def capabilities_route(include_unregistered: bool = Query(default=False)):
    return list_capabilities(include_unregistered=include_unregistered)


@router.get("/capabilities/health", response_model=CapabilityHealth)
def capability_health_route():
    return capability_health()


@router.get("/capabilities/search", response_model=CapabilitySearchResponse)
def capability_search_route(
    intent: str = Query(default=""),
    query: str = Query(default=""),
    business_domain: str | None = Query(default=None),
    business_id: str | None = Query(default=None),
    max_results: int = Query(default=10, ge=1, le=50),
):
    return search_capabilities(
        CapabilitySearchRequest(
            intent=intent,
            query=query,
            business_domain=business_domain,
            business_id=business_id,
            max_results=max_results,
        )
    )


@router.get("/capabilities/graph", response_model=CapabilityGraph)
def capability_graph_route():
    return capability_graph()


@router.get("/capabilities/validation", response_model=RegistryValidationReport)
def capability_validation_route():
    return validation_report()


@router.get("/capabilities/{capability_id}", response_model=Capability)
def capability_route(capability_id: str):
    capability = get_capability(capability_id)
    if capability is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability not found.")
    return capability


@router.post("/capabilities/register", response_model=Capability, status_code=status.HTTP_201_CREATED)
def capability_register_route(request: CapabilityRegistration):
    return register_capability(request)


@router.post("/capabilities/unregister")
def capability_unregister_route(capability_id: str = Query(...)):
    result = unregister_capability(capability_id)
    if not result["unregistered"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability not found.")
    return result


@router.post("/kernel/execute", response_model=CapabilityExecutionResult, status_code=status.HTTP_201_CREATED)
def kernel_execute_route(request: CapabilityExecutionRequest):
    try:
        result = execute_capability(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if result.status == "denied":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=result.error)
    if result.status == "failed":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error)
    return result


@router.post("/kernel/resolve", response_model=CapabilitySearchResponse)
def kernel_resolve_route(request: CapabilitySearchRequest):
    return search_capabilities(request)

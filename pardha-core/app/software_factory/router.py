from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.software_factory.schemas import (
    ApprovalDecision,
    ArtifactUpdate,
    EngineeringDashboard,
    FactoryRequest,
    FactoryValidationReport,
    ReverseEngineeringReport,
    ReverseEngineeringRequest,
    SoftwareFactoryArtifact,
    SoftwareFactoryDelivery,
)
from app.software_factory.service import (
    create_delivery,
    dashboard,
    decide_approval,
    get_delivery,
    list_deliveries,
    reverse_engineer,
    update_artifact,
    validation_report,
)

router = APIRouter(prefix="/software-factory", tags=["software-factory"])


@router.post("/requirements", response_model=SoftwareFactoryDelivery, status_code=status.HTTP_201_CREATED)
def create_requirement_route(request: FactoryRequest):
    try:
        return create_delivery(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/requirements", response_model=list[SoftwareFactoryDelivery])
def requirements_route(business_id: str | None = Query(default=None)):
    return list_deliveries(business_id=business_id)


@router.get("/requirements/{requirement_id}", response_model=SoftwareFactoryDelivery)
def requirement_route(requirement_id: str):
    try:
        return get_delivery(requirement_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/artifacts/{artifact_id}", response_model=SoftwareFactoryArtifact)
def update_artifact_route(artifact_id: str, update: ArtifactUpdate):
    try:
        return update_artifact(artifact_id, update)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/approve", response_model=SoftwareFactoryDelivery)
def approve_route(approval_id: str, decision: ApprovalDecision):
    try:
        return decide_approval(approval_id, "approved", decision.decided_by, decision.comment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/reject", response_model=SoftwareFactoryDelivery)
def reject_route(approval_id: str, decision: ApprovalDecision):
    try:
        return decide_approval(approval_id, "rejected", decision.decided_by, decision.comment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/dashboard", response_model=EngineeringDashboard)
def dashboard_route(business_id: str = Query(...)):
    return dashboard(business_id)


@router.get("/validation", response_model=FactoryValidationReport)
def validation_route(business_id: str | None = Query(default=None)):
    return validation_report(business_id=business_id)


@router.post("/reverse-engineer", response_model=ReverseEngineeringReport)
def reverse_engineer_route(request: ReverseEngineeringRequest):
    return reverse_engineer(request)

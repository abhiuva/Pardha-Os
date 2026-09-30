from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.hubspot.schemas import HubSpotConfigRequest, HubSpotConfigStatus, HubSpotLeadPayload, HubSpotSyncRequest, HubSpotSyncResult
from app.hubspot.service import build_lead_payload, configure_hubspot, hubspot_status, sync_history, sync_lead


router = APIRouter(prefix="/hubspot", tags=["hubspot"])


@router.get("/status", response_model=HubSpotConfigStatus)
def get_hubspot_status(business_id: str | None = Query(default=None)):
    return hubspot_status(business_id)


@router.post("/config", response_model=HubSpotConfigStatus)
def configure_hubspot_connector(request: HubSpotConfigRequest):
    return configure_hubspot(request)


@router.get("/leads/{lead_id}/payload", response_model=HubSpotLeadPayload)
def get_hubspot_lead_payload(lead_id: str):
    try:
        return build_lead_payload(lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sync/lead", response_model=HubSpotSyncResult)
def sync_hubspot_lead(request: HubSpotSyncRequest):
    try:
        return sync_lead(request.lead_id, allow_write=request.allow_write)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sync/history", response_model=list[HubSpotSyncResult])
def get_hubspot_sync_history(business_id: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=200)):
    return sync_history(business_id=business_id, limit=limit)

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HubSpotConfigRequest(BaseModel):
    business_id: Optional[str] = None
    portal_id: Optional[str] = None
    write_mode: str = "disabled"
    scopes: List[str] = Field(default_factory=lambda: ["crm.objects.contacts.read", "crm.objects.companies.read", "crm.objects.deals.read"])
    configuration: Dict[str, Any] = Field(default_factory=dict)
    secret_reference: Optional[str] = None


class HubSpotConfigStatus(BaseModel):
    business_id: str
    status: str
    portal_id: Optional[str] = None
    write_mode: str
    scopes: List[str] = Field(default_factory=list)
    authentication_status: str
    environment_valid: bool
    missing_environment: List[str] = Field(default_factory=list)
    last_checked_at: Optional[datetime] = None
    message: str


class HubSpotLeadPayload(BaseModel):
    lead_id: str
    duplicate_key: str
    contact: Dict[str, Any]
    company: Dict[str, Any]
    deal: Dict[str, Any]


class HubSpotSyncRequest(BaseModel):
    lead_id: str
    allow_write: bool = False


class HubSpotSyncResult(BaseModel):
    sync_id: str
    lead_id: str
    action: str
    sync_status: str
    duplicate: bool
    duplicate_key: Optional[str] = None
    retry_count: int = 0
    retryable: bool = False
    error: Optional[str] = None
    hubspot_ids: Dict[str, Optional[str]] = Field(default_factory=dict)
    payload: HubSpotLeadPayload
    safe_mode: bool
    message: str
    updated_at: datetime


class HubSpotSyncHistory(BaseModel):
    records: List[HubSpotSyncResult]

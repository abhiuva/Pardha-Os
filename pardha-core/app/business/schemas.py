from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class BusinessCreate(BaseModel):
    tenant_id: Optional[str] = None
    business_name: str = Field(..., min_length=1)
    business_type: str = Field(default="company", min_length=1)
    description: str = ""
    status: str = "active"


class Business(BusinessCreate):
    model_config = ConfigDict(from_attributes=True)

    business_id: str
    created_at: datetime


class ContextSwitchRequest(BaseModel):
    business_id: Optional[str] = None
    business_name: Optional[str] = None


class BusinessContext(BaseModel):
    active_business: Business
    counts: Dict[str, int] = Field(default_factory=dict)
    recent: Dict[str, Any] = Field(default_factory=dict)

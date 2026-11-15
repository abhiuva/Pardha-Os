from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CapabilityRegistration(BaseModel):
    capability_id: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    version: str = "1.0.0"
    description: str
    supported_intents: List[str] = Field(default_factory=list)
    business_domains: List[str] = Field(default_factory=list)
    required_inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    health: str = "healthy"
    supports_hitl: bool = False
    supports_streaming: bool = False
    supports_learning: bool = False
    priority: int = Field(default=50, ge=0, le=100)
    estimated_runtime_ms: int = Field(default=100, ge=0)
    registration_method: str = "manual"
    current_status: str = "registered"
    planner_interface: Dict[str, Any] = Field(default_factory=dict)
    execution_adapter: Optional[str] = None


class Capability(CapabilityRegistration):
    execution_count: int
    last_executed_at: Optional[datetime]
    registered_at: datetime
    updated_at: datetime


class CapabilityCandidate(BaseModel):
    capability: Capability
    confidence: int
    score: int
    reasons: List[str]


class CapabilitySearchRequest(BaseModel):
    intent: str = ""
    query: str = ""
    business_domain: Optional[str] = None
    business_id: Optional[str] = None
    required_inputs: List[str] = Field(default_factory=list)
    max_results: int = Field(default=10, ge=1, le=50)


class CapabilitySearchResponse(BaseModel):
    intent: str
    query: str
    candidates: List[CapabilityCandidate]


class CapabilityHealth(BaseModel):
    total: int
    healthy: int
    degraded: int
    unavailable: int
    unknown: int
    capabilities: List[Capability]


class CapabilityExecutionRequest(BaseModel):
    intent: str = Field(..., min_length=1)
    capability_id: Optional[str] = None
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    required_inputs: List[str] = Field(default_factory=list)


class CapabilityExecutionResult(BaseModel):
    execution_id: str
    capability_id: str
    status: str
    confidence: int
    runtime_ms: int
    output: Any
    error: Optional[str] = None


class CapabilityGraph(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class RegistryValidationReport(BaseModel):
    total_capabilities: int
    registered_existing_capabilities: int
    missing_required_fields: List[str]
    unhealthy_capabilities: List[str]
    duplicate_ids: List[str]
    ready: bool

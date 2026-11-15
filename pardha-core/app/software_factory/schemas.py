from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FactoryRequest(BaseModel):
    business_id: str
    requirement: str = Field(..., min_length=5)
    requester: str = "Founder"
    methodology: str = "scrum"
    stack: List[str] = Field(default_factory=list)


class ArtifactUpdate(BaseModel):
    content: Dict[str, Any] = Field(default_factory=dict)
    edited_by: str = "Founder"
    comment: str = "Edited from Product Engineering Factory."


class ApprovalDecision(BaseModel):
    decided_by: str = "Founder"
    comment: str = ""


class ReverseEngineeringRequest(BaseModel):
    business_id: str
    target: str = Field(..., min_length=2)
    target_type: str = "repository"


class SoftwareFactoryRequirement(BaseModel):
    requirement_id: str
    business_id: str
    title: str
    request: str
    requester: str
    methodology: str
    stack: List[str]
    status: str
    current_stage: str
    discovery: Dict[str, Any]
    orchestration_graph: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SoftwareFactoryArtifact(BaseModel):
    artifact_id: str
    requirement_id: str
    business_id: str
    artifact_type: str
    title: str
    version: int
    status: str
    content: Dict[str, Any]
    editable: bool
    created_at: datetime
    updated_at: datetime


class SoftwareFactoryApproval(BaseModel):
    approval_id: str
    requirement_id: str
    artifact_id: Optional[str]
    business_id: str
    approval_type: str
    title: str
    detail: str
    risk_level: str
    status: str
    requested_by: str
    decided_by: Optional[str]
    decision_comment: Optional[str]
    created_at: datetime
    decided_at: Optional[datetime]


class SoftwareFactoryDelivery(BaseModel):
    requirement: SoftwareFactoryRequirement
    artifacts: List[SoftwareFactoryArtifact]
    approvals: List[SoftwareFactoryApproval]
    lifecycle: List[Dict[str, Any]]
    validation: Dict[str, Any]


class EngineeringDashboard(BaseModel):
    business_id: str
    current_sprint: Dict[str, Any]
    velocity: Dict[str, Any]
    open_stories: int
    blocked_stories: int
    build_status: str
    qa_status: str
    code_reviews: Dict[str, Any]
    release_readiness: Dict[str, Any]
    technical_debt: List[str]
    current_risks: List[str]
    active_requirements: List[SoftwareFactoryRequirement]
    pending_approvals: List[SoftwareFactoryApproval]


class FactoryValidationReport(BaseModel):
    scenarios_run: int
    scenarios_passed: int
    requirement_to_prd: bool
    prd_to_architecture: bool
    architecture_to_sprint: bool
    sprint_to_jira: bool
    development_context_generated: bool
    qa_prepared: bool
    release_package_generated: bool
    founder_approval_required: bool
    score: int
    evidence: List[Dict[str, Any]]


class ReverseEngineeringReport(BaseModel):
    business_id: str
    target: str
    target_type: str
    explanation: Dict[str, Any]
    evidence: List[Dict[str, Any]]

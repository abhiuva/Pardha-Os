from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2)
    slug: str = Field(..., min_length=2)
    plan: str = "free_trial"
    data_region: str = "us"


class Tenant(BaseModel):
    tenant_id: str
    name: str
    slug: str
    plan: str
    status: str
    data_region: str
    security_profile: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class TenantUser(BaseModel):
    membership_id: str
    tenant_id: str
    user_id: str
    role: str
    permissions: List[str]
    status: str
    created_at: datetime
    updated_at: datetime


class PermissionMatrix(BaseModel):
    roles: Dict[str, List[str]]
    capabilities: List[str]


class AuditEventCreate(BaseModel):
    tenant_id: Optional[str] = None
    business_id: Optional[str] = None
    user_id: Optional[str] = None
    actor_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    capability_id: Optional[str] = None
    conversation_id: Optional[str] = None
    approval_id: Optional[str] = None
    execution_id: Optional[str] = None
    outcome: str = "success"
    rollback: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    audit_id: str
    tenant_id: Optional[str]
    business_id: Optional[str]
    user_id: Optional[str]
    actor_email: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    capability_id: Optional[str]
    conversation_id: Optional[str]
    approval_id: Optional[str]
    execution_id: Optional[str]
    outcome: str
    rollback: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


class ObservabilitySummary(BaseModel):
    tenant_id: Optional[str]
    system_metrics: Dict[str, Any]
    execution_metrics: Dict[str, Any]
    conversation_metrics: Dict[str, Any]
    planner_metrics: Dict[str, Any]
    capability_metrics: Dict[str, Any]
    api_metrics: Dict[str, Any]
    queue_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    alerts: List[Dict[str, Any]]


class BillingSubscription(BaseModel):
    subscription_id: str
    tenant_id: str
    plan: str
    status: str
    trial_ends_at: Optional[datetime]
    limits: Dict[str, Any]
    usage: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EnterpriseIntegration(BaseModel):
    integration_id: str
    tenant_id: str
    provider: str
    auth_type: str
    status: str
    scopes: List[str]
    configuration: Dict[str, Any]
    secret_reference: Optional[str]
    rotation_due_at: Optional[datetime]
    last_checked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class DeploymentProfile(BaseModel):
    profile_id: str
    environment: str
    docker_ready: bool
    kubernetes_ready: bool
    configuration: Dict[str, Any]
    health_checks: List[Dict[str, Any]]
    backup_policy: Dict[str, Any]
    restore_policy: Dict[str, Any]
    status: str
    updated_at: datetime


class AIGovernanceRecord(BaseModel):
    governance_id: str
    tenant_id: Optional[str]
    business_id: Optional[str]
    reasoning_provider: str
    model_version: str
    prompt_version: str
    capability_id: Optional[str]
    conversation_id: Optional[str]
    confidence: int
    evidence: List[Dict[str, Any]]
    human_approval: bool
    provider_switch_ready: bool
    created_at: datetime


class FeatureFlagCreate(BaseModel):
    key: str
    name: str
    enabled: bool = False
    beta: bool = False
    tenant_id: Optional[str] = None
    rollout_percentage: int = Field(default=0, ge=0, le=100)
    emergency_disabled: bool = False
    rules: Dict[str, Any] = Field(default_factory=dict)


class FeatureFlag(BaseModel):
    flag_id: str
    key: str
    name: str
    enabled: bool
    beta: bool
    tenant_id: Optional[str]
    rollout_percentage: int
    emergency_disabled: bool
    rules: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EnterpriseDashboard(BaseModel):
    tenant_health: Dict[str, Any]
    businesses: Dict[str, Any]
    users: Dict[str, Any]
    executions: Dict[str, Any]
    performance: Dict[str, Any]
    revenue: Dict[str, Any]
    subscriptions: Dict[str, Any]
    knowledge_growth: Dict[str, Any]
    security_alerts: List[Dict[str, Any]]
    audit_activity: Dict[str, Any]


class AdministrationConsole(BaseModel):
    tenants: List[Tenant]
    users: List[TenantUser]
    businesses: List[Dict[str, Any]]
    capabilities: Dict[str, Any]
    integrations: List[EnterpriseIntegration]
    executions: Dict[str, Any]
    approvals: Dict[str, Any]
    audit_logs: List[AuditEvent]
    system_health: Dict[str, Any]
    feature_flags: List[FeatureFlag]


class SecurityReadiness(BaseModel):
    jwt_authentication: str
    refresh_tokens: str
    password_policy: Dict[str, Any]
    mfa_ready: bool
    session_management: str
    secure_cookies: str
    rate_limiting: str
    csrf_protection: str
    cors: str
    encryption_at_rest: str
    encryption_in_transit: str


class EnterpriseValidationReport(BaseModel):
    scenarios_run: int
    scenarios_passed: int
    score: int
    security: bool
    isolation: bool
    performance: bool
    rbac: bool
    audit: bool
    billing: bool
    deployment: bool
    observability: bool
    evidence: List[Dict[str, Any]]

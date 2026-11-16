from __future__ import annotations

from fastapi import APIRouter, Query

from app.enterprise.schemas import (
    AdministrationConsole,
    AuditEvent,
    AuditEventCreate,
    BillingSubscription,
    DeploymentProfile,
    EnterpriseDashboard,
    EnterpriseIntegration,
    EnterpriseValidationReport,
    FeatureFlag,
    FeatureFlagCreate,
    ObservabilitySummary,
    PermissionMatrix,
    SecurityReadiness,
    Tenant,
    TenantCreate,
    TenantUser,
)
from app.enterprise.service import (
    admin_console,
    audit_logs,
    billing,
    create_tenant,
    deployment_profiles,
    enterprise_dashboard,
    feature_flags,
    governance_records,
    integrations,
    list_tenants,
    observability_summary,
    permission_matrix,
    record_audit,
    security_readiness,
    tenant_users,
    upsert_feature_flag,
    validation_report,
)
from app.enterprise.schemas import AIGovernanceRecord

router = APIRouter(prefix="/enterprise", tags=["enterprise-platform"])


@router.post("/tenants", response_model=Tenant)
def create_tenant_route(request: TenantCreate):
    return create_tenant(request)


@router.get("/tenants", response_model=list[Tenant])
def tenants_route():
    return list_tenants()


@router.get("/users", response_model=list[TenantUser])
def users_route(tenant_id: str | None = Query(default=None)):
    return tenant_users(tenant_id=tenant_id)


@router.get("/rbac", response_model=PermissionMatrix)
def rbac_route():
    return permission_matrix()


@router.post("/audit", response_model=AuditEvent)
def audit_route(request: AuditEventCreate):
    return record_audit(request)


@router.get("/audit", response_model=list[AuditEvent])
def audit_logs_route(tenant_id: str | None = Query(default=None), business_id: str | None = Query(default=None), limit: int = Query(default=100, ge=1, le=500)):
    return audit_logs(tenant_id=tenant_id, business_id=business_id, limit=limit)


@router.get("/observability", response_model=ObservabilitySummary)
def observability_route(tenant_id: str | None = Query(default=None)):
    return observability_summary(tenant_id=tenant_id)


@router.get("/billing", response_model=list[BillingSubscription])
def billing_route(tenant_id: str | None = Query(default=None)):
    return billing(tenant_id=tenant_id)


@router.get("/integrations", response_model=list[EnterpriseIntegration])
def integrations_route(tenant_id: str | None = Query(default=None)):
    return integrations(tenant_id=tenant_id)


@router.get("/deployment/profiles", response_model=list[DeploymentProfile])
def deployment_profiles_route():
    return deployment_profiles()


@router.get("/governance", response_model=list[AIGovernanceRecord])
def governance_route(tenant_id: str | None = Query(default=None), limit: int = Query(default=100, ge=1, le=500)):
    return governance_records(tenant_id=tenant_id, limit=limit)


@router.post("/feature-flags", response_model=FeatureFlag)
def feature_flag_route(request: FeatureFlagCreate):
    return upsert_feature_flag(request)


@router.get("/feature-flags", response_model=list[FeatureFlag])
def feature_flags_route(tenant_id: str | None = Query(default=None)):
    return feature_flags(tenant_id=tenant_id)


@router.get("/security", response_model=SecurityReadiness)
def security_route():
    return security_readiness()


@router.get("/dashboard", response_model=EnterpriseDashboard)
def dashboard_route(tenant_id: str | None = Query(default=None)):
    return enterprise_dashboard(tenant_id=tenant_id)


@router.get("/admin", response_model=AdministrationConsole)
def admin_route(tenant_id: str | None = Query(default=None)):
    return admin_console(tenant_id=tenant_id)


@router.get("/validation", response_model=EnterpriseValidationReport)
def validation_route():
    return validation_report()

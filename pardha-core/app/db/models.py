from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from app.db import Base


class Business(Base):
    __tablename__ = "businesses"

    business_id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=True, index=True)
    business_name = Column(String, nullable=False, unique=True, index=True)
    business_type = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    status = Column(String, nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthUser(Base):
    __tablename__ = "auth_users"

    user_id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="founder", index=True)
    status = Column(String, nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    session_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("auth_users.user_id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    remember_me = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, index=True)


class AuthRefreshToken(Base):
    __tablename__ = "auth_refresh_tokens"

    refresh_token_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("auth_users.user_id"), nullable=False, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=True, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id = Column(String(36), primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    plan = Column(String, nullable=False, default="free_trial", index=True)
    status = Column(String, nullable=False, default="active", index=True)
    data_region = Column(String, nullable=False, default="us", index=True)
    security_profile = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class TenantUser(Base):
    __tablename__ = "tenant_users"

    membership_id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("auth_users.user_id"), nullable=False, index=True)
    role = Column(String, nullable=False, index=True)
    permissions = Column(JSON, nullable=False, default=list)
    status = Column(String, nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("auth_users.user_id"), nullable=True, index=True)
    actor_email = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False, index=True)
    resource_id = Column(String, nullable=True, index=True)
    capability_id = Column(String(120), nullable=True, index=True)
    conversation_id = Column(String(36), nullable=True, index=True)
    approval_id = Column(String(36), nullable=True, index=True)
    execution_id = Column(String(36), nullable=True, index=True)
    outcome = Column(String, nullable=False, default="success", index=True)
    rollback = Column(JSON, nullable=False, default=dict)
    ip_address = Column(String, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ObservabilityMetric(Base):
    __tablename__ = "observability_metrics"

    metric_id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    metric_type = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    value = Column(Integer, nullable=False, default=0)
    unit = Column(String, nullable=False, default="count", index=True)
    dimensions = Column(JSON, nullable=False, default=dict)
    captured_at = Column(DateTime(timezone=True), nullable=False, index=True)


class BillingSubscription(Base):
    __tablename__ = "billing_subscriptions"

    subscription_id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, unique=True, index=True)
    plan = Column(String, nullable=False, default="free_trial", index=True)
    status = Column(String, nullable=False, default="trialing", index=True)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True, index=True)
    limits = Column(JSON, nullable=False, default=dict)
    usage = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class EnterpriseIntegration(Base):
    __tablename__ = "enterprise_integrations"

    integration_id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)
    auth_type = Column(String, nullable=False, default="oauth", index=True)
    status = Column(String, nullable=False, default="not_configured", index=True)
    scopes = Column(JSON, nullable=False, default=list)
    configuration = Column(JSON, nullable=False, default=dict)
    secret_reference = Column(String, nullable=True, index=True)
    rotation_due_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class DeploymentProfile(Base):
    __tablename__ = "deployment_profiles"

    profile_id = Column(String(36), primary_key=True, index=True)
    environment = Column(String, nullable=False, unique=True, index=True)
    docker_ready = Column(Integer, nullable=False, default=1, index=True)
    kubernetes_ready = Column(Integer, nullable=False, default=1, index=True)
    configuration = Column(JSON, nullable=False, default=dict)
    health_checks = Column(JSON, nullable=False, default=list)
    backup_policy = Column(JSON, nullable=False, default=dict)
    restore_policy = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="ready", index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class AIGovernanceRecord(Base):
    __tablename__ = "ai_governance_records"

    governance_id = Column(String(36), primary_key=True, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    reasoning_provider = Column(String, nullable=False, default="deterministic", index=True)
    model_version = Column(String, nullable=False, default="none", index=True)
    prompt_version = Column(String, nullable=False, default="v1", index=True)
    capability_id = Column(String(120), nullable=True, index=True)
    conversation_id = Column(String(36), nullable=True, index=True)
    confidence = Column(Integer, nullable=False, default=0, index=True)
    evidence = Column(JSON, nullable=False, default=list)
    human_approval = Column(Integer, nullable=False, default=0, index=True)
    provider_switch_ready = Column(Integer, nullable=False, default=1, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    flag_id = Column(String(36), primary_key=True, index=True)
    key = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    enabled = Column(Integer, nullable=False, default=0, index=True)
    beta = Column(Integer, nullable=False, default=0, index=True)
    tenant_id = Column(String(36), ForeignKey("tenants.tenant_id"), nullable=True, index=True)
    rollout_percentage = Column(Integer, nullable=False, default=0, index=True)
    emergency_disabled = Column(Integer, nullable=False, default=0, index=True)
    rules = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class Event(Base):
    __tablename__ = "events"

    event_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    source_agent = Column(String(36), nullable=False, index=True)
    target_agent = Column(String(36), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)


class Memory(Base):
    __tablename__ = "memories"

    memory_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    agent_id = Column(String(36), nullable=False, index=True)
    content = Column(String, nullable=False)
    metadata_json = Column("metadata", JSON, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)


class FounderOperationalLearning(Base):
    __tablename__ = "founder_operational_learning"

    learning_id = Column(String(36), primary_key=True, index=True)
    owner = Column(String, nullable=False, default="Founder", index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    signal_type = Column(String, nullable=False, index=True)
    signal_key = Column(String, nullable=False, index=True)
    signal_value = Column(JSON, nullable=False, default=dict)
    confidence = Column(Integer, nullable=False, default=60, index=True)
    source_conversation_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class Knowledge(Base):
    __tablename__ = "knowledge"
    __table_args__ = (
        CheckConstraint(
            "category IN ('company', 'product', 'project', 'roadmap', 'prd', 'sop', "
            "'meeting_notes', 'customer_feedback')",
            name="ck_knowledge_category",
        ),
    )

    knowledge_id = Column(Uuid(as_uuid=True), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    business_name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, nullable=False, default=list)
    source = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Reserved for future document ingestion and embedding workflows.
    source_uri = Column(String, nullable=True)
    document_metadata_json = Column("document_metadata", JSON, nullable=False, default=dict)
    embedding_model = Column(String, nullable=True)
    embedding_reference = Column(String, nullable=True)


class AgentExecution(Base):
    __tablename__ = "agent_executions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_agent_execution_status",
        ),
    )

    execution_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    cycle_id = Column(String(36), nullable=False, index=True)
    agent_name = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    output = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)


class KnowledgeImport(Base):
    __tablename__ = "knowledge_imports"

    import_id = Column(String(36), primary_key=True, index=True)
    file_path = Column(Text, nullable=False, unique=True)
    file_hash = Column(String(64), nullable=False, unique=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    business_name = Column(String, nullable=False, index=True)
    knowledge_id = Column(Uuid(as_uuid=True), nullable=False, index=True)
    imported_at = Column(DateTime(timezone=True), nullable=False, index=True)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'failed')",
            name="ck_task_status",
        ),
    )

    task_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)
    assigned_agent = Column(String, nullable=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    project_name = Column(String, nullable=False, index=True)
    project_path = Column(Text, nullable=False, unique=True)
    language = Column(String, nullable=False)
    framework = Column(String, nullable=False)
    repository_summary = Column(Text, nullable=False)
    analysis = Column(JSON, nullable=False, default=dict)
    last_scanned = Column(DateTime(timezone=True), nullable=False, index=True)


class Objective(Base):
    __tablename__ = "objectives"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('critical', 'high', 'medium', 'low')",
            name="ck_objective_priority",
        ),
        CheckConstraint(
            "status IN ('NEW', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED')",
            name="ck_objective_status",
        ),
    )

    objective_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    business_name = Column(String, nullable=False, index=True)
    priority = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="NEW", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class AgentCollaboration(Base):
    __tablename__ = "agent_collaborations"

    collaboration_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    objective_id = Column(String(36), nullable=False, index=True)
    source_agent = Column(String, nullable=False, index=True)
    target_agent = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    status = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class AgentReasoning(Base):
    __tablename__ = "agent_reasoning"

    reasoning_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    agent_name = Column(String, nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    model = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False, index=True)
    provider_metadata = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)


class SalesCompany(Base):
    __tablename__ = "sales_companies"

    company_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    industry = Column(String, nullable=False, index=True)
    website = Column(String, nullable=True)
    company_size = Column(String, nullable=True)
    country = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    business_summary = Column(Text, nullable=False, default="")
    ai_opportunity_score = Column(Integer, nullable=False, default=0)
    sales_priority = Column(String, nullable=False, default="medium", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class SalesContact(Base):
    __tablename__ = "sales_contacts"

    contact_id = Column(String(36), primary_key=True, index=True)
    company_id = Column(String(36), ForeignKey("sales_companies.company_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=True)
    email = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class SalesLead(Base):
    __tablename__ = "sales_leads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'contacted', 'demo_requested', 'demo_scheduled', 'demo_completed', 'proposal_sent', 'negotiation', 'won', 'lost')",
            name="ck_sales_lead_status",
        ),
    )

    lead_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("sales_companies.company_id"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("sales_contacts.contact_id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="new", index=True)
    pipeline_stage = Column(String, nullable=False, default="prospect", index=True)
    ai_opportunity_score = Column(Integer, nullable=False, default=0)
    sales_priority = Column(String, nullable=False, default="medium", index=True)
    outreach_email = Column(Text, nullable=True)
    outreach_linkedin = Column(Text, nullable=True)
    next_action = Column(String, nullable=True)
    demo_requested_at = Column(DateTime(timezone=True), nullable=True)
    demo_scheduled_at = Column(DateTime(timezone=True), nullable=True)
    demo_completed_at = Column(DateTime(timezone=True), nullable=True)
    proposal_sent_at = Column(DateTime(timezone=True), nullable=True)
    negotiation_started_at = Column(DateTime(timezone=True), nullable=True)
    won_at = Column(DateTime(timezone=True), nullable=True)
    lost_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class SalesLeadQualification(Base):
    __tablename__ = "sales_lead_qualifications"

    qualification_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("sales_leads.lead_id"), nullable=False, unique=True, index=True)
    business_type = Column(String, nullable=False, index=True)
    location = Column(String, nullable=False, index=True)
    stage = Column(String, nullable=False, index=True)
    budget = Column(Integer, nullable=False, default=0, index=True)
    timeline = Column(String, nullable=False, index=True)
    requirement = Column(Text, nullable=False)
    source = Column(String, nullable=False, index=True)
    score = Column(Integer, nullable=False, default=0, index=True)
    qualification_status = Column(String, nullable=False, default="new", index=True)
    missing_fields = Column(JSON, nullable=False, default=list)
    scoring_factors = Column(JSON, nullable=False, default=dict)
    recommendation = Column(Text, nullable=False, default="")
    hubspot_event_payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class SalesDemoBooking(Base):
    __tablename__ = "sales_demo_bookings"

    booking_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("sales_leads.lead_id"), nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("sales_companies.company_id"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("sales_contacts.contact_id"), nullable=True, index=True)
    status = Column(String, nullable=False, default="requested", index=True)
    requested_slot = Column(DateTime(timezone=True), nullable=True, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    meeting_url = Column(String, nullable=True)
    owner = Column(String, nullable=False, default="Founder", index=True)
    calendar_mode = Column(String, nullable=False, default="mock", index=True)
    hubspot_event_payload = Column(JSON, nullable=False, default=dict)
    notes = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class SalesPostDemoDraft(Base):
    __tablename__ = "sales_post_demo_drafts"

    draft_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    booking_id = Column(String(36), ForeignKey("sales_demo_bookings.booking_id"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("sales_leads.lead_id"), nullable=False, index=True)
    deal_id = Column(String(36), ForeignKey("sales_deals.deal_id"), nullable=True, index=True)
    company_id = Column(String(36), ForeignKey("sales_companies.company_id"), nullable=False, index=True)
    contact_id = Column(String(36), ForeignKey("sales_contacts.contact_id"), nullable=True, index=True)
    demo_summary = Column(Text, nullable=False)
    pain_points = Column(JSON, nullable=False, default=list)
    dp360_fit = Column(Text, nullable=False)
    next_action = Column(Text, nullable=False)
    commercial_cta = Column(Text, nullable=False)
    follow_up_email = Column(Text, nullable=False)
    proposal_draft = Column(Text, nullable=False)
    approval_status = Column(String, nullable=False, default="pending", index=True)
    external_send_blocked = Column(Integer, nullable=False, default=1, index=True)
    hubspot_event_payload = Column(JSON, nullable=False, default=dict)
    reasoning_provider = Column(String, nullable=False, default="deterministic", index=True)
    reasoning_model = Column(String, nullable=False, default="deterministic", index=True)
    created_by = Column(String, nullable=False, default="Sales Executive", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class SalesDeal(Base):
    __tablename__ = "sales_deals"

    deal_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("sales_leads.lead_id"), nullable=False, index=True)
    pipeline_stage = Column(String, nullable=False, default="prospecting", index=True)
    amount = Column(Integer, nullable=False, default=0)
    probability = Column(Integer, nullable=False, default=0)
    expected_close_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class SalesActivity(Base):
    __tablename__ = "sales_activities"

    activity_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("sales_leads.lead_id"), nullable=False, index=True)
    activity_type = Column(String, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class HubSpotConnectorConfig(Base):
    __tablename__ = "hubspot_connector_configs"

    config_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, unique=True, index=True)
    portal_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="not_configured", index=True)
    write_mode = Column(String, nullable=False, default="disabled", index=True)
    scopes = Column(JSON, nullable=False, default=list)
    configuration = Column(JSON, nullable=False, default=dict)
    secret_reference = Column(String, nullable=True, index=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class HubSpotSyncRecord(Base):
    __tablename__ = "hubspot_sync_records"

    sync_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    lead_id = Column(String(36), ForeignKey("sales_leads.lead_id"), nullable=False, index=True)
    local_contact_id = Column(String(36), nullable=True, index=True)
    local_company_id = Column(String(36), nullable=True, index=True)
    local_deal_id = Column(String(36), nullable=True, index=True)
    hubspot_contact_id = Column(String, nullable=True, index=True)
    hubspot_company_id = Column(String, nullable=True, index=True)
    hubspot_deal_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False, default="draft", index=True)
    sync_status = Column(String, nullable=False, default="draft", index=True)
    duplicate_key = Column(String, nullable=True, index=True)
    retry_count = Column(Integer, nullable=False, default=0, index=True)
    retryable = Column(Integer, nullable=False, default=0, index=True)
    error = Column(Text, nullable=True)
    contact_payload = Column(JSON, nullable=False, default=dict)
    company_payload = Column(JSON, nullable=False, default=dict)
    deal_payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"

    campaign_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    objective = Column(Text, nullable=False)
    audience = Column(JSON, nullable=False, default=dict)
    channels = Column(JSON, nullable=False, default=list)
    budget = Column(Integer, nullable=False, default=0)
    goals = Column(JSON, nullable=False, default=list)
    kpis = Column(JSON, nullable=False, default=list)
    status = Column(String, nullable=False, default="active", index=True)
    start_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True), nullable=False, index=True)
    campaign_plan = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MarketingContent(Base):
    __tablename__ = "marketing_content"

    content_id = Column(String(36), primary_key=True, index=True)
    campaign_id = Column(String(36), ForeignKey("marketing_campaigns.campaign_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    content_type = Column(String, nullable=False, index=True)
    channel = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    body = Column(Text, nullable=False)
    call_to_action = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft", index=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MarketingCalendarItem(Base):
    __tablename__ = "marketing_calendar_items"

    calendar_item_id = Column(String(36), primary_key=True, index=True)
    campaign_id = Column(String(36), ForeignKey("marketing_campaigns.campaign_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    channel = Column(String, nullable=False, index=True)
    content_type = Column(String, nullable=False, index=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String, nullable=False, default="planned", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MarketingAnalytics(Base):
    __tablename__ = "marketing_analytics"

    analytics_id = Column(String(36), primary_key=True, index=True)
    campaign_id = Column(String(36), ForeignKey("marketing_campaigns.campaign_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    channel = Column(String, nullable=False, index=True)
    impressions = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    conversions = Column(Integer, nullable=False, default=0)
    leads = Column(Integer, nullable=False, default=0)
    spend = Column(Integer, nullable=False, default=0)
    revenue = Column(Integer, nullable=False, default=0)
    captured_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MetaConnectorConfig(Base):
    __tablename__ = "meta_connector_configs"

    config_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, unique=True, index=True)
    ad_account_id = Column(String, nullable=True, index=True)
    instagram_account_id = Column(String, nullable=True, index=True)
    page_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="not_configured", index=True)
    authentication_status = Column(String, nullable=False, default="missing_credentials", index=True)
    scopes = Column(JSON, nullable=False, default=list)
    configuration = Column(JSON, nullable=False, default=dict)
    secret_reference = Column(String, nullable=True, index=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MetaCampaignInsight(Base):
    __tablename__ = "meta_campaign_insights"

    insight_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    campaign_id = Column(String(36), ForeignKey("marketing_campaigns.campaign_id"), nullable=True, index=True)
    external_campaign_id = Column(String, nullable=False, index=True)
    campaign_name = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False, default="meta", index=True)
    channel = Column(String, nullable=False, default="Meta Ads", index=True)
    spend = Column(Integer, nullable=False, default=0)
    impressions = Column(Integer, nullable=False, default=0)
    reach = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    ctr = Column(Integer, nullable=False, default=0)
    cpc = Column(Integer, nullable=False, default=0)
    leads = Column(Integer, nullable=False, default=0)
    sync_status = Column(String, nullable=False, default="mock", index=True)
    error = Column(Text, nullable=True)
    raw_payload = Column(JSON, nullable=False, default=dict)
    captured_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MetaAdApproval(Base):
    __tablename__ = "meta_ad_approvals"

    approval_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    campaign_name = Column(String, nullable=False, index=True)
    budget = Column(Integer, nullable=False, default=0)
    audience = Column(JSON, nullable=False, default=dict)
    creative = Column(JSON, nullable=False, default=dict)
    expected_goal = Column(Text, nullable=False, default="")
    status = Column(String, nullable=False, default="pending", index=True)
    approval_required = Column(Integer, nullable=False, default=1, index=True)
    external_write_blocked = Column(Integer, nullable=False, default=1, index=True)
    external_write_attempted = Column(Integer, nullable=False, default=0, index=True)
    requested_by = Column(String, nullable=False, default="Marketing Executive", index=True)
    decided_by = Column(String, nullable=True, index=True)
    decision_comment = Column(Text, nullable=True)
    audit_event_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)
    decided_at = Column(DateTime(timezone=True), nullable=True, index=True)


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    profile_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, unique=True, index=True)
    company_name = Column(String, nullable=False, index=True)
    business_type = Column(String, nullable=False, index=True)
    lifecycle_stage = Column(String, nullable=False, default="onboarding", index=True)
    health_score = Column(Integer, nullable=False, default=75)
    revenue_goal = Column(Integer, nullable=False, default=0)
    success_plan = Column(JSON, nullable=False, default=dict)
    onboarding_status = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MeetingNote(Base):
    __tablename__ = "meeting_notes"

    meeting_note_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    attendees = Column(JSON, nullable=False, default=list)
    action_items = Column(JSON, nullable=False, default=list)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class CustomerTimelineEntry(Base):
    __tablename__ = "customer_timeline_entries"

    timeline_entry_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    detail = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ChiefConversation(Base):
    __tablename__ = "chief_conversations"

    conversation_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ChiefMessage(Base):
    __tablename__ = "chief_messages"

    message_id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("chief_conversations.conversation_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    role = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    intent = Column(String, nullable=False, default="general", index=True)
    rich_response = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class FounderGoal(Base):
    __tablename__ = "founder_goals"

    goal_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    priority = Column(String, nullable=False, default="high", index=True)
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    owner = Column(String, nullable=False, default="Founder", index=True)
    status = Column(String, nullable=False, default="active", index=True)
    success_metrics = Column(JSON, nullable=False, default=list)
    objective_id = Column(String(36), nullable=True, index=True)
    plans = Column(JSON, nullable=False, default=dict)
    timeline = Column(JSON, nullable=False, default=list)
    daily_followups = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class Capability(Base):
    __tablename__ = "capabilities"

    capability_id = Column(String(120), primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False, default="1.0.0", index=True)
    description = Column(Text, nullable=False)
    supported_intents = Column(JSON, nullable=False, default=list)
    business_domains = Column(JSON, nullable=False, default=list)
    required_inputs = Column(JSON, nullable=False, default=list)
    outputs = Column(JSON, nullable=False, default=list)
    dependencies = Column(JSON, nullable=False, default=list)
    permissions = Column(JSON, nullable=False, default=list)
    health = Column(String, nullable=False, default="unknown", index=True)
    supports_hitl = Column(Integer, nullable=False, default=0, index=True)
    supports_streaming = Column(Integer, nullable=False, default=0, index=True)
    supports_learning = Column(Integer, nullable=False, default=0, index=True)
    priority = Column(Integer, nullable=False, default=50, index=True)
    estimated_runtime_ms = Column(Integer, nullable=False, default=100, index=True)
    registration_method = Column(String, nullable=False, default="automatic", index=True)
    current_status = Column(String, nullable=False, default="registered", index=True)
    planner_interface = Column(JSON, nullable=False, default=dict)
    execution_adapter = Column(String, nullable=True, index=True)
    execution_count = Column(Integer, nullable=False, default=0, index=True)
    last_executed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    registered_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class CapabilityExecution(Base):
    __tablename__ = "capability_executions"

    execution_id = Column(String(36), primary_key=True, index=True)
    capability_id = Column(String(120), ForeignKey("capabilities.capability_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    intent = Column(String, nullable=False, index=True)
    input_payload = Column(JSON, nullable=False, default=dict)
    output_payload = Column(JSON, nullable=True)
    status = Column(String, nullable=False, index=True)
    confidence = Column(Integer, nullable=False, default=0, index=True)
    runtime_ms = Column(Integer, nullable=False, default=0, index=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    conversation_id = Column(String(36), primary_key=True, index=True)
    id = Column(String(36), nullable=True, unique=True, index=True)
    title = Column(String, nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    founder_id = Column(String(36), ForeignKey("auth_users.user_id"), nullable=True, index=True)
    owner = Column(String, nullable=False, default="Founder", index=True)
    conversation_type = Column(String, nullable=False, default="general", index=True)
    status = Column(String, nullable=False, default="active", index=True)
    voice_enabled = Column(Integer, nullable=False, default=0, index=True)
    pinned = Column(Integer, nullable=False, default=0, index=True)
    archived = Column(Integer, nullable=False, default=0, index=True)
    summary = Column(Text, nullable=False, default="")
    context_snapshot = Column(JSON, nullable=False, default=dict)
    current_context = Column(JSON, nullable=False, default=dict)
    started_at = Column(DateTime(timezone=True), nullable=True, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    message_id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversation_sessions.conversation_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    role = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    message = Column(Text, nullable=True)
    intent = Column(String, nullable=False, default="general", index=True)
    planner = Column(String, nullable=True, index=True)
    specialist = Column(String, nullable=True, index=True)
    reasoning_model = Column(String, nullable=True, index=True)
    tool_used = Column(String, nullable=True, index=True)
    tokens = Column(Integer, nullable=False, default=0, index=True)
    latency = Column(Integer, nullable=False, default=0, index=True)
    conversation_type = Column(String, nullable=False, default="general", index=True)
    context_snapshot = Column(JSON, nullable=False, default=dict)
    capability_ids = Column(JSON, nullable=False, default=list)
    response_payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ConversationTimelineEvent(Base):
    __tablename__ = "conversation_timeline_events"

    timeline_event_id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversation_sessions.conversation_id"), nullable=False, index=True)
    message_id = Column(String(36), ForeignKey("conversation_messages.message_id"), nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    detail = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ConversationContext(Base):
    __tablename__ = "conversation_context"

    context_id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversation_sessions.conversation_id"), nullable=False, unique=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    active_module = Column(String, nullable=True, index=True)
    active_business = Column(JSON, nullable=False, default=dict)
    active_specialist = Column(String, nullable=True, index=True)
    current_goal = Column(JSON, nullable=False, default=dict)
    context_payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ConversationIntent(Base):
    __tablename__ = "conversation_intents"

    intent_id = Column(String(36), primary_key=True, index=True)
    intent_name = Column(String, nullable=False, unique=True, index=True)
    category = Column(String, nullable=False, index=True)
    priority = Column(Integer, nullable=False, default=50, index=True)
    requires_business_context = Column(Integer, nullable=False, default=0, index=True)
    requires_reasoning = Column(Integer, nullable=False, default=0, index=True)
    requires_tool = Column(Integer, nullable=False, default=0, index=True)
    requires_memory = Column(Integer, nullable=False, default=0, index=True)
    allowed_specialists = Column(JSON, nullable=False, default=list)
    status = Column(String, nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class Specialist(Base):
    __tablename__ = "specialists"

    specialist_id = Column(String(36), primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    role = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    voice_enabled = Column(Integer, nullable=False, default=0, index=True)
    system_prompt = Column(Text, nullable=False, default="")
    memory_scope = Column(JSON, nullable=False, default=list)
    knowledge_scope = Column(JSON, nullable=False, default=list)
    capability_scope = Column(JSON, nullable=False, default=list)
    status = Column(String, nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ReasoningModel(Base):
    __tablename__ = "reasoning_models"

    reasoning_model_id = Column(String(36), primary_key=True, index=True)
    provider = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False, index=True)
    host = Column(String, nullable=True, index=True)
    endpoint = Column(Text, nullable=True)
    priority = Column(Integer, nullable=False, default=50, index=True)
    max_context = Column(Integer, nullable=False, default=4096, index=True)
    cost = Column(String, nullable=False, default="local", index=True)
    latency = Column(Integer, nullable=False, default=0, index=True)
    health = Column(String, nullable=False, default="unknown", index=True)
    status = Column(String, nullable=False, default="available", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    mcp_server_id = Column(String(36), primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    endpoint = Column(Text, nullable=False)
    transport = Column(String, nullable=False, default="stdio", index=True)
    authentication = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="not_configured", index=True)
    health = Column(String, nullable=False, default="unknown", index=True)
    capabilities = Column(JSON, nullable=False, default=list)
    last_seen = Column(DateTime(timezone=True), nullable=True, index=True)
    supported_tools = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MCPServerCapability(Base):
    __tablename__ = "mcp_server_capabilities"

    capability_id = Column(String(36), primary_key=True, index=True)
    server_id = Column(String(36), ForeignKey("mcp_servers.mcp_server_id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MCPServerHealth(Base):
    __tablename__ = "mcp_server_health"

    health_id = Column(String(36), primary_key=True, index=True)
    server_id = Column(String(36), ForeignKey("mcp_servers.mcp_server_id"), nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    latency_ms = Column(Integer, nullable=True, index=True)
    authentication_status = Column(String, nullable=False, index=True)
    capabilities = Column(JSON, nullable=False, default=list)
    connected_tools = Column(JSON, nullable=False, default=list)
    failure_count = Column(Integer, nullable=False, default=0, index=True)
    message = Column(Text, nullable=False, default="")
    checked_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MCPTool(Base):
    __tablename__ = "mcp_tools"

    tool_id = Column(String(80), primary_key=True, index=True)
    server_id = Column(String(36), ForeignKey("mcp_servers.mcp_server_id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    input_schema = Column(JSON, nullable=False, default=dict)
    permissions = Column(JSON, nullable=False, default=list)
    enabled = Column(Integer, nullable=False, default=1, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MCPConnection(Base):
    __tablename__ = "mcp_connections"

    connection_id = Column(String(36), primary_key=True, index=True)
    server_id = Column(String(36), ForeignKey("mcp_servers.mcp_server_id"), nullable=False, index=True)
    auth_type = Column(String, nullable=False, index=True)
    authentication_status = Column(String, nullable=False, index=True)
    credentials = Column(JSON, nullable=False, default=dict)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    connected_at = Column(DateTime(timezone=True), nullable=True, index=True)
    disconnected_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MCPPermission(Base):
    __tablename__ = "mcp_permissions"

    permission_id = Column(String(36), primary_key=True, index=True)
    server_id = Column(String(36), ForeignKey("mcp_servers.mcp_server_id"), nullable=False, index=True)
    permission = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    granted = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MCPExecutionHistory(Base):
    __tablename__ = "mcp_execution_history"

    execution_id = Column(String(36), primary_key=True, index=True)
    server_id = Column(String(36), ForeignKey("mcp_servers.mcp_server_id"), nullable=False, index=True)
    tool = Column(String, nullable=False, index=True)
    parameters = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, index=True)
    latency_ms = Column(Integer, nullable=False, default=0, index=True)
    output = Column(JSON, nullable=False, default=dict)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MCPEvent(Base):
    __tablename__ = "mcp_events"

    event_id = Column(String(36), primary_key=True, index=True)
    server_id = Column(String(36), ForeignKey("mcp_servers.mcp_server_id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MCPLog(Base):
    __tablename__ = "mcp_logs"

    log_id = Column(String(36), primary_key=True, index=True)
    server_id = Column(String(36), ForeignKey("mcp_servers.mcp_server_id"), nullable=False, index=True)
    level = Column(String, nullable=False, default="info", index=True)
    message = Column(Text, nullable=False)
    context = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class CapabilityRoute(Base):
    __tablename__ = "capability_routes"

    route_id = Column(String(36), primary_key=True, index=True)
    intent = Column(String, nullable=False, index=True)
    planner = Column(String, nullable=True, index=True)
    specialist = Column(String, nullable=True, index=True)
    tool = Column(String, nullable=True, index=True)
    mcp_server = Column(String, nullable=True, index=True)
    reasoning_model = Column(String, nullable=True, index=True)
    priority = Column(Integer, nullable=False, default=50, index=True)
    status = Column(String, nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class FounderMemory(Base):
    __tablename__ = "founder_memory"

    memory_id = Column(String(36), primary_key=True, index=True)
    founder_id = Column(String(36), ForeignKey("auth_users.user_id"), nullable=True, index=True)
    owner = Column(String, nullable=False, default="Founder", index=True)
    memory_type = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    confidence = Column(Integer, nullable=False, default=60, index=True)
    source_conversation_id = Column(String(36), ForeignKey("conversation_sessions.conversation_id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class BusinessMemory(Base):
    __tablename__ = "business_memory"

    memory_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    memory_type = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    confidence = Column(Integer, nullable=False, default=60, index=True)
    source_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class SpecialistMemory(Base):
    __tablename__ = "specialist_memory"

    memory_id = Column(String(36), primary_key=True, index=True)
    specialist_id = Column(String(36), ForeignKey("specialists.specialist_id"), nullable=True, index=True)
    specialist = Column(String, nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    memory_type = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    confidence = Column(Integer, nullable=False, default=60, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ConversationMemory(Base):
    __tablename__ = "conversation_memory"

    memory_id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversation_sessions.conversation_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    memory_type = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class LearningMemory(Base):
    __tablename__ = "learning_memory"

    memory_id = Column(String(36), primary_key=True, index=True)
    owner = Column(String, nullable=False, default="Founder", index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    signal_type = Column(String, nullable=False, index=True)
    signal_value = Column(JSON, nullable=False, default=dict)
    confidence = Column(Integer, nullable=False, default=60, index=True)
    source_event_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class LearningEvent(Base):
    __tablename__ = "learning_events"

    learning_event_id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversation_sessions.conversation_id"), nullable=True, index=True)
    event = Column(String, nullable=False, index=True)
    correction = Column(Text, nullable=True)
    accepted = Column(Integer, nullable=False, default=0, index=True)
    confidence = Column(Integer, nullable=False, default=60, index=True)
    feedback = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    voice_session_id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversation_sessions.conversation_id"), nullable=False, index=True)
    microphone = Column(JSON, nullable=False, default=dict)
    transcription = Column(JSON, nullable=False, default=dict)
    reasoning_time = Column(Integer, nullable=False, default=0, index=True)
    speech_time = Column(Integer, nullable=False, default=0, index=True)
    duration = Column(Integer, nullable=False, default=0, index=True)
    status = Column(String, nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ExecutionTrace(Base):
    __tablename__ = "execution_trace"

    trace_id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversation_sessions.conversation_id"), nullable=True, index=True)
    planner = Column(String, nullable=True, index=True)
    specialist = Column(String, nullable=True, index=True)
    tool = Column(String, nullable=True, index=True)
    duration = Column(Integer, nullable=False, default=0, index=True)
    result = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="recorded", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class PlanningGoal(Base):
    __tablename__ = "planning_goals"

    goal_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    priority = Column(String, nullable=False, default="high", index=True)
    owner = Column(String, nullable=False, default="Founder", index=True)
    department = Column(String, nullable=False, default="Executive", index=True)
    target_date = Column(DateTime(timezone=True), nullable=True, index=True)
    success_metrics = Column(JSON, nullable=False, default=list)
    current_status = Column(String, nullable=False, default="active", index=True)
    risk_level = Column(String, nullable=False, default="medium", index=True)
    progress = Column(Integer, nullable=False, default=0, index=True)
    dependencies = Column(JSON, nullable=False, default=list)
    created_by = Column(String, nullable=False, default="Founder", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ExecutionPlan(Base):
    __tablename__ = "execution_plans"

    plan_id = Column(String(36), primary_key=True, index=True)
    goal_id = Column(String(36), ForeignKey("planning_goals.goal_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    request = Column(Text, nullable=False)
    plan_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="preview", index=True)
    risk_level = Column(String, nullable=False, default="medium", index=True)
    approval_required = Column(Integer, nullable=False, default=1, index=True)
    progress = Column(Integer, nullable=False, default=0, index=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True, index=True)
    summary = Column(Text, nullable=False, default="")
    capability_ids = Column(JSON, nullable=False, default=list)
    graph = Column(JSON, nullable=False, default=dict)
    created_by = Column(String, nullable=False, default="Founder", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ExecutionPlanNode(Base):
    __tablename__ = "execution_plan_nodes"

    node_id = Column(String(36), primary_key=True, index=True)
    plan_id = Column(String(36), ForeignKey("execution_plans.plan_id"), nullable=False, index=True)
    goal_id = Column(String(36), ForeignKey("planning_goals.goal_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    node_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False, default="")
    capability_id = Column(String(120), ForeignKey("capabilities.capability_id"), nullable=True, index=True)
    status = Column(String, nullable=False, default="queued", index=True)
    risk_level = Column(String, nullable=False, default="low", index=True)
    approval_required = Column(Integer, nullable=False, default=0, index=True)
    dependencies = Column(JSON, nullable=False, default=list)
    parallel_group = Column(String, nullable=True, index=True)
    critical_path = Column(Integer, nullable=False, default=0, index=True)
    estimated_runtime_ms = Column(Integer, nullable=False, default=0)
    output = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class PlanApproval(Base):
    __tablename__ = "plan_approvals"

    approval_id = Column(String(36), primary_key=True, index=True)
    plan_id = Column(String(36), ForeignKey("execution_plans.plan_id"), nullable=False, index=True)
    node_id = Column(String(36), ForeignKey("execution_plan_nodes.node_id"), nullable=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    approval_type = Column(String, nullable=False, index=True)
    risk_level = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    detail = Column(Text, nullable=False, default="")
    status = Column(String, nullable=False, default="pending", index=True)
    requested_by = Column(String, nullable=False, default="Planner", index=True)
    decided_by = Column(String, nullable=True, index=True)
    decision_comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    decided_at = Column(DateTime(timezone=True), nullable=True, index=True)


class PlanExecution(Base):
    __tablename__ = "plan_executions"

    execution_id = Column(String(36), primary_key=True, index=True)
    plan_id = Column(String(36), ForeignKey("execution_plans.plan_id"), nullable=False, index=True)
    goal_id = Column(String(36), ForeignKey("planning_goals.goal_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    current_step = Column(String, nullable=False, default="", index=True)
    current_capability = Column(String(120), nullable=True, index=True)
    progress = Column(Integer, nullable=False, default=0, index=True)
    estimated_time_ms = Column(Integer, nullable=False, default=0)
    logs = Column(JSON, nullable=False, default=list)
    retry_count = Column(Integer, nullable=False, default=0, index=True)
    status = Column(String, nullable=False, default="queued", index=True)
    started_at = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class GoalKPI(Base):
    __tablename__ = "goal_kpis"

    kpi_id = Column(String(36), primary_key=True, index=True)
    goal_id = Column(String(36), ForeignKey("planning_goals.goal_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    target_value = Column(Integer, nullable=False, default=0)
    current_value = Column(Integer, nullable=False, default=0)
    unit = Column(String, nullable=False, default="count", index=True)
    status = Column(String, nullable=False, default="tracking", index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class PlanningTimelineEvent(Base):
    __tablename__ = "planning_timeline_events"

    timeline_event_id = Column(String(36), primary_key=True, index=True)
    goal_id = Column(String(36), ForeignKey("planning_goals.goal_id"), nullable=False, index=True)
    plan_id = Column(String(36), ForeignKey("execution_plans.plan_id"), nullable=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    detail = Column(Text, nullable=False, default="")
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class RuntimeExecution(Base):
    __tablename__ = "runtime_executions"

    execution_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    goal_id = Column(String(36), nullable=True, index=True)
    plan_id = Column(String(36), nullable=True, index=True)
    execution_graph = Column(JSON, nullable=False, default=dict)
    current_stage = Column(String, nullable=False, default="queued", index=True)
    current_capability = Column(String(120), nullable=True, index=True)
    logs = Column(JSON, nullable=False, default=list)
    retries = Column(Integer, nullable=False, default=0, index=True)
    progress = Column(Integer, nullable=False, default=0, index=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    dependencies = Column(JSON, nullable=False, default=list)
    rollback = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="queued", index=True)
    started_at = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class DepartmentRuntime(Base):
    __tablename__ = "department_runtimes"

    department_id = Column(String(80), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    owner = Column(String, nullable=False, default="Founder", index=True)
    objectives = Column(JSON, nullable=False, default=list)
    capabilities = Column(JSON, nullable=False, default=list)
    current_work = Column(JSON, nullable=False, default=list)
    queue = Column(JSON, nullable=False, default=list)
    kpis = Column(JSON, nullable=False, default=dict)
    health = Column(String, nullable=False, default="healthy", index=True)
    current_load = Column(Integer, nullable=False, default=0, index=True)
    dependencies = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class RuntimeQueueItem(Base):
    __tablename__ = "runtime_queue_items"

    queue_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    execution_id = Column(String(36), ForeignKey("runtime_executions.execution_id"), nullable=True, index=True)
    plan_id = Column(String(36), nullable=True, index=True)
    capability_id = Column(String(120), nullable=True, index=True)
    priority = Column(Integer, nullable=False, default=50, index=True)
    dependencies = Column(JSON, nullable=False, default=list)
    retry_count = Column(Integer, nullable=False, default=0, index=True)
    timeout_ms = Column(Integer, nullable=False, default=30000)
    scheduled_for = Column(DateTime(timezone=True), nullable=True, index=True)
    recurring = Column(Integer, nullable=False, default=0, index=True)
    delay_until = Column(DateTime(timezone=True), nullable=True, index=True)
    status = Column(String, nullable=False, default="queued", index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class ToolRuntimeInvocation(Base):
    __tablename__ = "tool_runtime_invocations"

    invocation_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    tool_name = Column(String, nullable=False, index=True)
    capability_id = Column(String(120), nullable=True, index=True)
    execution_id = Column(String(36), ForeignKey("runtime_executions.execution_id"), nullable=True, index=True)
    status = Column(String, nullable=False, default="queued", index=True)
    input_payload = Column(JSON, nullable=False, default=dict)
    output_payload = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class RuntimeNotification(Base):
    __tablename__ = "runtime_notifications"

    notification_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    priority = Column(String, nullable=False, default="medium", index=True)
    category = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="unread", index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True, index=True)
    archived_at = Column(DateTime(timezone=True), nullable=True, index=True)


class SoftwareFactoryRequirement(Base):
    __tablename__ = "software_factory_requirements"

    requirement_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    request = Column(Text, nullable=False)
    requester = Column(String, nullable=False, default="Founder", index=True)
    methodology = Column(String, nullable=False, default="scrum", index=True)
    stack = Column(JSON, nullable=False, default=list)
    status = Column(String, nullable=False, default="waiting_approval", index=True)
    current_stage = Column(String, nullable=False, default="discovery", index=True)
    discovery = Column(JSON, nullable=False, default=dict)
    orchestration_graph = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class SoftwareFactoryArtifact(Base):
    __tablename__ = "software_factory_artifacts"

    artifact_id = Column(String(36), primary_key=True, index=True)
    requirement_id = Column(String(36), ForeignKey("software_factory_requirements.requirement_id"), nullable=False, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    artifact_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1, index=True)
    status = Column(String, nullable=False, default="draft", index=True)
    content = Column(JSON, nullable=False, default=dict)
    editable = Column(Integer, nullable=False, default=1, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class SoftwareFactoryApproval(Base):
    __tablename__ = "software_factory_approvals"

    approval_id = Column(String(36), primary_key=True, index=True)
    requirement_id = Column(String(36), ForeignKey("software_factory_requirements.requirement_id"), nullable=False, index=True)
    artifact_id = Column(String(36), ForeignKey("software_factory_artifacts.artifact_id"), nullable=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    approval_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    detail = Column(Text, nullable=False, default="")
    risk_level = Column(String, nullable=False, default="medium", index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    requested_by = Column(String, nullable=False, default="Software Factory", index=True)
    decided_by = Column(String, nullable=True, index=True)
    decision_comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    decided_at = Column(DateTime(timezone=True), nullable=True, index=True)


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    rule_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=True, index=True)
    name = Column(String, nullable=False, index=True)
    trigger_event = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    enabled = Column(Integer, nullable=False, default=1, index=True)
    priority = Column(Integer, nullable=False, default=50, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class BusinessTimelineEvent(Base):
    __tablename__ = "business_timeline_events"

    timeline_event_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    detail = Column(Text, nullable=False, default="")
    source = Column(String, nullable=False, default="runtime", index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class CommunicationAccount(Base):
    __tablename__ = "communication_accounts"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('gmail', 'outlook')",
            name="ck_communication_account_provider",
        ),
    )

    account_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)
    account_name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="configured", index=True)
    last_sync = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class MessageThread(Base):
    __tablename__ = "message_threads"

    thread_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("communication_accounts.account_id"), nullable=False, index=True)
    provider_thread_id = Column(String, nullable=True, index=True)
    subject = Column(String, nullable=False, index=True)
    participants = Column(JSON, nullable=False, default=list)
    unread_count = Column(Integer, nullable=False, default=0)
    last_message_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="ck_message_direction",
        ),
        CheckConstraint(
            "status IN ('received', 'draft', 'sent', 'failed')",
            name="ck_message_status",
        ),
    )

    message_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("communication_accounts.account_id"), nullable=False, index=True)
    thread_id = Column(String(36), ForeignKey("message_threads.thread_id"), nullable=False, index=True)
    provider_message_id = Column(String, nullable=True, index=True)
    provider_thread_id = Column(String, nullable=True, index=True)
    direction = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    sender = Column(String, nullable=False, index=True)
    recipients = Column(JSON, nullable=False, default=list)
    cc = Column(JSON, nullable=False, default=list)
    bcc = Column(JSON, nullable=False, default=list)
    subject = Column(String, nullable=False, index=True)
    body = Column(Text, nullable=False)
    snippet = Column(Text, nullable=False)
    labels = Column(JSON, nullable=False, default=list)
    is_read = Column(Integer, nullable=False, default=0, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True, index=True)
    received_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class CommunicationHistory(Base):
    __tablename__ = "communication_history"

    history_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("communication_accounts.account_id"), nullable=True, index=True)
    message_id = Column(String(36), ForeignKey("messages.message_id"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    detail = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)


class WhatsAppAccount(Base):
    __tablename__ = "whatsapp_accounts"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('whatsapp_cloud', 'twilio', 'meta_direct')",
            name="ck_whatsapp_account_provider",
        ),
    )

    account_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    phone_number = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False, default="whatsapp_cloud", index=True)
    status = Column(String, nullable=False, default="configured", index=True)
    last_sync = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class WhatsAppConversation(Base):
    __tablename__ = "whatsapp_conversations"

    conversation_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("whatsapp_accounts.account_id"), nullable=False, index=True)
    contact_phone = Column(String, nullable=False, index=True)
    contact_name = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="active", index=True)
    message_count = Column(Integer, nullable=False, default=0)
    last_message_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class WhatsAppTemplate(Base):
    __tablename__ = "whatsapp_templates"

    template_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("whatsapp_accounts.account_id"), nullable=True, index=True)
    template_name = Column(String, nullable=False, index=True)
    language = Column(String, nullable=False, default="en", index=True)
    body = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="approved", index=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="ck_whatsapp_message_direction",
        ),
        CheckConstraint(
            "message_type IN ('text', 'template')",
            name="ck_whatsapp_message_type",
        ),
        CheckConstraint(
            "status IN ('received', 'queued', 'sent', 'delivered', 'read', 'failed')",
            name="ck_whatsapp_message_status",
        ),
    )

    message_id = Column(String(36), primary_key=True, index=True)
    business_id = Column(String(36), ForeignKey("businesses.business_id"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("whatsapp_accounts.account_id"), nullable=False, index=True)
    conversation_id = Column(String(36), ForeignKey("whatsapp_conversations.conversation_id"), nullable=False, index=True)
    provider_message_id = Column(String, nullable=True, index=True)
    direction = Column(String, nullable=False, index=True)
    message_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    sender_phone = Column(String, nullable=False, index=True)
    recipient_phone = Column(String, nullable=False, index=True)
    body = Column(Text, nullable=False)
    template_name = Column(String, nullable=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    sent_at = Column(DateTime(timezone=True), nullable=True, index=True)
    received_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class JiraProject(Base):
    __tablename__ = "jira_projects"

    jira_project_id = Column(String(36), primary_key=True, index=True)
    project_key = Column(String, nullable=False, unique=True, index=True)
    jira_url = Column(Text, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    status = Column(String, nullable=False, default="configured", index=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True, index=True)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class JiraIssue(Base):
    __tablename__ = "jira_issues"
    __table_args__ = (
        CheckConstraint(
            "issue_type IN ('epic', 'story', 'technical_story')",
            name="ck_jira_issue_type",
        ),
        CheckConstraint(
            "source_type IN ('objective', 'task', 'engineering_task')",
            name="ck_jira_source_type",
        ),
    )

    jira_issue_id = Column(String(36), primary_key=True, index=True)
    jira_issue_key = Column(String, nullable=False, unique=True, index=True)
    project_key = Column(String, nullable=False, index=True)
    issue_type = Column(String, nullable=False, index=True)
    source_type = Column(String, nullable=False, index=True)
    source_id = Column(String, nullable=False, index=True)
    parent_jira_issue_key = Column(String, nullable=True, index=True)
    summary = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="created", index=True)
    url = Column(Text, nullable=True)
    raw = Column(JSON, nullable=False, default=dict)
    synced_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, index=True)


class JiraSyncHistory(Base):
    __tablename__ = "jira_sync_history"

    jira_sync_id = Column(String(36), primary_key=True, index=True)
    project_key = Column(String, nullable=False, index=True)
    objective_id = Column(String(36), nullable=True, index=True)
    status = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    issue_count = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=False, index=True)

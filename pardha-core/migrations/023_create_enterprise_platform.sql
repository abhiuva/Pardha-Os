CREATE TABLE IF NOT EXISTS tenants (
    tenant_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    slug VARCHAR NOT NULL UNIQUE,
    plan VARCHAR NOT NULL DEFAULT 'free_trial',
    status VARCHAR NOT NULL DEFAULT 'active',
    data_region VARCHAR NOT NULL DEFAULT 'us',
    security_profile JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(tenant_id);
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(tenant_id);
CREATE INDEX IF NOT EXISTS ix_businesses_tenant_id ON businesses(tenant_id);
CREATE INDEX IF NOT EXISTS ix_auth_users_tenant_id ON auth_users(tenant_id);

CREATE TABLE IF NOT EXISTS tenant_users (
    membership_id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(tenant_id),
    user_id VARCHAR(36) NOT NULL REFERENCES auth_users(user_id),
    role VARCHAR NOT NULL,
    permissions JSON NOT NULL DEFAULT '[]',
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_tenant_users_tenant_id ON tenant_users(tenant_id);
CREATE INDEX IF NOT EXISTS ix_tenant_users_user_id ON tenant_users(user_id);

CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
    refresh_token_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES auth_users(user_id),
    tenant_id VARCHAR(36) REFERENCES tenants(tenant_id),
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) REFERENCES tenants(tenant_id),
    business_id VARCHAR(36) REFERENCES businesses(business_id),
    user_id VARCHAR(36) REFERENCES auth_users(user_id),
    actor_email VARCHAR,
    action VARCHAR NOT NULL,
    resource_type VARCHAR NOT NULL,
    resource_id VARCHAR,
    capability_id VARCHAR(120),
    conversation_id VARCHAR(36),
    approval_id VARCHAR(36),
    execution_id VARCHAR(36),
    outcome VARCHAR NOT NULL DEFAULT 'success',
    rollback JSON NOT NULL DEFAULT '{}',
    ip_address VARCHAR,
    user_agent TEXT,
    metadata JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_business_id ON audit_logs(business_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at);

CREATE TABLE IF NOT EXISTS observability_metrics (
    metric_id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) REFERENCES tenants(tenant_id),
    business_id VARCHAR(36) REFERENCES businesses(business_id),
    metric_type VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    value INTEGER NOT NULL DEFAULT 0,
    unit VARCHAR NOT NULL DEFAULT 'count',
    dimensions JSON NOT NULL DEFAULT '{}',
    captured_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS billing_subscriptions (
    subscription_id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL UNIQUE REFERENCES tenants(tenant_id),
    plan VARCHAR NOT NULL DEFAULT 'free_trial',
    status VARCHAR NOT NULL DEFAULT 'trialing',
    trial_ends_at TIMESTAMPTZ,
    limits JSON NOT NULL DEFAULT '{}',
    usage JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS enterprise_integrations (
    integration_id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(tenant_id),
    provider VARCHAR NOT NULL,
    auth_type VARCHAR NOT NULL DEFAULT 'oauth',
    status VARCHAR NOT NULL DEFAULT 'not_configured',
    scopes JSON NOT NULL DEFAULT '[]',
    configuration JSON NOT NULL DEFAULT '{}',
    secret_reference VARCHAR,
    rotation_due_at TIMESTAMPTZ,
    last_checked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS deployment_profiles (
    profile_id VARCHAR(36) PRIMARY KEY,
    environment VARCHAR NOT NULL UNIQUE,
    docker_ready INTEGER NOT NULL DEFAULT 1,
    kubernetes_ready INTEGER NOT NULL DEFAULT 1,
    configuration JSON NOT NULL DEFAULT '{}',
    health_checks JSON NOT NULL DEFAULT '[]',
    backup_policy JSON NOT NULL DEFAULT '{}',
    restore_policy JSON NOT NULL DEFAULT '{}',
    status VARCHAR NOT NULL DEFAULT 'ready',
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_governance_records (
    governance_id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) REFERENCES tenants(tenant_id),
    business_id VARCHAR(36) REFERENCES businesses(business_id),
    reasoning_provider VARCHAR NOT NULL DEFAULT 'deterministic',
    model_version VARCHAR NOT NULL DEFAULT 'none',
    prompt_version VARCHAR NOT NULL DEFAULT 'v1',
    capability_id VARCHAR(120),
    conversation_id VARCHAR(36),
    confidence INTEGER NOT NULL DEFAULT 0,
    evidence JSON NOT NULL DEFAULT '[]',
    human_approval INTEGER NOT NULL DEFAULT 0,
    provider_switch_ready INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS feature_flags (
    flag_id VARCHAR(36) PRIMARY KEY,
    key VARCHAR NOT NULL UNIQUE,
    name VARCHAR NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 0,
    beta INTEGER NOT NULL DEFAULT 0,
    tenant_id VARCHAR(36) REFERENCES tenants(tenant_id),
    rollout_percentage INTEGER NOT NULL DEFAULT 0,
    emergency_disabled INTEGER NOT NULL DEFAULT 0,
    rules JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

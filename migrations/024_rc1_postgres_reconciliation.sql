-- RC1 PostgreSQL reconciliation.
-- Non-destructive: adds missing ownership columns, backfills existing rows,
-- restores migration history for reconciled sprint migrations, and never drops data.

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    slug VARCHAR NOT NULL UNIQUE,
    plan VARCHAR NOT NULL DEFAULT 'free_trial',
    status VARCHAR NOT NULL DEFAULT 'active',
    data_region VARCHAR NOT NULL DEFAULT 'us',
    security_profile JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO tenants (tenant_id, name, slug, plan, status, data_region, security_profile, created_at, updated_at)
VALUES (
    '55555555-5555-4555-8555-555555555555',
    'Pardha Internal',
    'pardha-internal',
    'enterprise',
    'active',
    'us',
    '{"jwt": true, "refresh_tokens": true, "mfa_ready": true, "rbac": "capability_based", "audit": "all_actions"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (slug) DO UPDATE SET
    plan = EXCLUDED.plan,
    status = EXCLUDED.status,
    security_profile = EXCLUDED.security_profile,
    updated_at = CURRENT_TIMESTAMP;

ALTER TABLE businesses ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36);
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36);

UPDATE businesses
SET tenant_id = (SELECT tenant_id FROM tenants WHERE slug = 'pardha-internal')
WHERE tenant_id IS NULL;

UPDATE auth_users
SET tenant_id = (SELECT tenant_id FROM tenants WHERE slug = 'pardha-internal')
WHERE tenant_id IS NULL;

ALTER TABLE knowledge ADD COLUMN IF NOT EXISTS business_id VARCHAR(36);
ALTER TABLE knowledge_imports ADD COLUMN IF NOT EXISTS business_id VARCHAR(36);
ALTER TABLE objectives ADD COLUMN IF NOT EXISTS business_id VARCHAR(36);
ALTER TABLE events ADD COLUMN IF NOT EXISTS business_id VARCHAR(36);
ALTER TABLE memories ADD COLUMN IF NOT EXISTS business_id VARCHAR(36);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS business_id VARCHAR(36);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS business_id VARCHAR(36);
ALTER TABLE agent_collaborations ADD COLUMN IF NOT EXISTS business_id VARCHAR(36);
ALTER TABLE agent_executions ADD COLUMN IF NOT EXISTS business_id VARCHAR(36);
ALTER TABLE agent_reasoning ADD COLUMN IF NOT EXISTS business_id VARCHAR(36);

UPDATE knowledge
SET business_id = (
    SELECT business_id FROM businesses
    WHERE lower(businesses.business_name) = lower(knowledge.business_name)
    LIMIT 1
)
WHERE business_id IS NULL;

UPDATE knowledge_imports
SET business_id = (
    SELECT business_id FROM businesses
    WHERE lower(businesses.business_name) = lower(knowledge_imports.business_name)
    LIMIT 1
)
WHERE business_id IS NULL;

UPDATE objectives
SET business_id = (
    SELECT business_id FROM businesses
    WHERE lower(businesses.business_name) = lower(objectives.business_name)
    LIMIT 1
)
WHERE business_id IS NULL;

UPDATE events
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360' LIMIT 1)
WHERE business_id IS NULL;

UPDATE memories
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360' LIMIT 1)
WHERE business_id IS NULL;

UPDATE tasks
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360' LIMIT 1)
WHERE business_id IS NULL;

UPDATE projects
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360' LIMIT 1)
WHERE business_id IS NULL;

UPDATE agent_collaborations
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360' LIMIT 1)
WHERE business_id IS NULL;

UPDATE agent_executions
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360' LIMIT 1)
WHERE business_id IS NULL;

UPDATE agent_reasoning
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360' LIMIT 1)
WHERE business_id IS NULL;

CREATE INDEX IF NOT EXISTS ix_businesses_tenant_id ON businesses(tenant_id);
CREATE INDEX IF NOT EXISTS ix_auth_users_tenant_id ON auth_users(tenant_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_business_id ON knowledge(business_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_imports_business_id ON knowledge_imports(business_id);
CREATE INDEX IF NOT EXISTS ix_objectives_business_id ON objectives(business_id);
CREATE INDEX IF NOT EXISTS ix_events_business_id ON events(business_id);
CREATE INDEX IF NOT EXISTS ix_memories_business_id ON memories(business_id);
CREATE INDEX IF NOT EXISTS ix_tasks_business_id ON tasks(business_id);
CREATE INDEX IF NOT EXISTS ix_projects_business_id ON projects(business_id);
CREATE INDEX IF NOT EXISTS ix_agent_collaborations_business_id ON agent_collaborations(business_id);
CREATE INDEX IF NOT EXISTS ix_agent_executions_business_id ON agent_executions(business_id);
CREATE INDEX IF NOT EXISTS ix_agent_reasoning_business_id ON agent_reasoning(business_id);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'businesses_tenant_id_fkey') THEN
        ALTER TABLE businesses ADD CONSTRAINT businesses_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'auth_users_tenant_id_fkey') THEN
        ALTER TABLE auth_users ADD CONSTRAINT auth_users_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'knowledge_business_id_fkey') THEN
        ALTER TABLE knowledge ADD CONSTRAINT knowledge_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'knowledge_imports_business_id_fkey') THEN
        ALTER TABLE knowledge_imports ADD CONSTRAINT knowledge_imports_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'objectives_business_id_fkey') THEN
        ALTER TABLE objectives ADD CONSTRAINT objectives_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'events_business_id_fkey') THEN
        ALTER TABLE events ADD CONSTRAINT events_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'memories_business_id_fkey') THEN
        ALTER TABLE memories ADD CONSTRAINT memories_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tasks_business_id_fkey') THEN
        ALTER TABLE tasks ADD CONSTRAINT tasks_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'projects_business_id_fkey') THEN
        ALTER TABLE projects ADD CONSTRAINT projects_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'agent_collaborations_business_id_fkey') THEN
        ALTER TABLE agent_collaborations ADD CONSTRAINT agent_collaborations_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'agent_executions_business_id_fkey') THEN
        ALTER TABLE agent_executions ADD CONSTRAINT agent_executions_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'agent_reasoning_business_id_fkey') THEN
        ALTER TABLE agent_reasoning ADD CONSTRAINT agent_reasoning_business_id_fkey FOREIGN KEY (business_id) REFERENCES businesses(business_id) NOT VALID;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_migrations (version)
VALUES
    ('009_create_jira_connector.sql'),
    ('010_create_business_context.sql'),
    ('011_create_communications.sql'),
    ('012_create_whatsapp_connector.sql'),
    ('013_create_sales_crm.sql'),
    ('014_create_marketing_workspace.sql'),
    ('015_create_customer_success.sql'),
    ('016_create_auth.sql'),
    ('017_create_chief_of_staff.sql'),
    ('018_create_capability_registry.sql'),
    ('019_create_conversation_engine.sql'),
    ('020_create_planning_engine.sql'),
    ('021_create_universal_runtime.sql'),
    ('022_create_software_factory.sql'),
    ('023_create_enterprise_platform.sql'),
    ('024_rc1_postgres_reconciliation.sql')
ON CONFLICT (version) DO NOTHING;

CREATE TABLE IF NOT EXISTS runtime_executions (
    execution_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    goal_id VARCHAR(36),
    plan_id VARCHAR(36),
    execution_graph JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_stage VARCHAR NOT NULL DEFAULT 'queued',
    current_capability VARCHAR(120),
    logs JSONB NOT NULL DEFAULT '[]'::jsonb,
    retries INTEGER NOT NULL DEFAULT 0,
    progress INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb,
    rollback JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR NOT NULL DEFAULT 'queued',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS department_runtimes (
    department_id VARCHAR(80) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    name VARCHAR NOT NULL,
    owner VARCHAR NOT NULL DEFAULT 'Founder',
    objectives JSONB NOT NULL DEFAULT '[]'::jsonb,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    current_work JSONB NOT NULL DEFAULT '[]'::jsonb,
    queue JSONB NOT NULL DEFAULT '[]'::jsonb,
    kpis JSONB NOT NULL DEFAULT '{}'::jsonb,
    health VARCHAR NOT NULL DEFAULT 'healthy',
    current_load INTEGER NOT NULL DEFAULT 0,
    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_queue_items (
    queue_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    execution_id VARCHAR(36) REFERENCES runtime_executions(execution_id),
    plan_id VARCHAR(36),
    capability_id VARCHAR(120),
    priority INTEGER NOT NULL DEFAULT 50,
    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb,
    retry_count INTEGER NOT NULL DEFAULT 0,
    timeout_ms INTEGER NOT NULL DEFAULT 30000,
    scheduled_for TIMESTAMPTZ,
    recurring INTEGER NOT NULL DEFAULT 0,
    delay_until TIMESTAMPTZ,
    status VARCHAR NOT NULL DEFAULT 'queued',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_runtime_invocations (
    invocation_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    tool_name VARCHAR NOT NULL,
    capability_id VARCHAR(120),
    execution_id VARCHAR(36) REFERENCES runtime_executions(execution_id),
    status VARCHAR NOT NULL DEFAULT 'queued',
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB,
    error TEXT,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_notifications (
    notification_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    priority VARCHAR NOT NULL DEFAULT 'medium',
    category VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'unread',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    read_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS automation_rules (
    rule_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) REFERENCES businesses(business_id),
    name VARCHAR NOT NULL,
    trigger_event VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 50,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS business_timeline_events (
    timeline_event_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    event_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    source VARCHAR NOT NULL DEFAULT 'runtime',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_runtime_executions_business_id ON runtime_executions(business_id);
CREATE INDEX IF NOT EXISTS ix_runtime_executions_status ON runtime_executions(status);
CREATE INDEX IF NOT EXISTS ix_department_runtimes_business_id ON department_runtimes(business_id);
CREATE INDEX IF NOT EXISTS ix_runtime_queue_items_business_id ON runtime_queue_items(business_id);
CREATE INDEX IF NOT EXISTS ix_runtime_queue_items_status ON runtime_queue_items(status);
CREATE INDEX IF NOT EXISTS ix_tool_runtime_invocations_business_id ON tool_runtime_invocations(business_id);
CREATE INDEX IF NOT EXISTS ix_runtime_notifications_business_id ON runtime_notifications(business_id);
CREATE INDEX IF NOT EXISTS ix_runtime_notifications_status ON runtime_notifications(status);
CREATE INDEX IF NOT EXISTS ix_automation_rules_trigger_event ON automation_rules(trigger_event);
CREATE INDEX IF NOT EXISTS ix_business_timeline_events_business_id ON business_timeline_events(business_id);

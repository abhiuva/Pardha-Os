CREATE TABLE IF NOT EXISTS capabilities (
    capability_id VARCHAR(120) PRIMARY KEY,
    name VARCHAR NOT NULL,
    version VARCHAR NOT NULL DEFAULT '1.0.0',
    description TEXT NOT NULL,
    supported_intents JSONB NOT NULL DEFAULT '[]'::jsonb,
    business_domains JSONB NOT NULL DEFAULT '[]'::jsonb,
    required_inputs JSONB NOT NULL DEFAULT '[]'::jsonb,
    outputs JSONB NOT NULL DEFAULT '[]'::jsonb,
    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    health VARCHAR NOT NULL DEFAULT 'unknown',
    supports_hitl INTEGER NOT NULL DEFAULT 0,
    supports_streaming INTEGER NOT NULL DEFAULT 0,
    supports_learning INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 50,
    estimated_runtime_ms INTEGER NOT NULL DEFAULT 100,
    registration_method VARCHAR NOT NULL DEFAULT 'automatic',
    current_status VARCHAR NOT NULL DEFAULT 'registered',
    planner_interface JSONB NOT NULL DEFAULT '{}'::jsonb,
    execution_adapter VARCHAR,
    execution_count INTEGER NOT NULL DEFAULT 0,
    last_executed_at TIMESTAMPTZ,
    registered_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_capabilities_name ON capabilities(name);
CREATE INDEX IF NOT EXISTS ix_capabilities_version ON capabilities(version);
CREATE INDEX IF NOT EXISTS ix_capabilities_health ON capabilities(health);
CREATE INDEX IF NOT EXISTS ix_capabilities_supports_hitl ON capabilities(supports_hitl);
CREATE INDEX IF NOT EXISTS ix_capabilities_supports_streaming ON capabilities(supports_streaming);
CREATE INDEX IF NOT EXISTS ix_capabilities_supports_learning ON capabilities(supports_learning);
CREATE INDEX IF NOT EXISTS ix_capabilities_priority ON capabilities(priority);
CREATE INDEX IF NOT EXISTS ix_capabilities_estimated_runtime_ms ON capabilities(estimated_runtime_ms);
CREATE INDEX IF NOT EXISTS ix_capabilities_registration_method ON capabilities(registration_method);
CREATE INDEX IF NOT EXISTS ix_capabilities_current_status ON capabilities(current_status);
CREATE INDEX IF NOT EXISTS ix_capabilities_execution_adapter ON capabilities(execution_adapter);
CREATE INDEX IF NOT EXISTS ix_capabilities_execution_count ON capabilities(execution_count);
CREATE INDEX IF NOT EXISTS ix_capabilities_last_executed_at ON capabilities(last_executed_at);
CREATE INDEX IF NOT EXISTS ix_capabilities_registered_at ON capabilities(registered_at);
CREATE INDEX IF NOT EXISTS ix_capabilities_updated_at ON capabilities(updated_at);

CREATE TABLE IF NOT EXISTS capability_executions (
    execution_id VARCHAR(36) PRIMARY KEY,
    capability_id VARCHAR(120) NOT NULL REFERENCES capabilities(capability_id),
    business_id VARCHAR(36) REFERENCES businesses(business_id),
    intent VARCHAR NOT NULL,
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_payload JSONB,
    status VARCHAR NOT NULL,
    confidence INTEGER NOT NULL DEFAULT 0,
    runtime_ms INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_capability_executions_capability_id ON capability_executions(capability_id);
CREATE INDEX IF NOT EXISTS ix_capability_executions_business_id ON capability_executions(business_id);
CREATE INDEX IF NOT EXISTS ix_capability_executions_intent ON capability_executions(intent);
CREATE INDEX IF NOT EXISTS ix_capability_executions_status ON capability_executions(status);
CREATE INDEX IF NOT EXISTS ix_capability_executions_confidence ON capability_executions(confidence);
CREATE INDEX IF NOT EXISTS ix_capability_executions_runtime_ms ON capability_executions(runtime_ms);
CREATE INDEX IF NOT EXISTS ix_capability_executions_created_at ON capability_executions(created_at);

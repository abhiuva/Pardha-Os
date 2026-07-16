CREATE TABLE IF NOT EXISTS agent_executions (
    execution_id VARCHAR(36) PRIMARY KEY,
    cycle_id VARCHAR(36) NOT NULL,
    agent_name TEXT NOT NULL,
    status TEXT NOT NULL,
    output JSONB,
    error TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    CONSTRAINT ck_agent_execution_status CHECK (
        status IN ('running', 'succeeded', 'failed')
    )
);

CREATE INDEX IF NOT EXISTS ix_agent_executions_cycle_id ON agent_executions (cycle_id);
CREATE INDEX IF NOT EXISTS ix_agent_executions_agent_name ON agent_executions (agent_name);
CREATE INDEX IF NOT EXISTS ix_agent_executions_status ON agent_executions (status);
CREATE INDEX IF NOT EXISTS ix_agent_executions_started_at ON agent_executions (started_at);

CREATE TABLE IF NOT EXISTS agent_reasoning (
    reasoning_id VARCHAR(36) PRIMARY KEY,
    agent_name VARCHAR NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT NOT NULL,
    model VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_agent_reasoning_agent_name ON agent_reasoning (agent_name);
CREATE INDEX IF NOT EXISTS ix_agent_reasoning_model ON agent_reasoning (model);
CREATE INDEX IF NOT EXISTS ix_agent_reasoning_source ON agent_reasoning (source);
CREATE INDEX IF NOT EXISTS ix_agent_reasoning_timestamp ON agent_reasoning (timestamp);

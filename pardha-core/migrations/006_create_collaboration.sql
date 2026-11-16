CREATE TABLE IF NOT EXISTS objectives (
    objective_id VARCHAR(36) PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_objective_priority CHECK (
        priority IN ('critical', 'high', 'medium', 'low')
    ),
    CONSTRAINT ck_objective_status CHECK (
        status IN ('active', 'completed', 'cancelled')
    )
);

CREATE TABLE IF NOT EXISTS agent_collaborations (
    collaboration_id VARCHAR(36) PRIMARY KEY,
    objective_id VARCHAR(36) NOT NULL,
    source_agent TEXT NOT NULL,
    target_agent TEXT NOT NULL,
    action TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    status TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_objectives_priority ON objectives (priority);
CREATE INDEX IF NOT EXISTS ix_objectives_status ON objectives (status);
CREATE INDEX IF NOT EXISTS ix_objectives_created_at ON objectives (created_at);
CREATE INDEX IF NOT EXISTS ix_agent_collaborations_objective_id ON agent_collaborations (objective_id);
CREATE INDEX IF NOT EXISTS ix_agent_collaborations_source_agent ON agent_collaborations (source_agent);
CREATE INDEX IF NOT EXISTS ix_agent_collaborations_target_agent ON agent_collaborations (target_agent);
CREATE INDEX IF NOT EXISTS ix_agent_collaborations_action ON agent_collaborations (action);
CREATE INDEX IF NOT EXISTS ix_agent_collaborations_step_order ON agent_collaborations (step_order);
CREATE INDEX IF NOT EXISTS ix_agent_collaborations_status ON agent_collaborations (status);
CREATE INDEX IF NOT EXISTS ix_agent_collaborations_created_at ON agent_collaborations (created_at);

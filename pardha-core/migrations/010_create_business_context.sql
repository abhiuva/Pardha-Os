CREATE TABLE IF NOT EXISTS businesses (
    business_id VARCHAR(36) PRIMARY KEY,
    business_name VARCHAR NOT NULL UNIQUE,
    business_type VARCHAR NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO businesses (business_id, business_name, business_type, description, status)
VALUES
    ('11111111-1111-4111-8111-111111111111', 'UVA', 'education', 'UVA business operating context.', 'active'),
    ('22222222-2222-4222-8222-222222222222', 'DP360', 'data_platform', 'DP360 business operating context.', 'active'),
    ('33333333-3333-4333-8333-333333333333', 'EatOnTime', 'foodtech', 'EatOnTime school meal operations context.', 'active'),
    ('44444444-4444-4444-8444-444444444444', 'Trevia EV', 'ev', 'Trevia EV electric mobility operating context.', 'active')
ON CONFLICT (business_name) DO NOTHING;

ALTER TABLE knowledge ADD COLUMN business_id VARCHAR(36);
ALTER TABLE knowledge_imports ADD COLUMN business_id VARCHAR(36);
ALTER TABLE objectives ADD COLUMN business_id VARCHAR(36);
ALTER TABLE events ADD COLUMN business_id VARCHAR(36);
ALTER TABLE memories ADD COLUMN business_id VARCHAR(36);
ALTER TABLE tasks ADD COLUMN business_id VARCHAR(36);
ALTER TABLE projects ADD COLUMN business_id VARCHAR(36);
ALTER TABLE agent_collaborations ADD COLUMN business_id VARCHAR(36);
ALTER TABLE agent_executions ADD COLUMN business_id VARCHAR(36);
ALTER TABLE agent_reasoning ADD COLUMN business_id VARCHAR(36);

UPDATE knowledge
SET business_id = (SELECT business_id FROM businesses WHERE lower(businesses.business_name) = lower(knowledge.business_name))
WHERE business_id IS NULL;

UPDATE knowledge_imports
SET business_id = (SELECT business_id FROM businesses WHERE lower(businesses.business_name) = lower(knowledge_imports.business_name))
WHERE business_id IS NULL;

UPDATE objectives
SET business_id = (SELECT business_id FROM businesses WHERE lower(businesses.business_name) = lower(objectives.business_name))
WHERE business_id IS NULL;

UPDATE events
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360')
WHERE business_id IS NULL;

UPDATE memories
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360')
WHERE business_id IS NULL;

UPDATE tasks
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360')
WHERE business_id IS NULL;

UPDATE projects
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360')
WHERE business_id IS NULL;

UPDATE agent_collaborations
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360')
WHERE business_id IS NULL;

UPDATE agent_executions
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360')
WHERE business_id IS NULL;

UPDATE agent_reasoning
SET business_id = (SELECT business_id FROM businesses WHERE business_name = 'DP360')
WHERE business_id IS NULL;

CREATE INDEX IF NOT EXISTS ix_businesses_business_name ON businesses (business_name);
CREATE INDEX IF NOT EXISTS ix_businesses_business_type ON businesses (business_type);
CREATE INDEX IF NOT EXISTS ix_businesses_status ON businesses (status);
CREATE INDEX IF NOT EXISTS ix_knowledge_business_id ON knowledge (business_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_imports_business_id ON knowledge_imports (business_id);
CREATE INDEX IF NOT EXISTS ix_objectives_business_id ON objectives (business_id);
CREATE INDEX IF NOT EXISTS ix_events_business_id ON events (business_id);
CREATE INDEX IF NOT EXISTS ix_memories_business_id ON memories (business_id);
CREATE INDEX IF NOT EXISTS ix_tasks_business_id ON tasks (business_id);
CREATE INDEX IF NOT EXISTS ix_projects_business_id ON projects (business_id);
CREATE INDEX IF NOT EXISTS ix_agent_collaborations_business_id ON agent_collaborations (business_id);
CREATE INDEX IF NOT EXISTS ix_agent_executions_business_id ON agent_executions (business_id);
CREATE INDEX IF NOT EXISTS ix_agent_reasoning_business_id ON agent_reasoning (business_id);

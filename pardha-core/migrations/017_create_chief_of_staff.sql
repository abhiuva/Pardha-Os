CREATE TABLE IF NOT EXISTS chief_conversations (
    conversation_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    title VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_chief_conversations_business_id ON chief_conversations(business_id);
CREATE INDEX IF NOT EXISTS ix_chief_conversations_title ON chief_conversations(title);
CREATE INDEX IF NOT EXISTS ix_chief_conversations_status ON chief_conversations(status);
CREATE INDEX IF NOT EXISTS ix_chief_conversations_created_at ON chief_conversations(created_at);
CREATE INDEX IF NOT EXISTS ix_chief_conversations_updated_at ON chief_conversations(updated_at);

CREATE TABLE IF NOT EXISTS chief_messages (
    message_id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL REFERENCES chief_conversations(conversation_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    intent VARCHAR NOT NULL DEFAULT 'general',
    rich_response JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_chief_messages_conversation_id ON chief_messages(conversation_id);
CREATE INDEX IF NOT EXISTS ix_chief_messages_business_id ON chief_messages(business_id);
CREATE INDEX IF NOT EXISTS ix_chief_messages_role ON chief_messages(role);
CREATE INDEX IF NOT EXISTS ix_chief_messages_intent ON chief_messages(intent);
CREATE INDEX IF NOT EXISTS ix_chief_messages_created_at ON chief_messages(created_at);

CREATE TABLE IF NOT EXISTS founder_goals (
    goal_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    title VARCHAR NOT NULL,
    priority VARCHAR NOT NULL DEFAULT 'high',
    due_date TIMESTAMPTZ,
    owner VARCHAR NOT NULL DEFAULT 'Founder',
    status VARCHAR NOT NULL DEFAULT 'active',
    success_metrics JSONB NOT NULL DEFAULT '[]'::jsonb,
    objective_id VARCHAR(36),
    plans JSONB NOT NULL DEFAULT '{}'::jsonb,
    timeline JSONB NOT NULL DEFAULT '[]'::jsonb,
    daily_followups JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_founder_goals_business_id ON founder_goals(business_id);
CREATE INDEX IF NOT EXISTS ix_founder_goals_title ON founder_goals(title);
CREATE INDEX IF NOT EXISTS ix_founder_goals_priority ON founder_goals(priority);
CREATE INDEX IF NOT EXISTS ix_founder_goals_due_date ON founder_goals(due_date);
CREATE INDEX IF NOT EXISTS ix_founder_goals_owner ON founder_goals(owner);
CREATE INDEX IF NOT EXISTS ix_founder_goals_status ON founder_goals(status);
CREATE INDEX IF NOT EXISTS ix_founder_goals_objective_id ON founder_goals(objective_id);
CREATE INDEX IF NOT EXISTS ix_founder_goals_created_at ON founder_goals(created_at);
CREATE INDEX IF NOT EXISTS ix_founder_goals_updated_at ON founder_goals(updated_at);

CREATE TABLE IF NOT EXISTS conversation_sessions (
    conversation_id VARCHAR(36) PRIMARY KEY,
    title VARCHAR NOT NULL,
    business_id VARCHAR(36) REFERENCES businesses(business_id),
    owner VARCHAR NOT NULL DEFAULT 'Founder',
    conversation_type VARCHAR NOT NULL DEFAULT 'general',
    pinned INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0,
    summary TEXT NOT NULL DEFAULT '',
    context_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_conversation_sessions_title ON conversation_sessions(title);
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_business_id ON conversation_sessions(business_id);
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_owner ON conversation_sessions(owner);
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_conversation_type ON conversation_sessions(conversation_type);
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_pinned ON conversation_sessions(pinned);
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_archived ON conversation_sessions(archived);
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_created_at ON conversation_sessions(created_at);
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_updated_at ON conversation_sessions(updated_at);

CREATE TABLE IF NOT EXISTS conversation_messages (
    message_id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversation_sessions(conversation_id),
    business_id VARCHAR(36) REFERENCES businesses(business_id),
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    intent VARCHAR NOT NULL DEFAULT 'general',
    conversation_type VARCHAR NOT NULL DEFAULT 'general',
    context_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    capability_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_conversation_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_business_id ON conversation_messages(business_id);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_role ON conversation_messages(role);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_intent ON conversation_messages(intent);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_conversation_type ON conversation_messages(conversation_type);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_created_at ON conversation_messages(created_at);

CREATE TABLE IF NOT EXISTS conversation_timeline_events (
    timeline_event_id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversation_sessions(conversation_id),
    message_id VARCHAR(36) REFERENCES conversation_messages(message_id),
    event_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    detail TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_conversation_timeline_events_conversation_id ON conversation_timeline_events(conversation_id);
CREATE INDEX IF NOT EXISTS ix_conversation_timeline_events_message_id ON conversation_timeline_events(message_id);
CREATE INDEX IF NOT EXISTS ix_conversation_timeline_events_event_type ON conversation_timeline_events(event_type);
CREATE INDEX IF NOT EXISTS ix_conversation_timeline_events_created_at ON conversation_timeline_events(created_at);

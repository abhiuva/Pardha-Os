CREATE TABLE IF NOT EXISTS communication_accounts (
    account_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    provider VARCHAR NOT NULL,
    account_name VARCHAR NOT NULL,
    email VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'configured',
    last_sync TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_communication_account_provider CHECK (provider IN ('gmail', 'outlook'))
);

CREATE TABLE IF NOT EXISTS message_threads (
    thread_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    account_id VARCHAR(36) NOT NULL REFERENCES communication_accounts(account_id),
    provider_thread_id VARCHAR,
    subject VARCHAR NOT NULL,
    participants JSONB NOT NULL DEFAULT '[]'::jsonb,
    unread_count INTEGER NOT NULL DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    message_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    account_id VARCHAR(36) NOT NULL REFERENCES communication_accounts(account_id),
    thread_id VARCHAR(36) NOT NULL REFERENCES message_threads(thread_id),
    provider_message_id VARCHAR,
    provider_thread_id VARCHAR,
    direction VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    sender VARCHAR NOT NULL,
    recipients JSONB NOT NULL DEFAULT '[]'::jsonb,
    cc JSONB NOT NULL DEFAULT '[]'::jsonb,
    bcc JSONB NOT NULL DEFAULT '[]'::jsonb,
    subject VARCHAR NOT NULL,
    body TEXT NOT NULL,
    snippet TEXT NOT NULL,
    labels JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_read INTEGER NOT NULL DEFAULT 0,
    sent_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_message_direction CHECK (direction IN ('inbound', 'outbound')),
    CONSTRAINT ck_message_status CHECK (status IN ('received', 'draft', 'sent', 'failed'))
);

CREATE TABLE IF NOT EXISTS communication_history (
    history_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    account_id VARCHAR(36) REFERENCES communication_accounts(account_id),
    message_id VARCHAR(36) REFERENCES messages(message_id),
    action VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    detail TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_communication_accounts_business_id ON communication_accounts (business_id);
CREATE INDEX IF NOT EXISTS ix_communication_accounts_provider ON communication_accounts (provider);
CREATE INDEX IF NOT EXISTS ix_communication_accounts_email ON communication_accounts (email);
CREATE INDEX IF NOT EXISTS ix_communication_accounts_status ON communication_accounts (status);
CREATE INDEX IF NOT EXISTS ix_communication_accounts_last_sync ON communication_accounts (last_sync);
CREATE INDEX IF NOT EXISTS ix_message_threads_business_id ON message_threads (business_id);
CREATE INDEX IF NOT EXISTS ix_message_threads_account_id ON message_threads (account_id);
CREATE INDEX IF NOT EXISTS ix_message_threads_provider_thread_id ON message_threads (provider_thread_id);
CREATE INDEX IF NOT EXISTS ix_message_threads_last_message_at ON message_threads (last_message_at);
CREATE INDEX IF NOT EXISTS ix_messages_business_id ON messages (business_id);
CREATE INDEX IF NOT EXISTS ix_messages_account_id ON messages (account_id);
CREATE INDEX IF NOT EXISTS ix_messages_thread_id ON messages (thread_id);
CREATE INDEX IF NOT EXISTS ix_messages_provider_message_id ON messages (provider_message_id);
CREATE INDEX IF NOT EXISTS ix_messages_direction ON messages (direction);
CREATE INDEX IF NOT EXISTS ix_messages_status ON messages (status);
CREATE INDEX IF NOT EXISTS ix_messages_subject ON messages (subject);
CREATE INDEX IF NOT EXISTS ix_messages_is_read ON messages (is_read);
CREATE INDEX IF NOT EXISTS ix_messages_sent_at ON messages (sent_at);
CREATE INDEX IF NOT EXISTS ix_messages_received_at ON messages (received_at);
CREATE INDEX IF NOT EXISTS ix_communication_history_business_id ON communication_history (business_id);
CREATE INDEX IF NOT EXISTS ix_communication_history_account_id ON communication_history (account_id);
CREATE INDEX IF NOT EXISTS ix_communication_history_message_id ON communication_history (message_id);
CREATE INDEX IF NOT EXISTS ix_communication_history_action ON communication_history (action);
CREATE INDEX IF NOT EXISTS ix_communication_history_status ON communication_history (status);
CREATE INDEX IF NOT EXISTS ix_communication_history_created_at ON communication_history (created_at);

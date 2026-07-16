CREATE TABLE IF NOT EXISTS whatsapp_accounts (
    account_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    phone_number VARCHAR NOT NULL,
    provider VARCHAR NOT NULL DEFAULT 'whatsapp_cloud',
    status VARCHAR NOT NULL DEFAULT 'configured',
    last_sync TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_whatsapp_account_provider CHECK (provider IN ('whatsapp_cloud', 'twilio', 'meta_direct'))
);

CREATE TABLE IF NOT EXISTS whatsapp_conversations (
    conversation_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    account_id VARCHAR(36) NOT NULL REFERENCES whatsapp_accounts(account_id),
    contact_phone VARCHAR NOT NULL,
    contact_name VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'active',
    message_count INTEGER NOT NULL DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS whatsapp_templates (
    template_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    account_id VARCHAR(36) REFERENCES whatsapp_accounts(account_id),
    template_name VARCHAR NOT NULL,
    language VARCHAR NOT NULL DEFAULT 'en',
    body TEXT NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'approved',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS whatsapp_messages (
    message_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    account_id VARCHAR(36) NOT NULL REFERENCES whatsapp_accounts(account_id),
    conversation_id VARCHAR(36) NOT NULL REFERENCES whatsapp_conversations(conversation_id),
    provider_message_id VARCHAR,
    direction VARCHAR NOT NULL,
    message_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    sender_phone VARCHAR NOT NULL,
    recipient_phone VARCHAR NOT NULL,
    body TEXT NOT NULL,
    template_name VARCHAR,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    sent_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_whatsapp_message_direction CHECK (direction IN ('inbound', 'outbound')),
    CONSTRAINT ck_whatsapp_message_type CHECK (message_type IN ('text', 'template')),
    CONSTRAINT ck_whatsapp_message_status CHECK (status IN ('received', 'queued', 'sent', 'delivered', 'read', 'failed'))
);

CREATE INDEX IF NOT EXISTS ix_whatsapp_accounts_business_id ON whatsapp_accounts (business_id);
CREATE INDEX IF NOT EXISTS ix_whatsapp_accounts_phone_number ON whatsapp_accounts (phone_number);
CREATE INDEX IF NOT EXISTS ix_whatsapp_accounts_provider ON whatsapp_accounts (provider);
CREATE INDEX IF NOT EXISTS ix_whatsapp_accounts_status ON whatsapp_accounts (status);
CREATE INDEX IF NOT EXISTS ix_whatsapp_accounts_last_sync ON whatsapp_accounts (last_sync);
CREATE INDEX IF NOT EXISTS ix_whatsapp_conversations_business_id ON whatsapp_conversations (business_id);
CREATE INDEX IF NOT EXISTS ix_whatsapp_conversations_account_id ON whatsapp_conversations (account_id);
CREATE INDEX IF NOT EXISTS ix_whatsapp_conversations_contact_phone ON whatsapp_conversations (contact_phone);
CREATE INDEX IF NOT EXISTS ix_whatsapp_conversations_status ON whatsapp_conversations (status);
CREATE INDEX IF NOT EXISTS ix_whatsapp_conversations_last_message_at ON whatsapp_conversations (last_message_at);
CREATE INDEX IF NOT EXISTS ix_whatsapp_templates_business_id ON whatsapp_templates (business_id);
CREATE INDEX IF NOT EXISTS ix_whatsapp_templates_account_id ON whatsapp_templates (account_id);
CREATE INDEX IF NOT EXISTS ix_whatsapp_templates_template_name ON whatsapp_templates (template_name);
CREATE INDEX IF NOT EXISTS ix_whatsapp_templates_language ON whatsapp_templates (language);
CREATE INDEX IF NOT EXISTS ix_whatsapp_templates_status ON whatsapp_templates (status);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_business_id ON whatsapp_messages (business_id);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_account_id ON whatsapp_messages (account_id);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_conversation_id ON whatsapp_messages (conversation_id);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_provider_message_id ON whatsapp_messages (provider_message_id);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_direction ON whatsapp_messages (direction);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_message_type ON whatsapp_messages (message_type);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_status ON whatsapp_messages (status);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_sender_phone ON whatsapp_messages (sender_phone);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_recipient_phone ON whatsapp_messages (recipient_phone);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_template_name ON whatsapp_messages (template_name);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_sent_at ON whatsapp_messages (sent_at);
CREATE INDEX IF NOT EXISTS ix_whatsapp_messages_received_at ON whatsapp_messages (received_at);

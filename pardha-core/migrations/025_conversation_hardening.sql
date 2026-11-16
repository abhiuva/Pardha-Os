-- Pardha 3.0 Product Hardening Item 1.
-- Non-destructive operational learning store for founder preferences,
-- usage patterns, correction history, and workflow signals.

CREATE TABLE IF NOT EXISTS founder_operational_learning (
    learning_id VARCHAR(36) PRIMARY KEY,
    owner VARCHAR NOT NULL DEFAULT 'Founder',
    business_id VARCHAR(36) NULL REFERENCES businesses(business_id),
    signal_type VARCHAR NOT NULL,
    signal_key VARCHAR NOT NULL,
    signal_value JSON NOT NULL DEFAULT '{}',
    confidence INTEGER NOT NULL DEFAULT 60,
    source_conversation_id VARCHAR(36) NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_founder_operational_learning_owner ON founder_operational_learning(owner);
CREATE INDEX IF NOT EXISTS ix_founder_operational_learning_business_id ON founder_operational_learning(business_id);
CREATE INDEX IF NOT EXISTS ix_founder_operational_learning_signal_type ON founder_operational_learning(signal_type);
CREATE INDEX IF NOT EXISTS ix_founder_operational_learning_signal_key ON founder_operational_learning(signal_key);
CREATE INDEX IF NOT EXISTS ix_founder_operational_learning_confidence ON founder_operational_learning(confidence);
CREATE INDEX IF NOT EXISTS ix_founder_operational_learning_source_conversation_id ON founder_operational_learning(source_conversation_id);
CREATE INDEX IF NOT EXISTS ix_founder_operational_learning_created_at ON founder_operational_learning(created_at);
CREATE INDEX IF NOT EXISTS ix_founder_operational_learning_updated_at ON founder_operational_learning(updated_at);

INSERT INTO schema_migrations (version)
VALUES ('025_conversation_hardening')
ON CONFLICT (version) DO NOTHING;

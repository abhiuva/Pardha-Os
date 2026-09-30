CREATE TABLE IF NOT EXISTS hubspot_connector_configs (
    config_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL UNIQUE REFERENCES businesses(business_id),
    portal_id VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'not_configured',
    write_mode VARCHAR NOT NULL DEFAULT 'disabled',
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    secret_reference VARCHAR,
    last_checked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hubspot_connector_configs_business_id ON hubspot_connector_configs (business_id);
CREATE INDEX IF NOT EXISTS ix_hubspot_connector_configs_status ON hubspot_connector_configs (status);
CREATE INDEX IF NOT EXISTS ix_hubspot_connector_configs_write_mode ON hubspot_connector_configs (write_mode);

CREATE TABLE IF NOT EXISTS hubspot_sync_records (
    sync_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    lead_id VARCHAR(36) NOT NULL REFERENCES sales_leads(lead_id),
    local_contact_id VARCHAR(36),
    local_company_id VARCHAR(36),
    local_deal_id VARCHAR(36),
    hubspot_contact_id VARCHAR,
    hubspot_company_id VARCHAR,
    hubspot_deal_id VARCHAR,
    action VARCHAR NOT NULL DEFAULT 'draft',
    sync_status VARCHAR NOT NULL DEFAULT 'draft',
    duplicate_key VARCHAR,
    retry_count INTEGER NOT NULL DEFAULT 0,
    retryable INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    contact_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    company_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    deal_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hubspot_sync_records_business_id ON hubspot_sync_records (business_id);
CREATE INDEX IF NOT EXISTS ix_hubspot_sync_records_lead_id ON hubspot_sync_records (lead_id);
CREATE INDEX IF NOT EXISTS ix_hubspot_sync_records_sync_status ON hubspot_sync_records (sync_status);
CREATE INDEX IF NOT EXISTS ix_hubspot_sync_records_duplicate_key ON hubspot_sync_records (duplicate_key);
CREATE INDEX IF NOT EXISTS ix_hubspot_sync_records_retryable ON hubspot_sync_records (retryable);

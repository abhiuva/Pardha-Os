CREATE TABLE IF NOT EXISTS meta_connector_configs (
    config_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL UNIQUE REFERENCES businesses(business_id),
    ad_account_id VARCHAR,
    instagram_account_id VARCHAR,
    page_id VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'not_configured',
    authentication_status VARCHAR NOT NULL DEFAULT 'missing_credentials',
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    secret_reference VARCHAR,
    last_checked_at TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_meta_connector_configs_business_id ON meta_connector_configs (business_id);
CREATE INDEX IF NOT EXISTS ix_meta_connector_configs_ad_account_id ON meta_connector_configs (ad_account_id);
CREATE INDEX IF NOT EXISTS ix_meta_connector_configs_instagram_account_id ON meta_connector_configs (instagram_account_id);
CREATE INDEX IF NOT EXISTS ix_meta_connector_configs_page_id ON meta_connector_configs (page_id);
CREATE INDEX IF NOT EXISTS ix_meta_connector_configs_status ON meta_connector_configs (status);
CREATE INDEX IF NOT EXISTS ix_meta_connector_configs_authentication_status ON meta_connector_configs (authentication_status);
CREATE INDEX IF NOT EXISTS ix_meta_connector_configs_secret_reference ON meta_connector_configs (secret_reference);
CREATE INDEX IF NOT EXISTS ix_meta_connector_configs_last_checked_at ON meta_connector_configs (last_checked_at);
CREATE INDEX IF NOT EXISTS ix_meta_connector_configs_last_sync_at ON meta_connector_configs (last_sync_at);
CREATE INDEX IF NOT EXISTS ix_meta_connector_configs_created_at ON meta_connector_configs (created_at);
CREATE INDEX IF NOT EXISTS ix_meta_connector_configs_updated_at ON meta_connector_configs (updated_at);

CREATE TABLE IF NOT EXISTS meta_campaign_insights (
    insight_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    campaign_id VARCHAR(36) REFERENCES marketing_campaigns(campaign_id),
    external_campaign_id VARCHAR NOT NULL,
    campaign_name VARCHAR NOT NULL,
    source VARCHAR NOT NULL DEFAULT 'meta',
    channel VARCHAR NOT NULL DEFAULT 'Meta Ads',
    spend INTEGER NOT NULL DEFAULT 0,
    impressions INTEGER NOT NULL DEFAULT 0,
    reach INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    ctr INTEGER NOT NULL DEFAULT 0,
    cpc INTEGER NOT NULL DEFAULT 0,
    leads INTEGER NOT NULL DEFAULT 0,
    sync_status VARCHAR NOT NULL DEFAULT 'mock',
    error TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    captured_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_meta_campaign_insights_business_id ON meta_campaign_insights (business_id);
CREATE INDEX IF NOT EXISTS ix_meta_campaign_insights_campaign_id ON meta_campaign_insights (campaign_id);
CREATE INDEX IF NOT EXISTS ix_meta_campaign_insights_external_campaign_id ON meta_campaign_insights (external_campaign_id);
CREATE INDEX IF NOT EXISTS ix_meta_campaign_insights_campaign_name ON meta_campaign_insights (campaign_name);
CREATE INDEX IF NOT EXISTS ix_meta_campaign_insights_source ON meta_campaign_insights (source);
CREATE INDEX IF NOT EXISTS ix_meta_campaign_insights_channel ON meta_campaign_insights (channel);
CREATE INDEX IF NOT EXISTS ix_meta_campaign_insights_sync_status ON meta_campaign_insights (sync_status);
CREATE INDEX IF NOT EXISTS ix_meta_campaign_insights_captured_at ON meta_campaign_insights (captured_at);
CREATE INDEX IF NOT EXISTS ix_meta_campaign_insights_created_at ON meta_campaign_insights (created_at);
CREATE INDEX IF NOT EXISTS ix_meta_campaign_insights_updated_at ON meta_campaign_insights (updated_at);

CREATE TABLE IF NOT EXISTS marketing_campaigns (
    campaign_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    name VARCHAR NOT NULL,
    objective TEXT NOT NULL,
    audience JSONB NOT NULL DEFAULT '{}'::jsonb,
    channels JSONB NOT NULL DEFAULT '[]'::jsonb,
    budget INTEGER NOT NULL DEFAULT 0,
    goals JSONB NOT NULL DEFAULT '[]'::jsonb,
    kpis JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR NOT NULL DEFAULT 'active',
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    campaign_plan JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_marketing_campaigns_business_id ON marketing_campaigns(business_id);
CREATE INDEX IF NOT EXISTS ix_marketing_campaigns_name ON marketing_campaigns(name);
CREATE INDEX IF NOT EXISTS ix_marketing_campaigns_status ON marketing_campaigns(status);
CREATE INDEX IF NOT EXISTS ix_marketing_campaigns_start_date ON marketing_campaigns(start_date);
CREATE INDEX IF NOT EXISTS ix_marketing_campaigns_end_date ON marketing_campaigns(end_date);

CREATE TABLE IF NOT EXISTS marketing_content (
    content_id VARCHAR(36) PRIMARY KEY,
    campaign_id VARCHAR(36) NOT NULL REFERENCES marketing_campaigns(campaign_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    content_type VARCHAR NOT NULL,
    channel VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    body TEXT NOT NULL,
    call_to_action VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'draft',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_marketing_content_campaign_id ON marketing_content(campaign_id);
CREATE INDEX IF NOT EXISTS ix_marketing_content_business_id ON marketing_content(business_id);
CREATE INDEX IF NOT EXISTS ix_marketing_content_content_type ON marketing_content(content_type);
CREATE INDEX IF NOT EXISTS ix_marketing_content_channel ON marketing_content(channel);
CREATE INDEX IF NOT EXISTS ix_marketing_content_status ON marketing_content(status);

CREATE TABLE IF NOT EXISTS marketing_calendar_items (
    calendar_item_id VARCHAR(36) PRIMARY KEY,
    campaign_id VARCHAR(36) NOT NULL REFERENCES marketing_campaigns(campaign_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    title VARCHAR NOT NULL,
    channel VARCHAR NOT NULL,
    content_type VARCHAR NOT NULL,
    scheduled_for TIMESTAMPTZ NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'planned',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_marketing_calendar_items_campaign_id ON marketing_calendar_items(campaign_id);
CREATE INDEX IF NOT EXISTS ix_marketing_calendar_items_business_id ON marketing_calendar_items(business_id);
CREATE INDEX IF NOT EXISTS ix_marketing_calendar_items_channel ON marketing_calendar_items(channel);
CREATE INDEX IF NOT EXISTS ix_marketing_calendar_items_content_type ON marketing_calendar_items(content_type);
CREATE INDEX IF NOT EXISTS ix_marketing_calendar_items_scheduled_for ON marketing_calendar_items(scheduled_for);
CREATE INDEX IF NOT EXISTS ix_marketing_calendar_items_status ON marketing_calendar_items(status);

CREATE TABLE IF NOT EXISTS marketing_analytics (
    analytics_id VARCHAR(36) PRIMARY KEY,
    campaign_id VARCHAR(36) NOT NULL REFERENCES marketing_campaigns(campaign_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    channel VARCHAR NOT NULL,
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    leads INTEGER NOT NULL DEFAULT 0,
    spend INTEGER NOT NULL DEFAULT 0,
    revenue INTEGER NOT NULL DEFAULT 0,
    captured_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_marketing_analytics_campaign_id ON marketing_analytics(campaign_id);
CREATE INDEX IF NOT EXISTS ix_marketing_analytics_business_id ON marketing_analytics(business_id);
CREATE INDEX IF NOT EXISTS ix_marketing_analytics_channel ON marketing_analytics(channel);
CREATE INDEX IF NOT EXISTS ix_marketing_analytics_captured_at ON marketing_analytics(captured_at);

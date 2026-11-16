CREATE TABLE IF NOT EXISTS meta_ad_approvals (
    approval_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    action VARCHAR NOT NULL,
    campaign_name VARCHAR NOT NULL,
    budget INTEGER NOT NULL DEFAULT 0,
    audience JSONB NOT NULL DEFAULT '{}'::jsonb,
    creative JSONB NOT NULL DEFAULT '{}'::jsonb,
    expected_goal TEXT NOT NULL DEFAULT '',
    status VARCHAR NOT NULL DEFAULT 'pending',
    approval_required INTEGER NOT NULL DEFAULT 1,
    external_write_blocked INTEGER NOT NULL DEFAULT 1,
    external_write_attempted INTEGER NOT NULL DEFAULT 0,
    requested_by VARCHAR NOT NULL DEFAULT 'Marketing Executive',
    decided_by VARCHAR,
    decision_comment TEXT,
    audit_event_id VARCHAR(36),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_business_id ON meta_ad_approvals (business_id);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_action ON meta_ad_approvals (action);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_campaign_name ON meta_ad_approvals (campaign_name);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_status ON meta_ad_approvals (status);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_approval_required ON meta_ad_approvals (approval_required);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_external_write_blocked ON meta_ad_approvals (external_write_blocked);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_external_write_attempted ON meta_ad_approvals (external_write_attempted);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_requested_by ON meta_ad_approvals (requested_by);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_decided_by ON meta_ad_approvals (decided_by);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_audit_event_id ON meta_ad_approvals (audit_event_id);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_created_at ON meta_ad_approvals (created_at);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_updated_at ON meta_ad_approvals (updated_at);
CREATE INDEX IF NOT EXISTS ix_meta_ad_approvals_decided_at ON meta_ad_approvals (decided_at);

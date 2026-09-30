CREATE TABLE IF NOT EXISTS sales_post_demo_drafts (
    draft_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    booking_id VARCHAR(36) NOT NULL REFERENCES sales_demo_bookings(booking_id),
    lead_id VARCHAR(36) NOT NULL REFERENCES sales_leads(lead_id),
    deal_id VARCHAR(36) REFERENCES sales_deals(deal_id),
    company_id VARCHAR(36) NOT NULL REFERENCES sales_companies(company_id),
    contact_id VARCHAR(36) REFERENCES sales_contacts(contact_id),
    demo_summary TEXT NOT NULL,
    pain_points JSONB NOT NULL DEFAULT '[]'::jsonb,
    dp360_fit TEXT NOT NULL,
    next_action TEXT NOT NULL,
    commercial_cta TEXT NOT NULL,
    follow_up_email TEXT NOT NULL,
    proposal_draft TEXT NOT NULL,
    approval_status VARCHAR NOT NULL DEFAULT 'pending',
    external_send_blocked INTEGER NOT NULL DEFAULT 1,
    hubspot_event_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    reasoning_provider VARCHAR NOT NULL DEFAULT 'deterministic',
    reasoning_model VARCHAR NOT NULL DEFAULT 'deterministic',
    created_by VARCHAR NOT NULL DEFAULT 'Sales Executive',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_business_id ON sales_post_demo_drafts (business_id);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_booking_id ON sales_post_demo_drafts (booking_id);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_lead_id ON sales_post_demo_drafts (lead_id);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_deal_id ON sales_post_demo_drafts (deal_id);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_company_id ON sales_post_demo_drafts (company_id);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_contact_id ON sales_post_demo_drafts (contact_id);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_approval_status ON sales_post_demo_drafts (approval_status);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_external_send_blocked ON sales_post_demo_drafts (external_send_blocked);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_reasoning_provider ON sales_post_demo_drafts (reasoning_provider);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_reasoning_model ON sales_post_demo_drafts (reasoning_model);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_created_by ON sales_post_demo_drafts (created_by);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_created_at ON sales_post_demo_drafts (created_at);
CREATE INDEX IF NOT EXISTS ix_sales_post_demo_drafts_updated_at ON sales_post_demo_drafts (updated_at);

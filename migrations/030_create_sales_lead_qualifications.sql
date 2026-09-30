CREATE TABLE IF NOT EXISTS sales_lead_qualifications (
    qualification_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    lead_id VARCHAR(36) NOT NULL UNIQUE REFERENCES sales_leads(lead_id),
    business_type VARCHAR NOT NULL,
    location VARCHAR NOT NULL,
    stage VARCHAR NOT NULL,
    budget INTEGER NOT NULL DEFAULT 0,
    timeline VARCHAR NOT NULL,
    requirement TEXT NOT NULL,
    source VARCHAR NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    qualification_status VARCHAR NOT NULL DEFAULT 'new',
    missing_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    scoring_factors JSONB NOT NULL DEFAULT '{}'::jsonb,
    recommendation TEXT NOT NULL DEFAULT '',
    hubspot_event_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_sales_lead_qualifications_business_id ON sales_lead_qualifications (business_id);
CREATE INDEX IF NOT EXISTS ix_sales_lead_qualifications_lead_id ON sales_lead_qualifications (lead_id);
CREATE INDEX IF NOT EXISTS ix_sales_lead_qualifications_business_type ON sales_lead_qualifications (business_type);
CREATE INDEX IF NOT EXISTS ix_sales_lead_qualifications_location ON sales_lead_qualifications (location);
CREATE INDEX IF NOT EXISTS ix_sales_lead_qualifications_stage ON sales_lead_qualifications (stage);
CREATE INDEX IF NOT EXISTS ix_sales_lead_qualifications_score ON sales_lead_qualifications (score);
CREATE INDEX IF NOT EXISTS ix_sales_lead_qualifications_qualification_status ON sales_lead_qualifications (qualification_status);

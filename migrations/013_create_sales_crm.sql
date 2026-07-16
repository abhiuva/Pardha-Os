CREATE TABLE IF NOT EXISTS sales_companies (
    company_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    name VARCHAR NOT NULL,
    industry VARCHAR NOT NULL,
    website VARCHAR,
    company_size VARCHAR,
    country VARCHAR,
    linkedin_url VARCHAR,
    business_summary TEXT NOT NULL DEFAULT '',
    ai_opportunity_score INTEGER NOT NULL DEFAULT 0,
    sales_priority VARCHAR NOT NULL DEFAULT 'medium',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_sales_companies_business_id ON sales_companies(business_id);
CREATE INDEX IF NOT EXISTS ix_sales_companies_name ON sales_companies(name);
CREATE INDEX IF NOT EXISTS ix_sales_companies_industry ON sales_companies(industry);
CREATE INDEX IF NOT EXISTS ix_sales_companies_sales_priority ON sales_companies(sales_priority);

CREATE TABLE IF NOT EXISTS sales_contacts (
    contact_id VARCHAR(36) PRIMARY KEY,
    company_id VARCHAR(36) NOT NULL REFERENCES sales_companies(company_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    name VARCHAR NOT NULL,
    role VARCHAR,
    email VARCHAR,
    linkedin_url VARCHAR,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_sales_contacts_company_id ON sales_contacts(company_id);
CREATE INDEX IF NOT EXISTS ix_sales_contacts_business_id ON sales_contacts(business_id);

CREATE TABLE IF NOT EXISTS sales_leads (
    lead_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    company_id VARCHAR(36) NOT NULL REFERENCES sales_companies(company_id),
    contact_id VARCHAR(36) REFERENCES sales_contacts(contact_id),
    title VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'new',
    pipeline_stage VARCHAR NOT NULL DEFAULT 'prospect',
    ai_opportunity_score INTEGER NOT NULL DEFAULT 0,
    sales_priority VARCHAR NOT NULL DEFAULT 'medium',
    outreach_email TEXT,
    outreach_linkedin TEXT,
    next_action VARCHAR,
    demo_requested_at TIMESTAMPTZ,
    demo_scheduled_at TIMESTAMPTZ,
    demo_completed_at TIMESTAMPTZ,
    proposal_sent_at TIMESTAMPTZ,
    negotiation_started_at TIMESTAMPTZ,
    won_at TIMESTAMPTZ,
    lost_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_sales_lead_status CHECK (
        status IN ('new', 'contacted', 'demo_requested', 'demo_scheduled', 'demo_completed', 'proposal_sent', 'negotiation', 'won', 'lost')
    )
);

CREATE INDEX IF NOT EXISTS ix_sales_leads_business_id ON sales_leads(business_id);
CREATE INDEX IF NOT EXISTS ix_sales_leads_company_id ON sales_leads(company_id);
CREATE INDEX IF NOT EXISTS ix_sales_leads_contact_id ON sales_leads(contact_id);
CREATE INDEX IF NOT EXISTS ix_sales_leads_status ON sales_leads(status);
CREATE INDEX IF NOT EXISTS ix_sales_leads_pipeline_stage ON sales_leads(pipeline_stage);
CREATE INDEX IF NOT EXISTS ix_sales_leads_sales_priority ON sales_leads(sales_priority);
CREATE INDEX IF NOT EXISTS ix_sales_leads_created_at ON sales_leads(created_at);

CREATE TABLE IF NOT EXISTS sales_deals (
    deal_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    lead_id VARCHAR(36) NOT NULL REFERENCES sales_leads(lead_id),
    pipeline_stage VARCHAR NOT NULL DEFAULT 'prospecting',
    amount INTEGER NOT NULL DEFAULT 0,
    probability INTEGER NOT NULL DEFAULT 0,
    expected_close_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_sales_deals_business_id ON sales_deals(business_id);
CREATE INDEX IF NOT EXISTS ix_sales_deals_lead_id ON sales_deals(lead_id);
CREATE INDEX IF NOT EXISTS ix_sales_deals_pipeline_stage ON sales_deals(pipeline_stage);
CREATE INDEX IF NOT EXISTS ix_sales_deals_created_at ON sales_deals(created_at);

CREATE TABLE IF NOT EXISTS sales_activities (
    activity_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    lead_id VARCHAR(36) NOT NULL REFERENCES sales_leads(lead_id),
    activity_type VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_sales_activities_business_id ON sales_activities(business_id);
CREATE INDEX IF NOT EXISTS ix_sales_activities_lead_id ON sales_activities(lead_id);
CREATE INDEX IF NOT EXISTS ix_sales_activities_activity_type ON sales_activities(activity_type);
CREATE INDEX IF NOT EXISTS ix_sales_activities_created_at ON sales_activities(created_at);

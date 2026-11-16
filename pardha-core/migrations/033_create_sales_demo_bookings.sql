CREATE TABLE IF NOT EXISTS sales_demo_bookings (
    booking_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    lead_id VARCHAR(36) NOT NULL REFERENCES sales_leads(lead_id),
    company_id VARCHAR(36) NOT NULL REFERENCES sales_companies(company_id),
    contact_id VARCHAR(36) REFERENCES sales_contacts(contact_id),
    status VARCHAR NOT NULL DEFAULT 'requested',
    requested_slot TIMESTAMPTZ,
    scheduled_at TIMESTAMPTZ,
    meeting_url VARCHAR,
    owner VARCHAR NOT NULL DEFAULT 'Founder',
    calendar_mode VARCHAR NOT NULL DEFAULT 'mock',
    hubspot_event_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_sales_demo_bookings_business_id ON sales_demo_bookings (business_id);
CREATE INDEX IF NOT EXISTS ix_sales_demo_bookings_lead_id ON sales_demo_bookings (lead_id);
CREATE INDEX IF NOT EXISTS ix_sales_demo_bookings_company_id ON sales_demo_bookings (company_id);
CREATE INDEX IF NOT EXISTS ix_sales_demo_bookings_contact_id ON sales_demo_bookings (contact_id);
CREATE INDEX IF NOT EXISTS ix_sales_demo_bookings_status ON sales_demo_bookings (status);
CREATE INDEX IF NOT EXISTS ix_sales_demo_bookings_requested_slot ON sales_demo_bookings (requested_slot);
CREATE INDEX IF NOT EXISTS ix_sales_demo_bookings_scheduled_at ON sales_demo_bookings (scheduled_at);
CREATE INDEX IF NOT EXISTS ix_sales_demo_bookings_owner ON sales_demo_bookings (owner);
CREATE INDEX IF NOT EXISTS ix_sales_demo_bookings_calendar_mode ON sales_demo_bookings (calendar_mode);
CREATE INDEX IF NOT EXISTS ix_sales_demo_bookings_created_at ON sales_demo_bookings (created_at);
CREATE INDEX IF NOT EXISTS ix_sales_demo_bookings_updated_at ON sales_demo_bookings (updated_at);

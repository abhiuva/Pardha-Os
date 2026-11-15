CREATE TABLE IF NOT EXISTS customer_profiles (
    profile_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL UNIQUE REFERENCES businesses(business_id),
    company_name VARCHAR NOT NULL,
    business_type VARCHAR NOT NULL,
    lifecycle_stage VARCHAR NOT NULL DEFAULT 'onboarding',
    health_score INTEGER NOT NULL DEFAULT 75,
    revenue_goal INTEGER NOT NULL DEFAULT 0,
    success_plan JSONB NOT NULL DEFAULT '{}'::jsonb,
    onboarding_status JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_customer_profiles_business_id ON customer_profiles(business_id);
CREATE INDEX IF NOT EXISTS ix_customer_profiles_company_name ON customer_profiles(company_name);
CREATE INDEX IF NOT EXISTS ix_customer_profiles_business_type ON customer_profiles(business_type);
CREATE INDEX IF NOT EXISTS ix_customer_profiles_lifecycle_stage ON customer_profiles(lifecycle_stage);

CREATE TABLE IF NOT EXISTS meeting_notes (
    meeting_note_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    title VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    attendees JSONB NOT NULL DEFAULT '[]'::jsonb,
    action_items JSONB NOT NULL DEFAULT '[]'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_meeting_notes_business_id ON meeting_notes(business_id);
CREATE INDEX IF NOT EXISTS ix_meeting_notes_title ON meeting_notes(title);
CREATE INDEX IF NOT EXISTS ix_meeting_notes_occurred_at ON meeting_notes(occurred_at);
CREATE INDEX IF NOT EXISTS ix_meeting_notes_created_at ON meeting_notes(created_at);

CREATE TABLE IF NOT EXISTS customer_timeline_entries (
    timeline_entry_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    event_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    detail TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_customer_timeline_entries_business_id ON customer_timeline_entries(business_id);
CREATE INDEX IF NOT EXISTS ix_customer_timeline_entries_event_type ON customer_timeline_entries(event_type);
CREATE INDEX IF NOT EXISTS ix_customer_timeline_entries_occurred_at ON customer_timeline_entries(occurred_at);
CREATE INDEX IF NOT EXISTS ix_customer_timeline_entries_created_at ON customer_timeline_entries(created_at);

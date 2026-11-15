CREATE TABLE IF NOT EXISTS knowledge (
    knowledge_id UUID PRIMARY KEY,
    business_name TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_uri TEXT,
    document_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding_model TEXT,
    embedding_reference TEXT,
    CONSTRAINT ck_knowledge_category CHECK (
        category IN (
            'company',
            'product',
            'project',
            'roadmap',
            'prd',
            'sop',
            'meeting_notes',
            'customer_feedback'
        )
    )
);

CREATE INDEX IF NOT EXISTS ix_knowledge_business_name ON knowledge (business_name);
CREATE INDEX IF NOT EXISTS ix_knowledge_category ON knowledge (category);
CREATE INDEX IF NOT EXISTS ix_knowledge_created_at ON knowledge (created_at);
CREATE INDEX IF NOT EXISTS ix_knowledge_business_category ON knowledge (business_name, category);

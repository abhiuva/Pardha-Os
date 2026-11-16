CREATE TABLE IF NOT EXISTS knowledge_imports (
    import_id VARCHAR(36) PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    business_name TEXT NOT NULL,
    knowledge_id UUID NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_knowledge_imports_file_hash ON knowledge_imports (file_hash);
CREATE INDEX IF NOT EXISTS ix_knowledge_imports_business_name ON knowledge_imports (business_name);
CREATE INDEX IF NOT EXISTS ix_knowledge_imports_knowledge_id ON knowledge_imports (knowledge_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_imports_imported_at ON knowledge_imports (imported_at);

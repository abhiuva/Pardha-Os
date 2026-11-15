CREATE TABLE IF NOT EXISTS projects (
    project_id VARCHAR(36) PRIMARY KEY,
    project_name TEXT NOT NULL,
    project_path TEXT NOT NULL UNIQUE,
    language TEXT NOT NULL,
    framework TEXT NOT NULL,
    repository_summary TEXT NOT NULL,
    analysis JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_scanned TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_projects_project_name ON projects (project_name);
CREATE INDEX IF NOT EXISTS ix_projects_last_scanned ON projects (last_scanned);

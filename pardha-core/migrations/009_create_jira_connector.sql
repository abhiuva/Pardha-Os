CREATE TABLE IF NOT EXISTS jira_projects (
    jira_project_id VARCHAR(36) PRIMARY KEY,
    project_key VARCHAR NOT NULL UNIQUE,
    jira_url TEXT NOT NULL,
    name VARCHAR NOT NULL,
    email VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'configured',
    last_synced_at TIMESTAMP WITH TIME ZONE,
    metadata JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_jira_projects_project_key ON jira_projects (project_key);
CREATE INDEX IF NOT EXISTS ix_jira_projects_status ON jira_projects (status);
CREATE INDEX IF NOT EXISTS ix_jira_projects_last_synced_at ON jira_projects (last_synced_at);

CREATE TABLE IF NOT EXISTS jira_issues (
    jira_issue_id VARCHAR(36) PRIMARY KEY,
    jira_issue_key VARCHAR NOT NULL UNIQUE,
    project_key VARCHAR NOT NULL,
    issue_type VARCHAR NOT NULL,
    source_type VARCHAR NOT NULL,
    source_id VARCHAR NOT NULL,
    parent_jira_issue_key VARCHAR,
    summary VARCHAR NOT NULL,
    description TEXT,
    status VARCHAR NOT NULL DEFAULT 'created',
    url TEXT,
    raw JSON NOT NULL DEFAULT '{}',
    synced_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT ck_jira_issue_type CHECK (issue_type IN ('epic', 'story', 'technical_story')),
    CONSTRAINT ck_jira_source_type CHECK (source_type IN ('objective', 'task', 'engineering_task'))
);

CREATE INDEX IF NOT EXISTS ix_jira_issues_jira_issue_key ON jira_issues (jira_issue_key);
CREATE INDEX IF NOT EXISTS ix_jira_issues_project_key ON jira_issues (project_key);
CREATE INDEX IF NOT EXISTS ix_jira_issues_issue_type ON jira_issues (issue_type);
CREATE INDEX IF NOT EXISTS ix_jira_issues_source_type ON jira_issues (source_type);
CREATE INDEX IF NOT EXISTS ix_jira_issues_source_id ON jira_issues (source_id);
CREATE INDEX IF NOT EXISTS ix_jira_issues_parent_jira_issue_key ON jira_issues (parent_jira_issue_key);
CREATE INDEX IF NOT EXISTS ix_jira_issues_synced_at ON jira_issues (synced_at);

CREATE TABLE IF NOT EXISTS jira_sync_history (
    jira_sync_id VARCHAR(36) PRIMARY KEY,
    project_key VARCHAR NOT NULL,
    objective_id VARCHAR(36),
    status VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    summary TEXT NOT NULL,
    issue_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    payload JSON NOT NULL DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_jira_sync_history_project_key ON jira_sync_history (project_key);
CREATE INDEX IF NOT EXISTS ix_jira_sync_history_objective_id ON jira_sync_history (objective_id);
CREATE INDEX IF NOT EXISTS ix_jira_sync_history_status ON jira_sync_history (status);
CREATE INDEX IF NOT EXISTS ix_jira_sync_history_action ON jira_sync_history (action);
CREATE INDEX IF NOT EXISTS ix_jira_sync_history_started_at ON jira_sync_history (started_at);
CREATE INDEX IF NOT EXISTS ix_jira_sync_history_completed_at ON jira_sync_history (completed_at);

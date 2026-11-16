CREATE TABLE IF NOT EXISTS software_factory_requirements (
    requirement_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    title VARCHAR NOT NULL,
    request TEXT NOT NULL,
    requester VARCHAR NOT NULL DEFAULT 'Founder',
    methodology VARCHAR NOT NULL DEFAULT 'scrum',
    stack JSON NOT NULL DEFAULT '[]',
    status VARCHAR NOT NULL DEFAULT 'waiting_approval',
    current_stage VARCHAR NOT NULL DEFAULT 'discovery',
    discovery JSON NOT NULL DEFAULT '{}',
    orchestration_graph JSON NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_software_factory_requirements_business_id ON software_factory_requirements(business_id);
CREATE INDEX IF NOT EXISTS ix_software_factory_requirements_status ON software_factory_requirements(status);

CREATE TABLE IF NOT EXISTS software_factory_artifacts (
    artifact_id VARCHAR(36) PRIMARY KEY,
    requirement_id VARCHAR(36) NOT NULL REFERENCES software_factory_requirements(requirement_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    artifact_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR NOT NULL DEFAULT 'draft',
    content JSON NOT NULL DEFAULT '{}',
    editable INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_software_factory_artifacts_requirement_id ON software_factory_artifacts(requirement_id);
CREATE INDEX IF NOT EXISTS ix_software_factory_artifacts_business_id ON software_factory_artifacts(business_id);
CREATE INDEX IF NOT EXISTS ix_software_factory_artifacts_artifact_type ON software_factory_artifacts(artifact_type);

CREATE TABLE IF NOT EXISTS software_factory_approvals (
    approval_id VARCHAR(36) PRIMARY KEY,
    requirement_id VARCHAR(36) NOT NULL REFERENCES software_factory_requirements(requirement_id),
    artifact_id VARCHAR(36) REFERENCES software_factory_artifacts(artifact_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    approval_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    risk_level VARCHAR NOT NULL DEFAULT 'medium',
    status VARCHAR NOT NULL DEFAULT 'pending',
    requested_by VARCHAR NOT NULL DEFAULT 'Software Factory',
    decided_by VARCHAR,
    decision_comment TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_software_factory_approvals_requirement_id ON software_factory_approvals(requirement_id);
CREATE INDEX IF NOT EXISTS ix_software_factory_approvals_business_id ON software_factory_approvals(business_id);
CREATE INDEX IF NOT EXISTS ix_software_factory_approvals_status ON software_factory_approvals(status);
CREATE INDEX IF NOT EXISTS ix_software_factory_approvals_approval_type ON software_factory_approvals(approval_type);

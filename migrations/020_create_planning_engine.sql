CREATE TABLE IF NOT EXISTS planning_goals (
    goal_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    title VARCHAR NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    priority VARCHAR NOT NULL DEFAULT 'high',
    owner VARCHAR NOT NULL DEFAULT 'Founder',
    department VARCHAR NOT NULL DEFAULT 'Executive',
    target_date TIMESTAMPTZ,
    success_metrics JSONB NOT NULL DEFAULT '[]'::jsonb,
    current_status VARCHAR NOT NULL DEFAULT 'active',
    risk_level VARCHAR NOT NULL DEFAULT 'medium',
    progress INTEGER NOT NULL DEFAULT 0,
    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by VARCHAR NOT NULL DEFAULT 'Founder',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_plans (
    plan_id VARCHAR(36) PRIMARY KEY,
    goal_id VARCHAR(36) NOT NULL REFERENCES planning_goals(goal_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    title VARCHAR NOT NULL,
    request TEXT NOT NULL,
    plan_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'preview',
    risk_level VARCHAR NOT NULL DEFAULT 'medium',
    approval_required INTEGER NOT NULL DEFAULT 1,
    progress INTEGER NOT NULL DEFAULT 0,
    estimated_completion TIMESTAMPTZ,
    summary TEXT NOT NULL DEFAULT '',
    capability_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    graph JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by VARCHAR NOT NULL DEFAULT 'Founder',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_plan_nodes (
    node_id VARCHAR(36) PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL REFERENCES execution_plans(plan_id),
    goal_id VARCHAR(36) NOT NULL REFERENCES planning_goals(goal_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    node_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    capability_id VARCHAR(120) REFERENCES capabilities(capability_id),
    status VARCHAR NOT NULL DEFAULT 'queued',
    risk_level VARCHAR NOT NULL DEFAULT 'low',
    approval_required INTEGER NOT NULL DEFAULT 0,
    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb,
    parallel_group VARCHAR,
    critical_path INTEGER NOT NULL DEFAULT 0,
    estimated_runtime_ms INTEGER NOT NULL DEFAULT 0,
    output JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_approvals (
    approval_id VARCHAR(36) PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL REFERENCES execution_plans(plan_id),
    node_id VARCHAR(36) REFERENCES execution_plan_nodes(node_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    approval_type VARCHAR NOT NULL,
    risk_level VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    status VARCHAR NOT NULL DEFAULT 'pending',
    requested_by VARCHAR NOT NULL DEFAULT 'Planner',
    decided_by VARCHAR,
    decision_comment TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS plan_executions (
    execution_id VARCHAR(36) PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL REFERENCES execution_plans(plan_id),
    goal_id VARCHAR(36) NOT NULL REFERENCES planning_goals(goal_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    current_step VARCHAR NOT NULL DEFAULT '',
    current_capability VARCHAR(120),
    progress INTEGER NOT NULL DEFAULT 0,
    estimated_time_ms INTEGER NOT NULL DEFAULT 0,
    logs JSONB NOT NULL DEFAULT '[]'::jsonb,
    retry_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL DEFAULT 'queued',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS goal_kpis (
    kpi_id VARCHAR(36) PRIMARY KEY,
    goal_id VARCHAR(36) NOT NULL REFERENCES planning_goals(goal_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    name VARCHAR NOT NULL,
    target_value INTEGER NOT NULL DEFAULT 0,
    current_value INTEGER NOT NULL DEFAULT 0,
    unit VARCHAR NOT NULL DEFAULT 'count',
    status VARCHAR NOT NULL DEFAULT 'tracking',
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS planning_timeline_events (
    timeline_event_id VARCHAR(36) PRIMARY KEY,
    goal_id VARCHAR(36) NOT NULL REFERENCES planning_goals(goal_id),
    plan_id VARCHAR(36) REFERENCES execution_plans(plan_id),
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    event_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_planning_goals_business_id ON planning_goals(business_id);
CREATE INDEX IF NOT EXISTS ix_execution_plans_goal_id ON execution_plans(goal_id);
CREATE INDEX IF NOT EXISTS ix_execution_plans_business_id ON execution_plans(business_id);
CREATE INDEX IF NOT EXISTS ix_execution_plan_nodes_plan_id ON execution_plan_nodes(plan_id);
CREATE INDEX IF NOT EXISTS ix_plan_approvals_status ON plan_approvals(status);
CREATE INDEX IF NOT EXISTS ix_plan_executions_status ON plan_executions(status);
CREATE INDEX IF NOT EXISTS ix_goal_kpis_goal_id ON goal_kpis(goal_id);
CREATE INDEX IF NOT EXISTS ix_planning_timeline_events_goal_id ON planning_timeline_events(goal_id);

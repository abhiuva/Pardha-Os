CREATE TABLE IF NOT EXISTS mcp_server_capabilities (
    capability_id VARCHAR(36) PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL REFERENCES mcp_servers(mcp_server_id),
    name VARCHAR NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mcp_server_capabilities_server_id ON mcp_server_capabilities(server_id);
CREATE INDEX IF NOT EXISTS ix_mcp_server_capabilities_name ON mcp_server_capabilities(name);

CREATE TABLE IF NOT EXISTS mcp_server_health (
    health_id VARCHAR(36) PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL REFERENCES mcp_servers(mcp_server_id),
    status VARCHAR NOT NULL,
    latency_ms INTEGER,
    authentication_status VARCHAR NOT NULL,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    connected_tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    failure_count INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT '',
    checked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mcp_server_health_server_id ON mcp_server_health(server_id);
CREATE INDEX IF NOT EXISTS ix_mcp_server_health_status ON mcp_server_health(status);
CREATE INDEX IF NOT EXISTS ix_mcp_server_health_checked_at ON mcp_server_health(checked_at);

CREATE TABLE IF NOT EXISTS mcp_tools (
    tool_id VARCHAR(80) PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL REFERENCES mcp_servers(mcp_server_id),
    name VARCHAR NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    input_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mcp_tools_server_id ON mcp_tools(server_id);
CREATE INDEX IF NOT EXISTS ix_mcp_tools_name ON mcp_tools(name);
CREATE INDEX IF NOT EXISTS ix_mcp_tools_enabled ON mcp_tools(enabled);

CREATE TABLE IF NOT EXISTS mcp_connections (
    connection_id VARCHAR(36) PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL REFERENCES mcp_servers(mcp_server_id),
    auth_type VARCHAR NOT NULL,
    authentication_status VARCHAR NOT NULL,
    credentials JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    connected_at TIMESTAMPTZ,
    disconnected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mcp_connections_server_id ON mcp_connections(server_id);
CREATE INDEX IF NOT EXISTS ix_mcp_connections_auth_type ON mcp_connections(auth_type);
CREATE INDEX IF NOT EXISTS ix_mcp_connections_authentication_status ON mcp_connections(authentication_status);

CREATE TABLE IF NOT EXISTS mcp_permissions (
    permission_id VARCHAR(36) PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL REFERENCES mcp_servers(mcp_server_id),
    permission VARCHAR NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    granted INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mcp_permissions_server_id ON mcp_permissions(server_id);
CREATE INDEX IF NOT EXISTS ix_mcp_permissions_permission ON mcp_permissions(permission);
CREATE INDEX IF NOT EXISTS ix_mcp_permissions_granted ON mcp_permissions(granted);

CREATE TABLE IF NOT EXISTS mcp_execution_history (
    execution_id VARCHAR(36) PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL REFERENCES mcp_servers(mcp_server_id),
    tool VARCHAR NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR NOT NULL,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    output JSONB NOT NULL DEFAULT '{}'::jsonb,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mcp_execution_history_server_id ON mcp_execution_history(server_id);
CREATE INDEX IF NOT EXISTS ix_mcp_execution_history_tool ON mcp_execution_history(tool);
CREATE INDEX IF NOT EXISTS ix_mcp_execution_history_status ON mcp_execution_history(status);
CREATE INDEX IF NOT EXISTS ix_mcp_execution_history_created_at ON mcp_execution_history(created_at);

CREATE TABLE IF NOT EXISTS mcp_events (
    event_id VARCHAR(36) PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL REFERENCES mcp_servers(mcp_server_id),
    event_type VARCHAR NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mcp_events_server_id ON mcp_events(server_id);
CREATE INDEX IF NOT EXISTS ix_mcp_events_event_type ON mcp_events(event_type);
CREATE INDEX IF NOT EXISTS ix_mcp_events_created_at ON mcp_events(created_at);

CREATE TABLE IF NOT EXISTS mcp_logs (
    log_id VARCHAR(36) PRIMARY KEY,
    server_id VARCHAR(36) NOT NULL REFERENCES mcp_servers(mcp_server_id),
    level VARCHAR NOT NULL DEFAULT 'info',
    message TEXT NOT NULL,
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mcp_logs_server_id ON mcp_logs(server_id);
CREATE INDEX IF NOT EXISTS ix_mcp_logs_level ON mcp_logs(level);
CREATE INDEX IF NOT EXISTS ix_mcp_logs_created_at ON mcp_logs(created_at);

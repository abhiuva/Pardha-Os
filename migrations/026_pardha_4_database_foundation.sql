-- Pardha 4.0 database foundation.
-- Audit-driven, additive-only migration. No drops, no renames, no table recreation.

ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS id VARCHAR(36);
UPDATE conversation_sessions SET id = conversation_id WHERE id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_conversation_sessions_id ON conversation_sessions(id);
ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS founder_id VARCHAR(36) REFERENCES auth_users(user_id);
ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ;
ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'active';
ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS voice_enabled INTEGER NOT NULL DEFAULT 0;
ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS current_context JSONB NOT NULL DEFAULT '{}'::jsonb;
UPDATE conversation_sessions SET started_at = created_at WHERE started_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_founder_id ON conversation_sessions(founder_id);
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_status ON conversation_sessions(status);
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_voice_enabled ON conversation_sessions(voice_enabled);
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_started_at ON conversation_sessions(started_at);
CREATE INDEX IF NOT EXISTS ix_conversation_sessions_ended_at ON conversation_sessions(ended_at);

ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS message TEXT;
UPDATE conversation_messages SET message = content WHERE message IS NULL;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS planner VARCHAR;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS specialist VARCHAR;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS reasoning_model VARCHAR;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS tool_used VARCHAR;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS tokens INTEGER NOT NULL DEFAULT 0;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS latency INTEGER NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS ix_conversation_messages_planner ON conversation_messages(planner);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_specialist ON conversation_messages(specialist);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_reasoning_model ON conversation_messages(reasoning_model);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_tool_used ON conversation_messages(tool_used);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_tokens ON conversation_messages(tokens);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_latency ON conversation_messages(latency);

CREATE TABLE IF NOT EXISTS conversation_context (
    context_id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL UNIQUE REFERENCES conversation_sessions(conversation_id),
    business_id VARCHAR(36) REFERENCES businesses(business_id),
    active_module VARCHAR,
    active_business JSONB NOT NULL DEFAULT '{}'::jsonb,
    active_specialist VARCHAR,
    current_goal JSONB NOT NULL DEFAULT '{}'::jsonb,
    context_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_conversation_context_conversation_id ON conversation_context(conversation_id);
CREATE INDEX IF NOT EXISTS ix_conversation_context_business_id ON conversation_context(business_id);
CREATE INDEX IF NOT EXISTS ix_conversation_context_active_module ON conversation_context(active_module);
CREATE INDEX IF NOT EXISTS ix_conversation_context_active_specialist ON conversation_context(active_specialist);

CREATE TABLE IF NOT EXISTS conversation_intents (
    intent_id VARCHAR(36) PRIMARY KEY,
    intent_name VARCHAR NOT NULL UNIQUE,
    category VARCHAR NOT NULL,
    priority INTEGER NOT NULL DEFAULT 50,
    requires_business_context INTEGER NOT NULL DEFAULT 0,
    requires_reasoning INTEGER NOT NULL DEFAULT 0,
    requires_tool INTEGER NOT NULL DEFAULT 0,
    requires_memory INTEGER NOT NULL DEFAULT 0,
    allowed_specialists JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_conversation_intents_intent_name ON conversation_intents(intent_name);
CREATE INDEX IF NOT EXISTS ix_conversation_intents_category ON conversation_intents(category);
CREATE INDEX IF NOT EXISTS ix_conversation_intents_priority ON conversation_intents(priority);
CREATE INDEX IF NOT EXISTS ix_conversation_intents_status ON conversation_intents(status);

CREATE TABLE IF NOT EXISTS specialists (
    specialist_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    role VARCHAR NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    voice_enabled INTEGER NOT NULL DEFAULT 0,
    system_prompt TEXT NOT NULL DEFAULT '',
    memory_scope JSONB NOT NULL DEFAULT '[]'::jsonb,
    knowledge_scope JSONB NOT NULL DEFAULT '[]'::jsonb,
    capability_scope JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_specialists_name ON specialists(name);
CREATE INDEX IF NOT EXISTS ix_specialists_role ON specialists(role);
CREATE INDEX IF NOT EXISTS ix_specialists_status ON specialists(status);

CREATE TABLE IF NOT EXISTS reasoning_models (
    reasoning_model_id VARCHAR(36) PRIMARY KEY,
    provider VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    host VARCHAR,
    endpoint TEXT,
    priority INTEGER NOT NULL DEFAULT 50,
    max_context INTEGER NOT NULL DEFAULT 4096,
    cost VARCHAR NOT NULL DEFAULT 'local',
    latency INTEGER NOT NULL DEFAULT 0,
    health VARCHAR NOT NULL DEFAULT 'unknown',
    status VARCHAR NOT NULL DEFAULT 'available',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, model)
);
CREATE INDEX IF NOT EXISTS ix_reasoning_models_provider ON reasoning_models(provider);
CREATE INDEX IF NOT EXISTS ix_reasoning_models_model ON reasoning_models(model);
CREATE INDEX IF NOT EXISTS ix_reasoning_models_priority ON reasoning_models(priority);
CREATE INDEX IF NOT EXISTS ix_reasoning_models_status ON reasoning_models(status);

CREATE TABLE IF NOT EXISTS mcp_servers (
    mcp_server_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    endpoint TEXT NOT NULL,
    transport VARCHAR NOT NULL DEFAULT 'stdio',
    authentication JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR NOT NULL DEFAULT 'not_configured',
    health VARCHAR NOT NULL DEFAULT 'unknown',
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_seen TIMESTAMPTZ,
    supported_tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mcp_servers_name ON mcp_servers(name);
CREATE INDEX IF NOT EXISTS ix_mcp_servers_transport ON mcp_servers(transport);
CREATE INDEX IF NOT EXISTS ix_mcp_servers_status ON mcp_servers(status);
CREATE INDEX IF NOT EXISTS ix_mcp_servers_health ON mcp_servers(health);

CREATE TABLE IF NOT EXISTS capability_routes (
    route_id VARCHAR(36) PRIMARY KEY,
    intent VARCHAR NOT NULL,
    planner VARCHAR,
    specialist VARCHAR,
    tool VARCHAR,
    mcp_server VARCHAR,
    reasoning_model VARCHAR,
    priority INTEGER NOT NULL DEFAULT 50,
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_capability_routes_intent ON capability_routes(intent);
CREATE INDEX IF NOT EXISTS ix_capability_routes_specialist ON capability_routes(specialist);
CREATE INDEX IF NOT EXISTS ix_capability_routes_mcp_server ON capability_routes(mcp_server);
CREATE INDEX IF NOT EXISTS ix_capability_routes_reasoning_model ON capability_routes(reasoning_model);
CREATE INDEX IF NOT EXISTS ix_capability_routes_priority ON capability_routes(priority);

CREATE TABLE IF NOT EXISTS founder_memory (
    memory_id VARCHAR(36) PRIMARY KEY,
    founder_id VARCHAR(36) REFERENCES auth_users(user_id),
    owner VARCHAR NOT NULL DEFAULT 'Founder',
    memory_type VARCHAR NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence INTEGER NOT NULL DEFAULT 60,
    source_conversation_id VARCHAR(36) REFERENCES conversation_sessions(conversation_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_founder_memory_founder_id ON founder_memory(founder_id);
CREATE INDEX IF NOT EXISTS ix_founder_memory_owner ON founder_memory(owner);
CREATE INDEX IF NOT EXISTS ix_founder_memory_memory_type ON founder_memory(memory_type);
CREATE INDEX IF NOT EXISTS ix_founder_memory_source_conversation_id ON founder_memory(source_conversation_id);

CREATE TABLE IF NOT EXISTS business_memory (
    memory_id VARCHAR(36) PRIMARY KEY,
    business_id VARCHAR(36) NOT NULL REFERENCES businesses(business_id),
    memory_type VARCHAR NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence INTEGER NOT NULL DEFAULT 60,
    source_id VARCHAR(36),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_business_memory_business_id ON business_memory(business_id);
CREATE INDEX IF NOT EXISTS ix_business_memory_memory_type ON business_memory(memory_type);
CREATE INDEX IF NOT EXISTS ix_business_memory_source_id ON business_memory(source_id);

CREATE TABLE IF NOT EXISTS specialist_memory (
    memory_id VARCHAR(36) PRIMARY KEY,
    specialist_id VARCHAR(36) REFERENCES specialists(specialist_id),
    specialist VARCHAR NOT NULL,
    business_id VARCHAR(36) REFERENCES businesses(business_id),
    memory_type VARCHAR NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence INTEGER NOT NULL DEFAULT 60,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_specialist_memory_specialist_id ON specialist_memory(specialist_id);
CREATE INDEX IF NOT EXISTS ix_specialist_memory_specialist ON specialist_memory(specialist);
CREATE INDEX IF NOT EXISTS ix_specialist_memory_business_id ON specialist_memory(business_id);

CREATE TABLE IF NOT EXISTS conversation_memory (
    memory_id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversation_sessions(conversation_id),
    business_id VARCHAR(36) REFERENCES businesses(business_id),
    memory_type VARCHAR NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_conversation_memory_conversation_id ON conversation_memory(conversation_id);
CREATE INDEX IF NOT EXISTS ix_conversation_memory_business_id ON conversation_memory(business_id);
CREATE INDEX IF NOT EXISTS ix_conversation_memory_memory_type ON conversation_memory(memory_type);

CREATE TABLE IF NOT EXISTS learning_memory (
    memory_id VARCHAR(36) PRIMARY KEY,
    owner VARCHAR NOT NULL DEFAULT 'Founder',
    business_id VARCHAR(36) REFERENCES businesses(business_id),
    signal_type VARCHAR NOT NULL,
    signal_value JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence INTEGER NOT NULL DEFAULT 60,
    source_event_id VARCHAR(36),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_learning_memory_owner ON learning_memory(owner);
CREATE INDEX IF NOT EXISTS ix_learning_memory_business_id ON learning_memory(business_id);
CREATE INDEX IF NOT EXISTS ix_learning_memory_signal_type ON learning_memory(signal_type);
CREATE INDEX IF NOT EXISTS ix_learning_memory_source_event_id ON learning_memory(source_event_id);

CREATE TABLE IF NOT EXISTS learning_events (
    learning_event_id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) REFERENCES conversation_sessions(conversation_id),
    event VARCHAR NOT NULL,
    correction TEXT,
    accepted INTEGER NOT NULL DEFAULT 0,
    confidence INTEGER NOT NULL DEFAULT 60,
    feedback JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_learning_events_conversation_id ON learning_events(conversation_id);
CREATE INDEX IF NOT EXISTS ix_learning_events_event ON learning_events(event);
CREATE INDEX IF NOT EXISTS ix_learning_events_accepted ON learning_events(accepted);
CREATE INDEX IF NOT EXISTS ix_learning_events_created_at ON learning_events(created_at);

CREATE TABLE IF NOT EXISTS voice_sessions (
    voice_session_id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversation_sessions(conversation_id),
    microphone JSONB NOT NULL DEFAULT '{}'::jsonb,
    transcription JSONB NOT NULL DEFAULT '{}'::jsonb,
    reasoning_time INTEGER NOT NULL DEFAULT 0,
    speech_time INTEGER NOT NULL DEFAULT 0,
    duration INTEGER NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_voice_sessions_conversation_id ON voice_sessions(conversation_id);
CREATE INDEX IF NOT EXISTS ix_voice_sessions_status ON voice_sessions(status);
CREATE INDEX IF NOT EXISTS ix_voice_sessions_duration ON voice_sessions(duration);

CREATE TABLE IF NOT EXISTS execution_trace (
    trace_id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) REFERENCES conversation_sessions(conversation_id),
    planner VARCHAR,
    specialist VARCHAR,
    tool VARCHAR,
    duration INTEGER NOT NULL DEFAULT 0,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR NOT NULL DEFAULT 'recorded',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_execution_trace_conversation_id ON execution_trace(conversation_id);
CREATE INDEX IF NOT EXISTS ix_execution_trace_planner ON execution_trace(planner);
CREATE INDEX IF NOT EXISTS ix_execution_trace_specialist ON execution_trace(specialist);
CREATE INDEX IF NOT EXISTS ix_execution_trace_tool ON execution_trace(tool);
CREATE INDEX IF NOT EXISTS ix_execution_trace_status ON execution_trace(status);

INSERT INTO conversation_intents (intent_id, intent_name, category, priority, requires_business_context, requires_reasoning, requires_tool, requires_memory, allowed_specialists)
VALUES
('intent-general', 'General', 'General Conversation', 10, 0, 0, 0, 0, '[]'::jsonb),
('intent-weather', 'Weather', 'Weather', 20, 0, 0, 1, 0, '[]'::jsonb),
('intent-knowledge', 'Knowledge', 'Knowledge', 70, 1, 0, 1, 1, '["Knowledge"]'::jsonb),
('intent-business', 'Business', 'Business', 80, 1, 1, 1, 1, '["CEO", "Operations", "Finance"]'::jsonb),
('intent-marketing', 'Marketing', 'Marketing', 75, 1, 1, 1, 1, '["Marketing"]'::jsonb),
('intent-engineering', 'Engineering', 'Engineering', 75, 1, 1, 1, 1, '["CTO", "Engineering", "QA"]'::jsonb),
('intent-finance', 'Finance', 'Finance', 70, 1, 1, 1, 1, '["Finance"]'::jsonb),
('intent-founder', 'Founder', 'Founder', 85, 0, 0, 0, 1, '[]'::jsonb),
('intent-personal', 'Personal', 'Personal', 35, 0, 0, 0, 1, '[]'::jsonb),
('intent-system', 'System', 'System', 65, 0, 0, 1, 0, '["Operations"]'::jsonb),
('intent-coding', 'Coding', 'Coding', 55, 0, 1, 0, 0, '["Engineering"]'::jsonb)
ON CONFLICT (intent_name) DO NOTHING;

INSERT INTO specialists (specialist_id, name, role, description, voice_enabled, system_prompt, memory_scope, knowledge_scope, capability_scope, status)
VALUES
('specialist-ceo', 'CEO', 'Executive specialist', 'Hidden executive strategy specialist orchestrated by Pardha.', 0, '', '["business_memory", "learning_memory"]'::jsonb, '["business"]'::jsonb, '["ceo.daily_brief"]'::jsonb, 'active'),
('specialist-cto', 'CTO', 'Engineering specialist', 'Hidden technical architecture specialist orchestrated by Pardha.', 0, '', '["specialist_memory", "business_memory"]'::jsonb, '["engineering"]'::jsonb, '["cto.technical_brief", "projects.catalog"]'::jsonb, 'active'),
('specialist-pm', 'PM', 'Product specialist', 'Hidden product planning specialist orchestrated by Pardha.', 0, '', '["specialist_memory", "business_memory"]'::jsonb, '["product"]'::jsonb, '["pm.product_brief"]'::jsonb, 'active'),
('specialist-marketing', 'Marketing', 'Marketing specialist', 'Hidden marketing operating specialist orchestrated by Pardha.', 0, '', '["specialist_memory", "business_memory"]'::jsonb, '["marketing"]'::jsonb, '["marketing.summary"]'::jsonb, 'active'),
('specialist-sales', 'Sales', 'Sales specialist', 'Hidden sales operating specialist orchestrated by Pardha.', 0, '', '["specialist_memory", "business_memory"]'::jsonb, '["sales"]'::jsonb, '["sales.summary"]'::jsonb, 'active'),
('specialist-finance', 'Finance', 'Finance specialist', 'Hidden finance specialist reserved for Pardha orchestration.', 0, '', '["specialist_memory", "business_memory"]'::jsonb, '["finance"]'::jsonb, '[]'::jsonb, 'active'),
('specialist-knowledge', 'Knowledge', 'Knowledge specialist', 'Hidden knowledge retrieval specialist orchestrated by Pardha.', 0, '', '["business_memory", "conversation_memory"]'::jsonb, '["knowledge"]'::jsonb, '["knowledge.search"]'::jsonb, 'active'),
('specialist-qa', 'QA', 'Quality specialist', 'Hidden validation specialist orchestrated by Pardha.', 0, '', '["specialist_memory"]'::jsonb, '["quality"]'::jsonb, '["qa.validation"]'::jsonb, 'active'),
('specialist-operations', 'Operations', 'Operations specialist', 'Hidden operations specialist orchestrated by Pardha.', 0, '', '["business_memory", "learning_memory"]'::jsonb, '["operations"]'::jsonb, '["diagnostics.system_health"]'::jsonb, 'active')
ON CONFLICT (name) DO NOTHING;

INSERT INTO reasoning_models (reasoning_model_id, provider, model, host, endpoint, priority, max_context, cost, latency, health, status)
VALUES
('reasoning-ollama-qwen', 'Ollama', 'qwen3:8b', 'localhost', 'http://127.0.0.1:11434', 90, 4096, 'local', 0, 'unknown', 'available'),
('reasoning-ollama-llama', 'Ollama', 'llama3.2:3b', 'localhost', 'http://127.0.0.1:11434', 80, 4096, 'local', 0, 'unknown', 'available'),
('reasoning-openai-future', 'OpenAI', 'future', NULL, NULL, 40, 0, 'external', 0, 'not_configured', 'future'),
('reasoning-claude-future', 'Claude', 'future', NULL, NULL, 40, 0, 'external', 0, 'not_configured', 'future'),
('reasoning-gemini-future', 'Gemini', 'future', NULL, NULL, 40, 0, 'external', 0, 'not_configured', 'future')
ON CONFLICT (provider, model) DO NOTHING;

INSERT INTO mcp_servers (mcp_server_id, name, endpoint, transport, authentication, status, health, capabilities, supported_tools)
VALUES
('mcp-local-runtime', 'Local MCP Runtime', 'local://mcp-runtime', 'stdio', '{}'::jsonb, 'not_configured', 'unknown', '[]'::jsonb, '[]'::jsonb)
ON CONFLICT (name) DO NOTHING;

INSERT INTO capability_routes (route_id, intent, planner, specialist, tool, mcp_server, reasoning_model, priority)
VALUES
('route-business', 'Business', 'executive_planner', 'CEO', NULL, NULL, 'qwen3:8b', 80),
('route-marketing', 'Marketing', 'executive_planner', 'Marketing', NULL, NULL, 'qwen3:8b', 75),
('route-engineering', 'Engineering', 'executive_planner', 'CTO', NULL, NULL, 'qwen3:8b', 75),
('route-knowledge', 'Knowledge', NULL, 'Knowledge', 'knowledge.search', NULL, NULL, 70),
('route-system', 'System', NULL, 'Operations', 'diagnostics.system_health', 'Local MCP Runtime', NULL, 65)
ON CONFLICT (route_id) DO NOTHING;

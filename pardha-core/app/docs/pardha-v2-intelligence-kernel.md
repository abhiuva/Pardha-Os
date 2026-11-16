# Pardha v2.0 Sprint 1: Capability Registry and Intelligence Kernel

## Mission

Sprint 1 introduces the Intelligence Kernel foundation. It does not implement conversations, voice, chat, or new planning workflows.

The kernel discovers capabilities dynamically from the registry, ranks candidates, and executes the selected registered capability through its adapter. New future capabilities can register without modifying kernel selection logic.

## Architecture Diagram

```text
Founder / Developer Request
        |
        v
Intelligence Kernel
        |
        v
Capability Registry
        |
        v
Capability Selection
        |
        v
Execution Adapter
        |
        v
Response + Execution History
```

## Registry Diagram

```text
capabilities
  capability_id
  name
  version
  description
  supported_intents
  business_domains
  required_inputs
  outputs
  dependencies
  permissions
  health
  supports_hitl
  supports_streaming
  supports_learning
  priority
  estimated_runtime_ms
  registration_method
  current_status
  planner_interface
  execution_adapter
  execution_count
  last_executed_at

capability_executions
  execution_id
  capability_id
  business_id
  intent
  input_payload
  output_payload
  status
  confidence
  runtime_ms
  error
```

## Capability Graph

`GET /capabilities/graph` returns graph nodes for capabilities and dependency nodes for backing systems such as:

- agents
- events
- memories
- knowledge
- objectives
- tasks
- projects
- sales
- marketing
- Jira
- connectors
- diagnostics

Edges are emitted as:

```json
{
  "source": "cto.technical_brief",
  "target": "dependency:projects",
  "type": "depends_on"
}
```

## APIs

Capability Registry:

- `GET /capabilities`
- `GET /capabilities/{id}`
- `GET /capabilities/search`
- `GET /capabilities/health`
- `GET /capabilities/graph`
- `GET /capabilities/validation`
- `POST /capabilities/register`
- `POST /capabilities/unregister`

Intelligence Kernel:

- `POST /kernel/resolve`
- `POST /kernel/execute`

## Selection Criteria

The kernel ranks candidates using:

- Exact intent match
- Supported intent token match
- Semantic token match against name, description, domains, and outputs
- Business domain match
- Capability priority
- Health
- Current status
- Estimated runtime cost
- Required input coverage

## Registered Existing Capabilities

- `ceo.daily_brief`
- `pm.daily_brief`
- `cto.technical_brief`
- `knowledge.search`
- `knowledge.ingest`
- `sales.summary`
- `marketing.summary`
- `projects.catalog`
- `tasks.catalog`
- `jira.status`
- `diagnostics.system_health`
- `email.connector_health`
- `calendar.connector_health`
- `whatsapp.connector_health`
- `qa.validation`
- `vscode.workspace_status`

## Developer Registration Example

```json
{
  "capability_id": "future.plugin.demo",
  "name": "Future Plugin Demo",
  "version": "0.1.0",
  "description": "External plugin capability.",
  "supported_intents": ["future_plugin_test"],
  "business_domains": ["all"],
  "required_inputs": ["business_id"],
  "outputs": ["demo_result"],
  "dependencies": ["external_plugin"],
  "permissions": ["read:business"],
  "health": "healthy",
  "supports_hitl": true,
  "supports_streaming": false,
  "supports_learning": false,
  "priority": 99,
  "estimated_runtime_ms": 25,
  "registration_method": "manual",
  "current_status": "registered",
  "planner_interface": {
    "input_schema": "business_id",
    "output_schema": "demo_result"
  }
}
```

## Validation Report

Commands:

```bash
rm -f test_capability_registry.db
env PARDHA_ADMIN_EMAIL=founder@pardha.local PARDHA_ADMIN_PASSWORD='test-password' ./venv/bin/python -m unittest tests.test_capability_registry

rm -f /private/tmp/pardha_v2_full_test.db test_v1_release.db test_chief_of_staff.db test_capability_registry.db
env DATABASE_URL=sqlite:////private/tmp/pardha_v2_full_test.db PARDHA_ADMIN_EMAIL=founder@pardha.local ./venv/bin/python -m unittest discover tests

cd dashboard
npm run build
```

Results:

- Capability registry tests: 5 passed
- Full backend regression: 85 passed
- Dashboard build: passed

## Known Limitations

- Existing legacy routes remain for backward compatibility. The v2 kernel selection path does not depend on hardcoded direct agent routes.
- Execution adapters for existing internal capabilities are local Python adapters. Future external plugin execution should provide a stable remote adapter contract.
- `knowledge.ingest` is registered for discovery but uploads still use the existing multipart `/knowledge/upload` route.
- This sprint does not add conversational memory, voice, chat, or new planning logic.
- Some connector capabilities report `degraded` until real customer credentials are configured.

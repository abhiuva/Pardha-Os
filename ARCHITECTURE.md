# Pardha MCP Runtime Architecture

The MCP Runtime Platform is part of Pardha Core.

## Layers

1. Conversation Runtime
2. Planner
3. Capability Registry
4. MCP Runtime
5. Server Registry
6. Execution Engine
7. MCP Servers

## Persistence

The runtime normalizes provider state into:

- `mcp_servers`
- `mcp_server_capabilities`
- `mcp_server_health`
- `mcp_tools`
- `mcp_connections`
- `mcp_permissions`
- `mcp_execution_history`
- `mcp_events`
- `mcp_logs`

Existing integration tables are not duplicated. Provider-specific business data belongs in business modules; provider infrastructure belongs in MCP Runtime.

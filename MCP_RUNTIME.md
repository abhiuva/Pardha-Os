# MCP Runtime Platform

Pardha MCP Runtime is shared infrastructure for external systems. It owns server registration, authentication state, health checks, capability discovery, permissions, execution history, events, and logs.

Business modules must call MCP Runtime instead of implementing provider-specific authentication or execution.

## Core Flow

Pardha -> Conversation Runtime -> Planner -> Capability Registry -> MCP Runtime -> Server Registry -> Execution Engine -> MCP Server

## API

- `GET /mcp/servers`
- `GET /mcp/servers/{id}`
- `POST /mcp/connect`
- `POST /mcp/disconnect`
- `POST /mcp/execute`
- `GET /mcp/tools`
- `GET /mcp/health`
- `GET /mcp/events`
- `GET /mcp/logs`
- `GET /mcp/discovery`
- `GET /mcp/dashboard`

## Execution

All tool calls go through one entry point:

```json
{
  "server": "meta",
  "tool": "campaign.list",
  "params": {}
}
```

The execution engine records started, finished, and failed events, writes logs, and persists execution history.

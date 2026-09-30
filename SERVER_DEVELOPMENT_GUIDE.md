# MCP Server Development Guide

Every MCP server implements `MCPServerInterface`.

Required methods:

- `connect(credentials, metadata)`
- `disconnect()`
- `authenticate(credentials)`
- `health()`
- `discover_tools()`
- `execute(tool, params)`
- `logs(limit)`
- `permissions()`
- `metadata()`

To add a server:

1. Create `app/mcp/servers/<provider>.py`.
2. Implement `MCPServerInterface`.
3. Register the instance in `app/mcp/registry/service.py`.
4. Return tools as `MCPToolRecord`.
5. Keep provider credentials in MCP authentication state, not inside business modules.
6. Use `execute(server, tool, params)` from `app.mcp.execution.service`.

Do not add provider authentication, health checks, logs, or execution logic to Marketing, Sales, Product, or other business modules.

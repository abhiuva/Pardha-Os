# Meta MCP Server

Meta is the first MCP Runtime server.

Server id: `meta`

Tools:

- `campaign.list`
- `campaign.create`
- `campaign.pause`
- `campaign.resume`
- `analytics.summary`
- `lead.list`
- `audience.list`

Authentication is owned by MCP Runtime. Credentials are resolved from request payload or environment variables:

- `META_ACCESS_TOKEN`
- `META_BUSINESS_ACCOUNT_ID`
- `META_AD_ACCOUNT_ID`
- `META_PAGE_ID`
- `META_INSTAGRAM_ACCOUNT_ID`

Secrets are redacted before persistence.

Marketing must consume Meta through `/mcp/execute` or `app.mcp.execution.service.execute`; it must not own Meta authentication, health, logging, or diagnostics.

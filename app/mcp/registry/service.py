from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from app.db import SessionLocal
from app.db.models import MCPPermission, MCPServer, MCPServerCapability, MCPTool
from app.mcp.events.service import publish_event, write_log
from app.mcp.models.schemas import MCPHealthRecord, MCPServerRecord, MCPToolRecord
from app.mcp.servers.interface import MCPServerInterface
from app.mcp.servers.hubspot import hubspot_server
from app.mcp.servers.meta import meta_server


_SERVERS: Dict[str, MCPServerInterface] = {"meta": meta_server, "hubspot": hubspot_server}
_DEFAULTS_READY = False


def ensure_default_servers() -> None:
    global _DEFAULTS_READY
    if _DEFAULTS_READY:
        return
    for server in _SERVERS.values():
        register(server)
    _DEFAULTS_READY = True


def register(server: MCPServerInterface) -> MCPServerRecord:
    now = datetime.now(timezone.utc)
    tools = server.discover_tools()
    permissions = server.permissions()
    capabilities = sorted({permission.split(".")[1] if "." in permission else permission for permission in permissions})
    with SessionLocal() as session:
        row = session.get(MCPServer, server.server_id) or MCPServer(
            mcp_server_id=server.server_id,
            name=f"{server.name} MCP Server",
            endpoint=server.metadata().get("endpoint", "https://graph.facebook.com" if server.server_id == "meta" else "https://api.hubapi.com" if server.server_id == "hubspot" else "local://mcp"),
            transport="https" if server.server_id in {"meta", "hubspot"} else "stdio",
            authentication={"type": "bearer" if server.server_id in {"meta", "hubspot"} else "none", "status": "missing_credentials"},
            status="registered",
            health="unknown",
            created_at=now,
            updated_at=now,
        )
        row.capabilities = capabilities
        row.supported_tools = [tool.name for tool in tools]
        row.updated_at = now
        session.merge(row)
        session.flush()
        for capability in capabilities:
            session.merge(MCPServerCapability(
                capability_id=f"{server.server_id}.{capability}",
                server_id=server.server_id,
                name=capability,
                description=f"{server.name} {capability} capability",
                metadata_json={},
                created_at=now,
                updated_at=now,
            ))
        for tool in tools:
            session.merge(MCPTool(
                tool_id=tool.tool_id,
                server_id=server.server_id,
                name=tool.name,
                description=tool.description,
                input_schema=tool.input_schema,
                permissions=tool.permissions,
                enabled=1 if tool.enabled else 0,
                created_at=now,
                updated_at=now,
            ))
        for permission in permissions:
            session.merge(MCPPermission(
                permission_id=f"{server.server_id}.{permission}",
                server_id=server.server_id,
                permission=permission,
                description=f"Allows {permission}",
                granted=0,
                created_at=now,
                updated_at=now,
            ))
        session.commit()
    publish_event(server.server_id, "Server Registered", {"tools": [tool.name for tool in tools]})
    write_log(server.server_id, "info", "Server registered with MCP Runtime.", {"capabilities": capabilities})
    return metadata(server.server_id)


def unregister(server_id: str) -> dict:
    with SessionLocal() as session:
        row = session.get(MCPServer, server_id)
        if row:
            row.status = "unregistered"
            row.health = "unknown"
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
    publish_event(server_id, "Server Disconnected", {"reason": "unregistered"})
    return {"server_id": server_id, "status": "unregistered"}


def discover() -> list[MCPServerRecord]:
    ensure_default_servers()
    with SessionLocal() as session:
        rows = session.query(MCPServer).order_by(MCPServer.name.asc()).all()
        return [_server_record(row) for row in rows]


def capabilities(server_id: str | None = None) -> dict[str, list[str]]:
    ensure_default_servers()
    with SessionLocal() as session:
        query = session.query(MCPServerCapability)
        if server_id:
            query = query.filter(MCPServerCapability.server_id == server_id)
        result: dict[str, list[str]] = {}
        for row in query.order_by(MCPServerCapability.server_id.asc(), MCPServerCapability.name.asc()).all():
            result.setdefault(row.server_id, []).append(row.name)
        return result


def tools(server_id: str | None = None) -> list[MCPToolRecord]:
    ensure_default_servers()
    with SessionLocal() as session:
        query = session.query(MCPTool)
        if server_id:
            query = query.filter(MCPTool.server_id == server_id)
        rows = query.order_by(MCPTool.server_id.asc(), MCPTool.name.asc()).all()
        return [
            MCPToolRecord(tool_id=row.tool_id, server_id=row.server_id, name=row.name, description=row.description, input_schema=row.input_schema or {}, permissions=row.permissions or [], enabled=bool(row.enabled))
            for row in rows
        ]


def health(server_id: str | None = None) -> list[MCPHealthRecord]:
    ensure_default_servers()
    selected = [server for key, server in _SERVERS.items() if server_id in {None, key}]
    return [server.health() for server in selected]


def disconnect(server_id: str) -> dict:
    return _server(server_id).disconnect()


def metadata(server_id: str) -> MCPServerRecord:
    ensure_default_servers() if server_id not in _SERVERS else None
    with SessionLocal() as session:
        row = session.get(MCPServer, server_id)
        if row is None:
            raise KeyError(f"MCP server not found: {server_id}")
        return _server_record(row)


def server_impl(server_id: str) -> MCPServerInterface:
    return _server(server_id)


def _server(server_id: str) -> MCPServerInterface:
    server = _SERVERS.get(server_id)
    if server is None:
        raise KeyError(f"MCP server not registered: {server_id}")
    return server


def _server_record(row: MCPServer) -> MCPServerRecord:
    auth = row.authentication or {}
    return MCPServerRecord(
        server_id=row.mcp_server_id,
        name=row.name,
        provider=row.mcp_server_id,
        endpoint=row.endpoint,
        transport=row.transport,
        status=row.status,
        health=row.health,
        authentication_status=auth.get("status", "unknown"),
        capabilities=row.capabilities or [],
        supported_tools=row.supported_tools or [],
        last_seen=row.last_seen,
        metadata={"authentication": auth},
    )

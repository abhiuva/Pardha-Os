from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.db import SessionLocal
from app.db.models import MCPEvent, MCPLog
from app.mcp.execution.service import execute
from app.mcp.models.schemas import (
    MCPConnectRequest,
    MCPDisconnectRequest,
    MCPDiscoveryReport,
    MCPEventRecord,
    MCPExecuteRequest,
    MCPExecutionResult,
    MCPHealthRecord,
    MCPLogRecord,
    MCPRuntimeDashboard,
    MCPServerRecord,
    MCPToolRecord,
)
from app.mcp.registry import service as registry


router = APIRouter(prefix="/mcp", tags=["mcp-runtime"])


@router.get("/servers", response_model=list[MCPServerRecord])
def list_mcp_servers():
    return registry.discover()


@router.get("/servers/{server_id}", response_model=MCPServerRecord)
def get_mcp_server(server_id: str):
    try:
        return registry.metadata(server_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/connect", response_model=dict)
def connect_mcp_server(request: MCPConnectRequest):
    try:
        return registry.server_impl(request.server_id).connect(request.credentials, request.metadata)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/disconnect", response_model=dict)
def disconnect_mcp_server(request: MCPDisconnectRequest):
    try:
        return registry.disconnect(request.server_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/execute", response_model=MCPExecutionResult)
def execute_mcp_tool(request: MCPExecuteRequest):
    return execute(request.server, request.tool, request.params)


@router.get("/tools", response_model=list[MCPToolRecord])
def list_mcp_tools(server_id: str | None = None):
    return registry.tools(server_id)


@router.get("/health", response_model=list[MCPHealthRecord])
def get_mcp_health(server_id: str | None = None):
    return registry.health(server_id)


@router.get("/events", response_model=list[MCPEventRecord])
def list_mcp_events(server_id: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
    with SessionLocal() as session:
        query = session.query(MCPEvent)
        if server_id:
            query = query.filter(MCPEvent.server_id == server_id)
        rows = query.order_by(MCPEvent.created_at.desc()).limit(limit).all()
        return [MCPEventRecord(event_id=row.event_id, server_id=row.server_id, event_type=row.event_type, payload=row.payload or {}, created_at=row.created_at) for row in rows]


@router.get("/logs", response_model=list[MCPLogRecord])
def list_mcp_logs(server_id: str | None = None, limit: int = Query(default=100, ge=1, le=500)):
    with SessionLocal() as session:
        query = session.query(MCPLog)
        if server_id:
            query = query.filter(MCPLog.server_id == server_id)
        rows = query.order_by(MCPLog.created_at.desc()).limit(limit).all()
        return [MCPLogRecord(log_id=row.log_id, server_id=row.server_id, level=row.level, message=row.message, context=row.context or {}, created_at=row.created_at) for row in rows]


@router.get("/discovery", response_model=MCPDiscoveryReport)
def discover_mcp_runtime():
    servers = registry.discover()
    tools = registry.tools()
    return MCPDiscoveryReport(
        servers=servers,
        tools=tools,
        capabilities=registry.capabilities(),
        permissions={server.server_id: registry.server_impl(server.server_id).permissions() for server in servers if server.server_id in {"meta", "hubspot"}},
    )


@router.get("/dashboard", response_model=MCPRuntimeDashboard)
def mcp_runtime_dashboard():
    return MCPRuntimeDashboard(
        servers=registry.discover(),
        health=registry.health(),
        tools=registry.tools(),
        recent_events=list_mcp_events(limit=25),
        recent_logs=list_mcp_logs(limit=25),
    )

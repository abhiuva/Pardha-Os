from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AuthType = Literal["oauth2", "bearer", "api_key", "basic", "custom", "none"]


class MCPAuthPayload(BaseModel):
    server_id: str = "meta"
    auth_type: AuthType = "bearer"
    credentials: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPConnectRequest(BaseModel):
    server_id: str = "meta"
    auth_type: AuthType = "bearer"
    credentials: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPDisconnectRequest(BaseModel):
    server_id: str


class MCPExecuteRequest(BaseModel):
    server: str
    tool: str
    params: Dict[str, Any] = Field(default_factory=dict)


class MCPServerRecord(BaseModel):
    server_id: str
    name: str
    provider: str
    endpoint: str
    transport: str
    status: str
    health: str
    authentication_status: str
    capabilities: List[str] = Field(default_factory=list)
    supported_tools: List[str] = Field(default_factory=list)
    latency_ms: Optional[int] = None
    last_seen: Optional[datetime] = None
    failure_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPToolRecord(BaseModel):
    tool_id: str
    server_id: str
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    permissions: List[str] = Field(default_factory=list)
    enabled: bool = True


class MCPHealthRecord(BaseModel):
    server_id: str
    status: str
    latency_ms: Optional[int] = None
    last_seen: Optional[datetime] = None
    authentication_status: str
    capabilities: List[str] = Field(default_factory=list)
    connected_tools: List[str] = Field(default_factory=list)
    failure_count: int = 0
    message: str = ""


class MCPExecutionResult(BaseModel):
    execution_id: str
    server: str
    tool: str
    status: str
    latency_ms: int
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime


class MCPEventRecord(BaseModel):
    event_id: str
    server_id: str
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MCPLogRecord(BaseModel):
    log_id: str
    server_id: str
    level: str
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MCPDiscoveryReport(BaseModel):
    servers: List[MCPServerRecord]
    tools: List[MCPToolRecord]
    capabilities: Dict[str, List[str]]
    permissions: Dict[str, List[str]]


class MCPRuntimeDashboard(BaseModel):
    servers: List[MCPServerRecord]
    health: List[MCPHealthRecord]
    tools: List[MCPToolRecord]
    recent_events: List[MCPEventRecord]
    recent_logs: List[MCPLogRecord]

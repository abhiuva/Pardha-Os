from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from app.db import SessionLocal
from app.db.models import MCPConnection, MCPExecutionHistory, MCPLog, MCPServer, MCPServerHealth
from app.mcp.authentication.service import authentication_status, redact_credentials, resolve_credentials
from app.mcp.events.service import publish_event, write_log
from app.mcp.models.schemas import MCPHealthRecord, MCPLogRecord, MCPToolRecord
from app.mcp.servers.interface import MCPServerInterface
from app.settings import get_settings


META_TOOLS = [
    ("campaign.list", "List Meta campaigns", ["meta.campaigns.read"]),
    ("campaign.create", "Create Meta campaign draft", ["meta.campaigns.write"]),
    ("campaign.pause", "Pause a Meta campaign", ["meta.campaigns.write"]),
    ("campaign.resume", "Resume a Meta campaign", ["meta.campaigns.write"]),
    ("analytics.summary", "Read Meta analytics summary", ["meta.analytics.read"]),
    ("lead.list", "List Meta lead forms and leads", ["meta.leads.read"]),
    ("audience.list", "List Meta audiences", ["meta.audiences.read"]),
    ("instagram.media.list", "List Instagram business media", ["meta.instagram.read"]),
    ("instagram.insights.summary", "Read Instagram business account insights", ["meta.instagram.read"]),
]

READ_TOOLS = {"campaign.list", "analytics.summary", "lead.list", "audience.list", "instagram.media.list", "instagram.insights.summary"}


class MetaMCPServer(MCPServerInterface):
    server_id = "meta"
    name = "Meta"
    provider = "meta"

    def connect(self, credentials: Dict[str, Any], metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        resolved = resolve_credentials("meta", credentials)
        status = authentication_status("meta", resolved)
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            server = session.get(MCPServer, self.server_id) or MCPServer(
                mcp_server_id=self.server_id,
                name="Meta MCP Server",
                endpoint="https://graph.facebook.com",
                transport="https",
                created_at=now,
                updated_at=now,
            )
            server.authentication = {"type": "bearer", "status": status, "credentials": redact_credentials(resolved)}
            server.status = "connected" if status == "configured" else "needs_auth"
            server.health = "healthy" if status == "configured" else "degraded"
            server.capabilities = ["campaigns", "adsets", "ads", "audiences", "pixels", "leads", "analytics"]
            server.supported_tools = [name for name, _description, _permissions in META_TOOLS]
            server.last_seen = now
            server.updated_at = now
            session.merge(server)
            session.merge(MCPConnection(
                connection_id="meta-default",
                server_id=self.server_id,
                auth_type="bearer",
                authentication_status=status,
                credentials=redact_credentials(resolved),
                metadata_json=metadata or {},
                connected_at=now if status == "configured" else None,
                disconnected_at=None,
                created_at=now,
                updated_at=now,
            ))
            session.commit()
        publish_event(self.server_id, "Server Connected" if status == "configured" else "Authentication Changed", {"status": status})
        write_log(self.server_id, "info", f"Meta connection {status}.", {"metadata": metadata or {}})
        return {"server_id": self.server_id, "status": status, "connected": status == "configured"}

    def disconnect(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            server = session.get(MCPServer, self.server_id)
            if server:
                server.status = "disconnected"
                server.health = "unknown"
                server.updated_at = now
            connection = session.get(MCPConnection, "meta-default")
            if connection:
                connection.authentication_status = "disconnected"
                connection.disconnected_at = now
                connection.updated_at = now
            session.commit()
        publish_event(self.server_id, "Server Disconnected", {})
        write_log(self.server_id, "info", "Meta disconnected.")
        return {"server_id": self.server_id, "status": "disconnected", "connected": False}

    def authenticate(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        return {"authentication_status": authentication_status("meta", credentials)}

    def health(self) -> MCPHealthRecord:
        started = time.monotonic()
        with SessionLocal() as session:
            server = session.get(MCPServer, self.server_id)
            connection = session.get(MCPConnection, "meta-default")
            auth_status = connection.authentication_status if connection else authentication_status("meta", {})
            connected = bool(server and server.status == "connected" and auth_status == "configured")
            mock_mode = get_settings().connector_mode == "mock"
            latency = int((time.monotonic() - started) * 1000)
            failure_count = session.query(MCPExecutionHistory).filter(MCPExecutionHistory.server_id == self.server_id, MCPExecutionHistory.status == "failed").count()
            record = MCPHealthRecord(
                server_id=self.server_id,
                status="healthy" if connected else ("mock" if mock_mode else "degraded"),
                latency_ms=latency,
                last_seen=datetime.now(timezone.utc) if connected else (server.last_seen if server else None),
                authentication_status=auth_status,
                capabilities=server.capabilities if server else ["campaigns", "analytics", "leads", "instagram"],
                connected_tools=server.supported_tools if connected and server else [],
                failure_count=failure_count,
                message="Meta ready through MCP Runtime." if connected else "Meta live credentials are missing; mock connector contract is available." if mock_mode else "Meta credentials are not configured.",
            )
            session.merge(MCPServerHealth(
                health_id=f"meta-{int(time.time())}",
                server_id=self.server_id,
                status=record.status,
                latency_ms=latency,
                authentication_status=auth_status,
                capabilities=record.capabilities,
                connected_tools=record.connected_tools,
                failure_count=failure_count,
                message=record.message,
                checked_at=datetime.now(timezone.utc),
            ))
            session.commit()
            return record

    def discover_tools(self) -> List[MCPToolRecord]:
        return [
            MCPToolRecord(tool_id=f"meta.{tool}", server_id=self.server_id, name=tool, description=description, permissions=permissions)
            for tool, description, permissions in META_TOOLS
        ]

    def execute(self, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool not in {item[0] for item in META_TOOLS}:
            raise ValueError(f"Meta tool is not registered: {tool}")
        health = self.health()
        mock_mode = get_settings().connector_mode == "mock"
        if health.authentication_status != "configured" and not (mock_mode and tool in READ_TOOLS):
            raise PermissionError("Meta is not authenticated in MCP Runtime.")
        mode = "mock_contract" if health.authentication_status != "configured" else "live_ready_empty"
        if tool == "campaign.list":
            return {"campaigns": [], "source": "meta_mcp", "mode": mode}
        if tool == "analytics.summary":
            return {"spend": 0, "reach": 0, "impressions": 0, "ctr": 0, "cpc": 0, "cpm": 0, "roas": 0, "mode": mode}
        if tool == "lead.list":
            return {"leads": [], "mode": mode}
        if tool == "audience.list":
            return {"audiences": [], "mode": mode}
        if tool == "instagram.media.list":
            return {"media": [], "source": "instagram_business_account", "mode": mode}
        if tool == "instagram.insights.summary":
            return {"reach": 0, "profile_views": 0, "website_clicks": 0, "followers": 0, "mode": mode}
        return {
            "accepted": False,
            "requires_approval": True,
            "tool": tool,
            "params": params,
            "mode": "local_draft_only",
            "message": "External Meta writes require explicit founder approval.",
        }

    def logs(self, limit: int = 100) -> List[MCPLogRecord]:
        with SessionLocal() as session:
            rows = session.query(MCPLog).filter(MCPLog.server_id == self.server_id).order_by(MCPLog.created_at.desc()).limit(limit).all()
            return [MCPLogRecord(log_id=row.log_id, server_id=row.server_id, level=row.level, message=row.message, context=row.context or {}, created_at=row.created_at) for row in rows]

    def permissions(self) -> List[str]:
        permissions: list[str] = []
        for _tool, _description, tool_permissions in META_TOOLS:
            permissions.extend(tool_permissions)
        return sorted(set(permissions))

    def metadata(self) -> Dict[str, Any]:
        return {"provider": "meta", "api": "Meta Graph API", "resources": ["business", "ad_account", "page", "instagram"]}


meta_server = MetaMCPServer()

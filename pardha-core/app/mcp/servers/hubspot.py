from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.db import SessionLocal
from app.db.models import MCPConnection, MCPExecutionHistory, MCPLog, MCPServer, MCPServerHealth
from app.mcp.authentication.service import authentication_status, redact_credentials, resolve_credentials
from app.mcp.events.service import publish_event, write_log
from app.mcp.models.schemas import MCPHealthRecord, MCPLogRecord, MCPToolRecord
from app.mcp.servers.interface import MCPServerInterface
from app.settings import get_settings


HUBSPOT_TOOLS = [
    ("contact.list", "List HubSpot contacts", ["hubspot.contacts.read"]),
    ("company.list", "List HubSpot companies", ["hubspot.companies.read"]),
    ("deal.list", "List HubSpot deals", ["hubspot.deals.read"]),
    ("activity.list", "List HubSpot activities", ["hubspot.activities.read"]),
    ("lead.draft", "Create a local HubSpot lead draft for founder approval", ["hubspot.leads.write"]),
    ("followup.draft", "Create a local HubSpot follow-up draft for founder approval", ["hubspot.activities.write"]),
]

READ_TOOLS = {"contact.list", "company.list", "deal.list", "activity.list"}


class HubSpotMCPServer(MCPServerInterface):
    server_id = "hubspot"
    name = "HubSpot"
    provider = "hubspot"

    def connect(self, credentials: Dict[str, Any], metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        resolved = resolve_credentials("hubspot", credentials)
        status = authentication_status("hubspot", resolved)
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            server = session.get(MCPServer, self.server_id) or MCPServer(
                mcp_server_id=self.server_id,
                name="HubSpot MCP Server",
                endpoint="https://api.hubapi.com",
                transport="https",
                created_at=now,
                updated_at=now,
            )
            server.authentication = {"type": "bearer", "status": status, "credentials": redact_credentials(resolved)}
            server.status = "connected" if status == "configured" else "needs_auth"
            server.health = "healthy" if status == "configured" else "degraded"
            server.capabilities = ["contacts", "companies", "deals", "activities", "drafts"]
            server.supported_tools = [name for name, _description, _permissions in HUBSPOT_TOOLS]
            server.last_seen = now if status == "configured" else None
            server.updated_at = now
            session.merge(server)
            session.merge(MCPConnection(
                connection_id="hubspot-default",
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
        write_log(self.server_id, "info", f"HubSpot connection {status}.", {"metadata": metadata or {}})
        return {"server_id": self.server_id, "status": status, "connected": status == "configured"}

    def disconnect(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            server = session.get(MCPServer, self.server_id)
            if server:
                server.status = "disconnected"
                server.health = "unknown"
                server.updated_at = now
            connection = session.get(MCPConnection, "hubspot-default")
            if connection:
                connection.authentication_status = "disconnected"
                connection.disconnected_at = now
                connection.updated_at = now
            session.commit()
        publish_event(self.server_id, "Server Disconnected", {})
        write_log(self.server_id, "info", "HubSpot disconnected.")
        return {"server_id": self.server_id, "status": "disconnected", "connected": False}

    def authenticate(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        return {"authentication_status": authentication_status("hubspot", credentials)}

    def health(self) -> MCPHealthRecord:
        started = time.monotonic()
        with SessionLocal() as session:
            server = session.get(MCPServer, self.server_id)
            connection = session.get(MCPConnection, "hubspot-default")
            auth_status = connection.authentication_status if connection else authentication_status("hubspot", {})
            connected = bool(server and server.status == "connected" and auth_status == "configured")
            mock_mode = get_settings().connector_mode == "mock"
            latency = int((time.monotonic() - started) * 1000)
            failure_count = session.query(MCPExecutionHistory).filter(MCPExecutionHistory.server_id == self.server_id, MCPExecutionHistory.status == "failed").count()
            capabilities = server.capabilities if server else ["contacts", "companies", "deals", "activities", "drafts"]
            record = MCPHealthRecord(
                server_id=self.server_id,
                status="healthy" if connected else ("mock" if mock_mode else "degraded"),
                latency_ms=latency,
                last_seen=datetime.now(timezone.utc) if connected else (server.last_seen if server else None),
                authentication_status=auth_status,
                capabilities=capabilities,
                connected_tools=server.supported_tools if connected and server else [],
                failure_count=failure_count,
                message="HubSpot ready through MCP Runtime." if connected else "HubSpot live credentials are missing; mock connector contract is available." if mock_mode else "HubSpot credentials are not configured.",
            )
            session.merge(MCPServerHealth(
                health_id=f"hubspot-{int(time.time())}",
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
            MCPToolRecord(tool_id=f"hubspot.{tool}", server_id=self.server_id, name=tool, description=description, permissions=permissions)
            for tool, description, permissions in HUBSPOT_TOOLS
        ]

    def execute(self, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool not in {item[0] for item in HUBSPOT_TOOLS}:
            raise ValueError(f"HubSpot tool is not registered: {tool}")
        health = self.health()
        mock_mode = get_settings().connector_mode == "mock"
        if health.authentication_status != "configured" and not mock_mode:
            raise PermissionError("HubSpot is not authenticated in MCP Runtime.")
        if tool in READ_TOOLS:
            return {"items": [], "source": "hubspot_mcp", "mode": "mock_contract" if health.authentication_status != "configured" else "live_ready_empty"}
        if tool == "lead.draft" and params.get("lead_id"):
            from app.hubspot.service import sync_lead

            result = sync_lead(str(params["lead_id"]), allow_write=False)
            return result.model_dump(mode="json")
        return {
            "accepted": False,
            "requires_approval": True,
            "tool": tool,
            "params": params,
            "mode": "local_draft_only",
            "message": "External HubSpot writes require explicit founder approval.",
        }

    def logs(self, limit: int = 100) -> List[MCPLogRecord]:
        with SessionLocal() as session:
            rows = session.query(MCPLog).filter(MCPLog.server_id == self.server_id).order_by(MCPLog.created_at.desc()).limit(limit).all()
            return [MCPLogRecord(log_id=row.log_id, server_id=row.server_id, level=row.level, message=row.message, context=row.context or {}, created_at=row.created_at) for row in rows]

    def permissions(self) -> List[str]:
        permissions: list[str] = []
        for _tool, _description, tool_permissions in HUBSPOT_TOOLS:
            permissions.extend(tool_permissions)
        return sorted(set(permissions))

    def metadata(self) -> Dict[str, Any]:
        return {"provider": "hubspot", "api": "HubSpot CRM API", "resources": ["contacts", "companies", "deals", "activities"]}


hubspot_server = HubSpotMCPServer()

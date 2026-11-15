from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from app.db import SessionLocal
from app.db.models import MCPExecutionHistory
from app.mcp.events.service import publish_event, write_log
from app.mcp.models.schemas import MCPExecutionResult
from app.mcp.registry.service import server_impl


def execute(server: str, tool: str, params: Dict[str, Any] | None = None) -> MCPExecutionResult:
    execution_id = str(uuid4())
    payload = params or {}
    started = time.monotonic()
    created_at = datetime.now(timezone.utc)
    publish_event(server, "Execution Started", {"execution_id": execution_id, "tool": tool})
    try:
        output = server_impl(server).execute(tool, payload)
        status = "finished"
        error = None
        publish_event(server, "Execution Finished", {"execution_id": execution_id, "tool": tool})
        write_log(server, "info", f"Executed {tool}.", {"execution_id": execution_id})
    except Exception as exc:
        output = {}
        status = "failed"
        error = str(exc)
        publish_event(server, "Execution Failed", {"execution_id": execution_id, "tool": tool, "error": error})
        write_log(server, "error", f"Execution failed for {tool}: {error}", {"execution_id": execution_id})
    latency_ms = int((time.monotonic() - started) * 1000)
    with SessionLocal() as session:
        session.add(MCPExecutionHistory(
            execution_id=execution_id,
            server_id=server,
            tool=tool,
            parameters=payload,
            status=status,
            latency_ms=latency_ms,
            output=output,
            error=error,
            created_at=created_at,
        ))
        session.commit()
    return MCPExecutionResult(execution_id=execution_id, server=server, tool=tool, status=status, latency_ms=latency_ms, output=output, error=error, created_at=created_at)

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.mcp.models.schemas import MCPHealthRecord, MCPLogRecord, MCPToolRecord


class MCPServerInterface(ABC):
    server_id: str
    name: str
    provider: str

    @abstractmethod
    def connect(self, credentials: Dict[str, Any], metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> MCPHealthRecord:
        raise NotImplementedError

    @abstractmethod
    def discover_tools(self) -> List[MCPToolRecord]:
        raise NotImplementedError

    @abstractmethod
    def execute(self, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def logs(self, limit: int = 100) -> List[MCPLogRecord]:
        raise NotImplementedError

    @abstractmethod
    def permissions(self) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        raise NotImplementedError

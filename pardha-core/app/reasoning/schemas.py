from __future__ import annotations

from datetime import datetime

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentReasoning(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reasoning_id: str
    business_id: Optional[str] = None
    agent_name: str
    prompt: str
    response: str
    model: str
    source: str
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class ReasoningRequest(BaseModel):
    model: Literal["llama3.2:3b", "qwen3:8b"] = "llama3.2:3b"
    business_id: Optional[str] = None

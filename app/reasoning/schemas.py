from __future__ import annotations

from datetime import datetime

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class AgentReasoning(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reasoning_id: str
    business_id: Optional[str] = None
    agent_name: str
    prompt: str
    response: str
    model: str
    source: str
    timestamp: datetime


class ReasoningRequest(BaseModel):
    model: Literal["llama3.2:3b", "qwen3:8b"] = "qwen3:8b"
    business_id: Optional[str] = None

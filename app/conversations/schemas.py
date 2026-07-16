from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    business_id: Optional[str] = None
    owner: str = "Founder"
    conversation_type: str = "general"
    pinned: bool = False


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    pinned: Optional[bool] = None
    archived: Optional[bool] = None
    summary: Optional[str] = None


class ConversationSession(BaseModel):
    conversation_id: str
    title: str
    business_id: Optional[str]
    owner: str
    conversation_type: str
    pinned: bool
    archived: bool
    summary: str
    context_snapshot: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ConversationMessage(BaseModel):
    message_id: str
    conversation_id: str
    business_id: Optional[str]
    role: str
    content: str
    intent: str
    conversation_type: str
    context_snapshot: Dict[str, Any]
    capability_ids: List[str]
    response_payload: Dict[str, Any]
    created_at: datetime


class ConversationTimelineEvent(BaseModel):
    timeline_event_id: str
    conversation_id: str
    message_id: Optional[str]
    event_type: str
    title: str
    detail: str
    payload: Dict[str, Any]
    created_at: datetime


class ConversationDetail(BaseModel):
    conversation: ConversationSession
    messages: List[ConversationMessage]
    timeline: List[ConversationTimelineEvent]


class ConversationMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    business_id: Optional[str] = None
    owner: str = "Founder"


class SuggestedAction(BaseModel):
    label: str
    intent: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    executable: bool = True


class ConversationResponsePayload(BaseModel):
    executive_summary: str
    reasoning: List[str]
    capabilities_used: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    confidence: int
    next_recommended_actions: List[SuggestedAction]
    execution: Optional[Dict[str, Any]] = None
    verification: Dict[str, Any] = Field(default_factory=dict)
    transparency: Dict[str, Any] = Field(default_factory=dict)
    runtime_inspection: Dict[str, Any] = Field(default_factory=dict)
    reasoning_used: bool = False
    reasoning_provider: str = "deterministic"
    response_style: str = "executive"


class ConversationMessageResponse(BaseModel):
    conversation: ConversationSession
    user_message: ConversationMessage
    assistant_message: ConversationMessage
    timeline: List[ConversationTimelineEvent]
    response: ConversationResponsePayload


class ConversationExport(BaseModel):
    conversation: ConversationSession
    messages: List[ConversationMessage]
    timeline: List[ConversationTimelineEvent]
    exported_at: datetime


class ConversationDeleteResult(BaseModel):
    conversation_id: str
    deleted: bool


class ConversationEngineStatus(BaseModel):
    engine: str
    ready: bool
    database: Dict[str, Any]
    conversations: Dict[str, int]
    capabilities: Dict[str, Any]
    connectors: List[Dict[str, Any]]
    ollama: Dict[str, Any]
    voice: Dict[str, Any]
    pipeline: List[str]
    diagnostics: Dict[str, Any]


class ConversationValidationReport(BaseModel):
    score: int
    ready: bool
    checks: List[Dict[str, Any]]


class ConversationHardeningValidationReport(BaseModel):
    score: int
    ready: bool
    scenarios_run: int
    categories: Dict[str, Dict[str, Any]]
    failures: List[Dict[str, Any]]
    policy: Dict[str, bool]

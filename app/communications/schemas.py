from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


Provider = Literal["gmail", "outlook"]
MessageStatus = Literal["received", "draft", "sent", "failed"]
MessageDirection = Literal["inbound", "outbound"]


class CommunicationAccountCreate(BaseModel):
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    provider: Provider
    account_name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)
    status: str = "configured"


class CommunicationAccount(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: str
    business_id: str
    provider: Provider
    account_name: str
    email: str
    status: str
    last_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MessageRequest(BaseModel):
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    account_id: str
    recipients: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)


class Message(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: str
    business_id: str
    account_id: str
    thread_id: str
    provider_message_id: Optional[str] = None
    provider_thread_id: Optional[str] = None
    direction: MessageDirection
    status: MessageStatus
    sender: str
    recipients: list[str]
    cc: list[str]
    bcc: list[str]
    subject: str
    body: str
    snippet: str
    labels: list[str]
    is_read: bool
    sent_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MessageThread(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    thread_id: str
    business_id: str
    account_id: str
    provider_thread_id: Optional[str] = None
    subject: str
    participants: list[str]
    unread_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CommunicationHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    history_id: str
    business_id: str
    account_id: Optional[str] = None
    message_id: Optional[str] = None
    action: str
    status: str
    detail: str
    payload: Dict[str, Any]
    created_at: datetime


class InboxSummary(BaseModel):
    unread_count: int
    inbound_count: int
    draft_count: int
    sent_count: int
    risks: list[str]
    opportunities: list[str]
    followups: list[str]

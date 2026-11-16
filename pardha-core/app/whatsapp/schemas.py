from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


WhatsAppProvider = Literal["whatsapp_cloud", "twilio", "meta_direct"]
WhatsAppMessageType = Literal["text", "template"]
WhatsAppDirection = Literal["inbound", "outbound"]
WhatsAppMessageStatus = Literal["received", "queued", "sent", "delivered", "read", "failed"]


class WhatsAppAccountCreate(BaseModel):
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    phone_number: str = Field(..., min_length=3)
    provider: WhatsAppProvider = "whatsapp_cloud"
    status: str = "configured"


class WhatsAppAccount(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: str
    business_id: str
    phone_number: str
    provider: WhatsAppProvider
    status: str
    last_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WhatsAppSendRequest(BaseModel):
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    account_id: str
    to_phone: str = Field(..., min_length=3)
    body: str = Field(..., min_length=1)


class WhatsAppTemplateRequest(BaseModel):
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    account_id: str
    to_phone: str = Field(..., min_length=3)
    template_name: str = Field(..., min_length=1)
    language: str = "en"
    parameters: list[str] = Field(default_factory=list)
    body: Optional[str] = None


class WhatsAppReceiveRequest(BaseModel):
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    account_id: str
    from_phone: str = Field(..., min_length=3)
    body: str = Field(..., min_length=1)
    provider_message_id: Optional[str] = None
    contact_name: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class WhatsAppTemplateCreate(BaseModel):
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    account_id: Optional[str] = None
    template_name: str = Field(..., min_length=1)
    language: str = "en"
    body: str = Field(..., min_length=1)
    status: str = "approved"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WhatsAppConversation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: str
    business_id: str
    account_id: str
    contact_phone: str
    contact_name: Optional[str] = None
    status: str
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WhatsAppTemplate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    template_id: str
    business_id: str
    account_id: Optional[str] = None
    template_name: str
    language: str
    body: str
    status: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WhatsAppMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: str
    business_id: str
    account_id: str
    conversation_id: str
    provider_message_id: Optional[str] = None
    direction: WhatsAppDirection
    message_type: WhatsAppMessageType
    status: WhatsAppMessageStatus
    sender_phone: str
    recipient_phone: str
    body: str
    template_name: Optional[str] = None
    payload: Dict[str, Any]
    sent_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WhatsAppSummary(BaseModel):
    connected_numbers: int
    message_volume: int
    inbound_count: int
    outbound_count: int
    active_conversations: int
    risk_notifications: list[str]
    executive_alerts: list[str]
    operations_updates: list[str]

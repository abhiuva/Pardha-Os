from __future__ import annotations

from app.whatsapp.schemas import WhatsAppMessage, WhatsAppSendRequest, WhatsAppTemplateRequest
from app.whatsapp.service import get_conversation, send_message, send_template


def send_outreach_message(*, account_id: str, to_phone: str, body: str, business_id: str | None = None) -> WhatsAppMessage:
    return send_message(
        WhatsAppSendRequest(
            business_id=business_id,
            account_id=account_id,
            to_phone=to_phone,
            body=body,
        )
    )


def follow_up_lead(*, account_id: str, to_phone: str, lead_name: str, next_step: str, business_id: str | None = None) -> WhatsAppMessage:
    return send_outreach_message(
        account_id=account_id,
        to_phone=to_phone,
        body=f"Hi {lead_name}, following up on our conversation. Proposed next step: {next_step}.",
        business_id=business_id,
    )


def send_proposal(*, account_id: str, to_phone: str, template_name: str, parameters: list[str], business_id: str | None = None) -> WhatsAppMessage:
    return send_template(
        WhatsAppTemplateRequest(
            business_id=business_id,
            account_id=account_id,
            to_phone=to_phone,
            template_name=template_name,
            parameters=parameters,
        )
    )


def track_conversation_status(conversation_id: str, business_id: str | None = None) -> list[WhatsAppMessage]:
    return get_conversation(conversation_id, business_id=business_id)

from __future__ import annotations

from app.communications.schemas import Message, MessageRequest
from app.communications.service import create_draft, search_messages


def draft_outreach_email(
    *,
    account_id: str,
    recipient: str,
    subject: str,
    body: str,
    business_id: str | None = None,
) -> Message:
    return create_draft(
        MessageRequest(
            business_id=business_id,
            account_id=account_id,
            recipients=[recipient],
            subject=subject,
            body=body,
        )
    )


def draft_lead_followup(
    *,
    account_id: str,
    recipient: str,
    lead_name: str,
    next_step: str,
    business_id: str | None = None,
) -> Message:
    return draft_outreach_email(
        account_id=account_id,
        recipient=recipient,
        subject=f"Following up with {lead_name}",
        body=f"Hi {lead_name},\n\nFollowing up on our conversation. Proposed next step: {next_step}.\n\nRegards,\nPardha",
        business_id=business_id,
    )


def track_prospects(query: str, business_id: str | None = None) -> list[Message]:
    return search_messages(query=query, business_id=business_id)

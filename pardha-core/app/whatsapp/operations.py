from __future__ import annotations

from app.whatsapp.schemas import WhatsAppMessage, WhatsAppSendRequest
from app.whatsapp.service import send_message


def notify_pickup_completed(*, account_id: str, to_phone: str, order_ref: str, business_id: str | None = None) -> WhatsAppMessage:
    return send_message(
        WhatsAppSendRequest(
            business_id=business_id,
            account_id=account_id,
            to_phone=to_phone,
            body=f"Pickup completed for {order_ref}.",
        )
    )


def notify_lunch_delivered(*, account_id: str, to_phone: str, order_ref: str, business_id: str | None = None) -> WhatsAppMessage:
    return send_message(
        WhatsAppSendRequest(
            business_id=business_id,
            account_id=account_id,
            to_phone=to_phone,
            body=f"Lunch delivered for {order_ref}.",
        )
    )


def notify_subscription_renewal(*, account_id: str, to_phone: str, renewal_date: str, business_id: str | None = None) -> WhatsAppMessage:
    return send_message(
        WhatsAppSendRequest(
            business_id=business_id,
            account_id=account_id,
            to_phone=to_phone,
            body=f"Your EatOnTime subscription renewal is due on {renewal_date}.",
        )
    )

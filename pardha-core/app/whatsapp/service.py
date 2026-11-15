from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.business.service import get_active_business, resolve_business
from app.db import SessionLocal
from app.db.models import WhatsAppAccount as AccountModel
from app.db.models import WhatsAppConversation as ConversationModel
from app.db.models import WhatsAppMessage as MessageModel
from app.db.models import WhatsAppTemplate as TemplateModel
from app.whatsapp.connectors import WhatsAppProviderMessage, get_connector
from app.whatsapp.schemas import (
    WhatsAppAccount,
    WhatsAppAccountCreate,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppReceiveRequest,
    WhatsAppSendRequest,
    WhatsAppSummary,
    WhatsAppTemplate,
    WhatsAppTemplateCreate,
    WhatsAppTemplateRequest,
)


RISK_KEYWORDS = {"blocked", "critical", "delay", "emergency", "escalation", "failed", "issue", "risk", "urgent"}
ALERT_KEYWORDS = {"alert", "approval", "executive", "summary", "update"}
OPERATIONS_KEYWORDS = {"delivered", "lunch", "pickup", "renewal", "subscription"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_account(row: AccountModel) -> WhatsAppAccount:
    return WhatsAppAccount.model_validate(row)


def _row_to_conversation(row: ConversationModel) -> WhatsAppConversation:
    return WhatsAppConversation.model_validate(row)


def _row_to_message(row: MessageModel) -> WhatsAppMessage:
    return WhatsAppMessage.model_validate(row)


def _row_to_template(row: TemplateModel) -> WhatsAppTemplate:
    return WhatsAppTemplate(
        template_id=row.template_id,
        business_id=row.business_id,
        account_id=row.account_id,
        template_name=row.template_name,
        language=row.language,
        body=row.body,
        status=row.status,
        metadata=row.metadata_json or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _normalize_phone(value: str) -> str:
    return value.strip().replace(" ", "")


def create_account(data: WhatsAppAccountCreate | dict) -> WhatsAppAccount:
    validated = WhatsAppAccountCreate.model_validate(data)
    business = resolve_business(
        business_id=validated.business_id,
        business_name=validated.business_name,
        text=validated.phone_number,
    )
    phone_number = _normalize_phone(validated.phone_number)
    now = _now()
    with SessionLocal() as session:
        existing = (
            session.query(AccountModel)
            .filter(
                AccountModel.business_id == business.business_id,
                AccountModel.provider == validated.provider,
                AccountModel.phone_number == phone_number,
            )
            .one_or_none()
        )
        if existing is not None:
            existing.status = validated.status.strip()
            existing.updated_at = now
            session.commit()
            session.refresh(existing)
            return _row_to_account(existing)

        row = AccountModel(
            account_id=str(uuid4()),
            business_id=business.business_id,
            phone_number=phone_number,
            provider=validated.provider,
            status=validated.status.strip(),
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _row_to_account(row)


def get_accounts(business_id: Optional[str] = None) -> list[WhatsAppAccount]:
    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        rows = (
            session.query(AccountModel)
            .filter(AccountModel.business_id == resolved_business_id)
            .order_by(AccountModel.provider, AccountModel.phone_number, AccountModel.account_id)
            .all()
        )
        return [_row_to_account(row) for row in rows]


def _get_account(session, account_id: str, business_id: str | None = None) -> AccountModel:
    row = session.get(AccountModel, account_id)
    if row is None:
        raise ValueError("WhatsApp account not found.")
    if business_id is not None and row.business_id != business_id:
        raise ValueError("WhatsApp account does not belong to selected business.")
    return row


def _get_or_create_conversation(
    session,
    *,
    business_id: str,
    account_id: str,
    contact_phone: str,
    contact_name: str | None,
    message_time: datetime,
) -> ConversationModel:
    row = (
        session.query(ConversationModel)
        .filter(
            ConversationModel.business_id == business_id,
            ConversationModel.account_id == account_id,
            ConversationModel.contact_phone == contact_phone,
        )
        .one_or_none()
    )
    now = _now()
    if row is None:
        row = ConversationModel(
            conversation_id=str(uuid4()),
            business_id=business_id,
            account_id=account_id,
            contact_phone=contact_phone,
            contact_name=contact_name,
            status="active",
            message_count=0,
            last_message_at=message_time,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
    if contact_name:
        row.contact_name = contact_name
    row.message_count += 1
    row.last_message_at = message_time
    row.updated_at = now
    return row


def _persist_provider_message(
    session,
    *,
    account: AccountModel,
    provider_message: WhatsAppProviderMessage,
    direction: str,
    contact_phone: str,
    contact_name: str | None = None,
) -> MessageModel:
    message_time = provider_message.received_at or provider_message.sent_at or _now()
    conversation = _get_or_create_conversation(
        session,
        business_id=account.business_id,
        account_id=account.account_id,
        contact_phone=contact_phone,
        contact_name=contact_name,
        message_time=message_time,
    )
    row = MessageModel(
        message_id=str(uuid4()),
        business_id=account.business_id,
        account_id=account.account_id,
        conversation_id=conversation.conversation_id,
        provider_message_id=provider_message.provider_message_id,
        direction=direction,
        message_type=provider_message.message_type,
        status=provider_message.status,
        sender_phone=provider_message.sender_phone,
        recipient_phone=provider_message.recipient_phone,
        body=provider_message.body,
        template_name=provider_message.template_name,
        payload=provider_message.payload or {},
        sent_at=provider_message.sent_at,
        received_at=provider_message.received_at,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(row)
    account.last_sync = _now()
    account.updated_at = _now()
    return row


def send_message(request: WhatsAppSendRequest | dict) -> WhatsAppMessage:
    validated = WhatsAppSendRequest.model_validate(request)
    with SessionLocal() as session:
        account = _get_account(session, validated.account_id, business_id=validated.business_id)
        connector = get_connector(account.provider)
        to_phone = _normalize_phone(validated.to_phone)
        provider_message = connector.send_message(account.phone_number, to_phone, validated.body.strip())
        row = _persist_provider_message(
            session,
            account=account,
            provider_message=provider_message,
            direction="outbound",
            contact_phone=to_phone,
        )
        session.commit()
        session.refresh(row)
        return _row_to_message(row)


def _render_template(body: str, parameters: list[str]) -> str:
    rendered = body
    for index, value in enumerate(parameters, start=1):
        rendered = rendered.replace(f"{{{{{index}}}}}", value)
    return rendered


def create_template(data: WhatsAppTemplateCreate | dict) -> WhatsAppTemplate:
    validated = WhatsAppTemplateCreate.model_validate(data)
    business = resolve_business(
        business_id=validated.business_id,
        business_name=validated.business_name,
        text=f"{validated.template_name} {validated.body}",
    )
    now = _now()
    with SessionLocal() as session:
        if validated.account_id:
            _get_account(session, validated.account_id, business_id=business.business_id)
        existing = (
            session.query(TemplateModel)
            .filter(
                TemplateModel.business_id == business.business_id,
                TemplateModel.template_name == validated.template_name.strip(),
                TemplateModel.language == validated.language.strip(),
            )
            .one_or_none()
        )
        if existing is not None:
            existing.account_id = validated.account_id
            existing.body = validated.body.strip()
            existing.status = validated.status.strip()
            existing.metadata_json = validated.metadata
            existing.updated_at = now
            session.commit()
            session.refresh(existing)
            return _row_to_template(existing)

        row = TemplateModel(
            template_id=str(uuid4()),
            business_id=business.business_id,
            account_id=validated.account_id,
            template_name=validated.template_name.strip(),
            language=validated.language.strip(),
            body=validated.body.strip(),
            status=validated.status.strip(),
            metadata_json=validated.metadata,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _row_to_template(row)


def send_template(request: WhatsAppTemplateRequest | dict) -> WhatsAppMessage:
    validated = WhatsAppTemplateRequest.model_validate(request)
    with SessionLocal() as session:
        account = _get_account(session, validated.account_id, business_id=validated.business_id)
        template = (
            session.query(TemplateModel)
            .filter(
                TemplateModel.business_id == account.business_id,
                TemplateModel.template_name == validated.template_name.strip(),
                TemplateModel.language == validated.language.strip(),
            )
            .one_or_none()
        )
        body = validated.body.strip() if validated.body else None
        if template is not None and body is None:
            body = _render_template(template.body, validated.parameters)
        if body is None:
            body = _render_template(validated.template_name, validated.parameters)
        connector = get_connector(account.provider)
        to_phone = _normalize_phone(validated.to_phone)
        provider_message = connector.send_template(
            account.phone_number,
            to_phone,
            validated.template_name.strip(),
            validated.language.strip(),
            validated.parameters,
            body,
        )
        row = _persist_provider_message(
            session,
            account=account,
            provider_message=provider_message,
            direction="outbound",
            contact_phone=to_phone,
        )
        session.commit()
        session.refresh(row)
        return _row_to_message(row)


def receive_message(request: WhatsAppReceiveRequest | dict) -> WhatsAppMessage:
    validated = WhatsAppReceiveRequest.model_validate(request)
    with SessionLocal() as session:
        account = _get_account(session, validated.account_id, business_id=validated.business_id)
        now = _now()
        provider_message = WhatsAppProviderMessage(
            provider_message_id=validated.provider_message_id or f"whatsapp-local-inbound-{uuid4()}",
            sender_phone=_normalize_phone(validated.from_phone),
            recipient_phone=account.phone_number,
            body=validated.body.strip(),
            status="received",
            received_at=now,
            payload=validated.payload,
        )
        row = _persist_provider_message(
            session,
            account=account,
            provider_message=provider_message,
            direction="inbound",
            contact_phone=provider_message.sender_phone,
            contact_name=validated.contact_name,
        )
        session.commit()
        session.refresh(row)
        return _row_to_message(row)


def get_messages(
    business_id: Optional[str] = None,
    *,
    account_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    limit: int = 50,
) -> list[WhatsAppMessage]:
    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        query = session.query(MessageModel).filter(MessageModel.business_id == resolved_business_id)
        if account_id:
            query = query.filter(MessageModel.account_id == account_id)
        if conversation_id:
            query = query.filter(MessageModel.conversation_id == conversation_id)
        rows = (
            query.order_by(MessageModel.created_at.desc(), MessageModel.message_id.desc())
            .limit(min(max(limit, 1), 200))
            .all()
        )
        return [_row_to_message(row) for row in rows]


def get_conversations(
    business_id: Optional[str] = None,
    *,
    account_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[WhatsAppConversation]:
    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        query = session.query(ConversationModel).filter(ConversationModel.business_id == resolved_business_id)
        if account_id:
            query = query.filter(ConversationModel.account_id == account_id)
        if status:
            query = query.filter(ConversationModel.status == status)
        rows = (
            query.order_by(ConversationModel.last_message_at.desc().nullslast(), ConversationModel.updated_at.desc())
            .limit(min(max(limit, 1), 200))
            .all()
        )
        return [_row_to_conversation(row) for row in rows]


def get_conversation(conversation_id: str, business_id: Optional[str] = None) -> list[WhatsAppMessage]:
    resolved_business_id = business_id or get_active_business().business_id
    return get_messages(business_id=resolved_business_id, conversation_id=conversation_id, limit=200)


def get_templates(business_id: Optional[str] = None) -> list[WhatsAppTemplate]:
    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        rows = (
            session.query(TemplateModel)
            .filter(TemplateModel.business_id == resolved_business_id)
            .order_by(TemplateModel.template_name, TemplateModel.language, TemplateModel.template_id)
            .all()
        )
        return [_row_to_template(row) for row in rows]


def summarize_whatsapp(business_id: Optional[str] = None) -> WhatsAppSummary:
    messages = get_messages(business_id=business_id, limit=200)
    conversations = get_conversations(business_id=business_id, limit=200)
    accounts = get_accounts(business_id=business_id)

    def has_any(message: WhatsAppMessage, keywords: set[str]) -> bool:
        text = message.body.lower()
        return any(keyword in text for keyword in keywords)

    return WhatsAppSummary(
        connected_numbers=len(accounts),
        message_volume=len(messages),
        inbound_count=len([message for message in messages if message.direction == "inbound"]),
        outbound_count=len([message for message in messages if message.direction == "outbound"]),
        active_conversations=len([conversation for conversation in conversations if conversation.status == "active"]),
        risk_notifications=[message.body for message in messages if has_any(message, RISK_KEYWORDS)][:5],
        executive_alerts=[message.body for message in messages if has_any(message, ALERT_KEYWORDS)][:5],
        operations_updates=[message.body for message in messages if has_any(message, OPERATIONS_KEYWORDS)][:5],
    )

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import or_

from app.business.service import get_active_business, resolve_business
from app.communications.connectors import ConnectorMessage, get_connector
from app.communications.schemas import (
    CommunicationAccount,
    CommunicationAccountCreate,
    CommunicationHistory,
    InboxSummary,
    Message,
    MessageRequest,
    MessageThread,
)
from app.db import SessionLocal
from app.db.models import CommunicationAccount as AccountModel
from app.db.models import CommunicationHistory as HistoryModel
from app.db.models import Message as MessageModel
from app.db.models import MessageThread as ThreadModel


RISK_KEYWORDS = {"blocked", "cancel", "complaint", "critical", "delay", "escalation", "failed", "issue", "risk"}
OPPORTUNITY_KEYWORDS = {"budget", "buy", "demo", "interested", "opportunity", "pilot", "pricing", "proposal", "renewal"}
FOLLOWUP_KEYWORDS = {"follow up", "follow-up", "next steps", "reply", "waiting"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _snippet(body: str, length: int = 180) -> str:
    compact = " ".join(body.split())
    return compact[:length]


def _row_to_account(row: AccountModel) -> CommunicationAccount:
    return CommunicationAccount.model_validate(row)


def _row_to_thread(row: ThreadModel) -> MessageThread:
    return MessageThread(
        thread_id=row.thread_id,
        business_id=row.business_id,
        account_id=row.account_id,
        provider_thread_id=row.provider_thread_id,
        subject=row.subject,
        participants=row.participants or [],
        unread_count=row.unread_count,
        last_message_at=row.last_message_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _row_to_message(row: MessageModel) -> Message:
    return Message(
        message_id=row.message_id,
        business_id=row.business_id,
        account_id=row.account_id,
        thread_id=row.thread_id,
        provider_message_id=row.provider_message_id,
        provider_thread_id=row.provider_thread_id,
        direction=row.direction,
        status=row.status,
        sender=row.sender,
        recipients=row.recipients or [],
        cc=row.cc or [],
        bcc=row.bcc or [],
        subject=row.subject,
        body=row.body,
        snippet=row.snippet,
        labels=row.labels or [],
        is_read=bool(row.is_read),
        sent_at=row.sent_at,
        received_at=row.received_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _row_to_history(row: HistoryModel) -> CommunicationHistory:
    return CommunicationHistory.model_validate(row)


def _history(
    *,
    business_id: str,
    account_id: str | None,
    message_id: str | None,
    action: str,
    status: str,
    detail: str,
    payload: dict,
) -> HistoryModel:
    return HistoryModel(
        history_id=str(uuid4()),
        business_id=business_id,
        account_id=account_id,
        message_id=message_id,
        action=action,
        status=status,
        detail=detail,
        payload=payload,
        created_at=_now(),
    )


def create_account(data: CommunicationAccountCreate | dict) -> CommunicationAccount:
    validated = CommunicationAccountCreate.model_validate(data)
    business = resolve_business(
        business_id=validated.business_id,
        business_name=validated.business_name,
        text=f"{validated.account_name} {validated.email}",
    )
    now = _now()
    with SessionLocal() as session:
        existing = (
            session.query(AccountModel)
            .filter(
                AccountModel.business_id == business.business_id,
                AccountModel.provider == validated.provider,
                AccountModel.email == validated.email.strip().lower(),
            )
            .one_or_none()
        )
        if existing is not None:
            existing.account_name = validated.account_name.strip()
            existing.status = validated.status.strip()
            existing.updated_at = now
            session.commit()
            session.refresh(existing)
            return _row_to_account(existing)

        row = AccountModel(
            account_id=str(uuid4()),
            business_id=business.business_id,
            provider=validated.provider,
            account_name=validated.account_name.strip(),
            email=validated.email.strip().lower(),
            status=validated.status.strip(),
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.add(
            _history(
                business_id=business.business_id,
                account_id=row.account_id,
                message_id=None,
                action="account_configured",
                status="succeeded",
                detail=f"{validated.provider} account configured for {business.business_name}.",
                payload={"provider": validated.provider, "email": row.email},
            )
        )
        session.commit()
        session.refresh(row)
        return _row_to_account(row)


def get_accounts(business_id: Optional[str] = None) -> list[CommunicationAccount]:
    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        rows = (
            session.query(AccountModel)
            .filter(AccountModel.business_id == resolved_business_id)
            .order_by(AccountModel.provider, AccountModel.account_name, AccountModel.account_id)
            .all()
        )
        return [_row_to_account(row) for row in rows]


def _get_account(session, account_id: str, business_id: str | None = None) -> AccountModel:
    row = session.get(AccountModel, account_id)
    if row is None:
        raise ValueError("Communication account not found.")
    if business_id is not None and row.business_id != business_id:
        raise ValueError("Communication account does not belong to selected business.")
    return row


def _get_or_create_thread(
    session,
    *,
    business_id: str,
    account_id: str,
    provider_thread_id: str | None,
    subject: str,
    participants: list[str],
    message_time: datetime | None,
    unread_delta: int,
) -> ThreadModel:
    query = session.query(ThreadModel).filter(ThreadModel.business_id == business_id, ThreadModel.account_id == account_id)
    if provider_thread_id:
        query = query.filter(ThreadModel.provider_thread_id == provider_thread_id)
    else:
        query = query.filter(ThreadModel.subject == subject)
    row = query.first()
    now = _now()
    if row is None:
        row = ThreadModel(
            thread_id=str(uuid4()),
            business_id=business_id,
            account_id=account_id,
            provider_thread_id=provider_thread_id,
            subject=subject,
            participants=sorted(set(participants)),
            unread_count=max(0, unread_delta),
            last_message_at=message_time,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        return row
    row.participants = sorted(set((row.participants or []) + participants))
    row.unread_count = max(0, row.unread_count + unread_delta)
    if message_time and (row.last_message_at is None or message_time > row.last_message_at):
        row.last_message_at = message_time
    row.updated_at = now
    return row


def _persist_connector_message(
    session,
    *,
    account: AccountModel,
    connector_message: ConnectorMessage,
    direction: str,
    status: str,
) -> MessageModel:
    message_time = connector_message.received_at or connector_message.sent_at or _now()
    participants = [connector_message.sender] + connector_message.recipients + connector_message.cc + connector_message.bcc
    thread = _get_or_create_thread(
        session,
        business_id=account.business_id,
        account_id=account.account_id,
        provider_thread_id=connector_message.provider_thread_id,
        subject=connector_message.subject,
        participants=participants,
        message_time=message_time,
        unread_delta=1 if direction == "inbound" and not connector_message.is_read else 0,
    )
    row = MessageModel(
        message_id=str(uuid4()),
        business_id=account.business_id,
        account_id=account.account_id,
        thread_id=thread.thread_id,
        provider_message_id=connector_message.provider_message_id,
        provider_thread_id=connector_message.provider_thread_id,
        direction=direction,
        status=status,
        sender=connector_message.sender,
        recipients=connector_message.recipients,
        cc=connector_message.cc,
        bcc=connector_message.bcc,
        subject=connector_message.subject,
        body=connector_message.body,
        snippet=_snippet(connector_message.body),
        labels=connector_message.labels,
        is_read=1 if connector_message.is_read else 0,
        sent_at=connector_message.sent_at,
        received_at=connector_message.received_at,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(row)
    return row


def send_message(request: MessageRequest | dict) -> Message:
    validated = MessageRequest.model_validate(request)
    with SessionLocal() as session:
        account = _get_account(session, validated.account_id, business_id=validated.business_id)
        connector = get_connector(account.provider)
        sent = connector.send_email(
            account.email,
            [str(item) for item in validated.recipients],
            validated.subject.strip(),
            validated.body.strip(),
            cc=[str(item) for item in validated.cc],
            bcc=[str(item) for item in validated.bcc],
        )
        row = _persist_connector_message(session, account=account, connector_message=sent, direction="outbound", status="sent")
        session.add(
            _history(
                business_id=account.business_id,
                account_id=account.account_id,
                message_id=row.message_id,
                action="send_message",
                status="succeeded",
                detail=f"Sent message: {row.subject}",
                payload={"provider": account.provider, "recipients": row.recipients},
            )
        )
        account.last_sync = _now()
        account.updated_at = _now()
        session.commit()
        session.refresh(row)
        return _row_to_message(row)


def create_draft(request: MessageRequest | dict) -> Message:
    validated = MessageRequest.model_validate(request)
    with SessionLocal() as session:
        account = _get_account(session, validated.account_id, business_id=validated.business_id)
        connector = get_connector(account.provider)
        draft = connector.draft_email(
            account.email,
            [str(item) for item in validated.recipients],
            validated.subject.strip(),
            validated.body.strip(),
            cc=[str(item) for item in validated.cc],
            bcc=[str(item) for item in validated.bcc],
        )
        row = _persist_connector_message(session, account=account, connector_message=draft, direction="outbound", status="draft")
        session.add(
            _history(
                business_id=account.business_id,
                account_id=account.account_id,
                message_id=row.message_id,
                action="create_draft",
                status="succeeded",
                detail=f"Created draft: {row.subject}",
                payload={"provider": account.provider, "recipients": row.recipients},
            )
        )
        account.updated_at = _now()
        session.commit()
        session.refresh(row)
        return _row_to_message(row)


def sync_inbox(account_id: str, business_id: str | None = None, limit: int = 25) -> list[Message]:
    with SessionLocal() as session:
        account = _get_account(session, account_id, business_id=business_id)
        connector = get_connector(account.provider)
        imported: list[MessageModel] = []
        for connector_message in connector.read_emails(account.email, limit=limit):
            existing = (
                session.query(MessageModel)
                .filter(
                    MessageModel.account_id == account.account_id,
                    MessageModel.provider_message_id == connector_message.provider_message_id,
                )
                .one_or_none()
            )
            if existing is None:
                imported.append(
                    _persist_connector_message(
                        session,
                        account=account,
                        connector_message=connector_message,
                        direction="inbound",
                        status="received",
                    )
                )
        account.last_sync = _now()
        account.updated_at = _now()
        session.add(
            _history(
                business_id=account.business_id,
                account_id=account.account_id,
                message_id=None,
                action="read_messages",
                status="succeeded",
                detail=f"Read {len(imported)} new messages.",
                payload={"provider": account.provider, "imported_count": len(imported)},
            )
        )
        session.commit()
        return [_row_to_message(row) for row in imported]


def read_messages(
    business_id: Optional[str] = None,
    *,
    account_id: Optional[str] = None,
    status: Optional[str] = None,
    direction: Optional[str] = None,
    limit: int = 50,
) -> list[Message]:
    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        query = session.query(MessageModel).filter(MessageModel.business_id == resolved_business_id)
        if account_id:
            query = query.filter(MessageModel.account_id == account_id)
        if status:
            query = query.filter(MessageModel.status == status)
        if direction:
            query = query.filter(MessageModel.direction == direction)
        rows = (
            query.order_by(MessageModel.created_at.desc(), MessageModel.message_id.desc())
            .limit(min(max(limit, 1), 200))
            .all()
        )
        return [_row_to_message(row) for row in rows]


def search_messages(query: str, business_id: Optional[str] = None, *, limit: int = 50) -> list[Message]:
    resolved_business_id = business_id or get_active_business().business_id
    normalized = query.strip().lower()
    with SessionLocal() as session:
        db_query = session.query(MessageModel).filter(MessageModel.business_id == resolved_business_id)
        if normalized:
            pattern = f"%{normalized}%"
            db_query = db_query.filter(
                or_(
                    MessageModel.subject.ilike(pattern),
                    MessageModel.body.ilike(pattern),
                    MessageModel.sender.ilike(pattern),
                )
            )
        rows = (
            db_query.order_by(MessageModel.created_at.desc(), MessageModel.message_id.desc())
            .limit(min(max(limit, 1), 200))
            .all()
        )
        return [_row_to_message(row) for row in rows]


def get_threads(business_id: Optional[str] = None, *, account_id: Optional[str] = None, limit: int = 50) -> list[MessageThread]:
    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        query = session.query(ThreadModel).filter(ThreadModel.business_id == resolved_business_id)
        if account_id:
            query = query.filter(ThreadModel.account_id == account_id)
        rows = (
            query.order_by(ThreadModel.last_message_at.desc().nullslast(), ThreadModel.updated_at.desc())
            .limit(min(max(limit, 1), 200))
            .all()
        )
        return [_row_to_thread(row) for row in rows]


def get_history(business_id: Optional[str] = None, *, limit: int = 50) -> list[CommunicationHistory]:
    resolved_business_id = business_id or get_active_business().business_id
    with SessionLocal() as session:
        rows = (
            session.query(HistoryModel)
            .filter(HistoryModel.business_id == resolved_business_id)
            .order_by(HistoryModel.created_at.desc(), HistoryModel.history_id.desc())
            .limit(min(max(limit, 1), 200))
            .all()
        )
        return [_row_to_history(row) for row in rows]


def summarize_inbox(business_id: Optional[str] = None) -> InboxSummary:
    messages = read_messages(business_id=business_id, limit=200)
    unread_count = len([message for message in messages if not message.is_read and message.direction == "inbound"])
    inbound = [message for message in messages if message.direction == "inbound"]
    drafts = [message for message in messages if message.status == "draft"]
    sent = [message for message in messages if message.status == "sent"]

    def has_any(message: Message, keywords: set[str]) -> bool:
        text = f"{message.subject} {message.body}".lower()
        return any(keyword in text for keyword in keywords)

    risks = [message.subject for message in inbound if has_any(message, RISK_KEYWORDS)][:5]
    opportunities = [message.subject for message in inbound + sent if has_any(message, OPPORTUNITY_KEYWORDS)][:5]
    followups = [message.subject for message in inbound + sent if has_any(message, FOLLOWUP_KEYWORDS)][:5]
    return InboxSummary(
        unread_count=unread_count,
        inbound_count=len(inbound),
        draft_count=len(drafts),
        sent_count=len(sent),
        risks=risks,
        opportunities=opportunities,
        followups=followups,
    )

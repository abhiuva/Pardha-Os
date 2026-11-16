from __future__ import annotations

from app.business.schemas import BusinessContext
from app.business.service import get_business
from app.db import SessionLocal
from app.db.models import (
    AgentCollaboration,
    AgentExecution,
    CommunicationAccount,
    Message,
    MessageThread,
    WhatsAppAccount,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppTemplate,
    CommunicationHistory,
    Event,
    Knowledge,
    Memory,
    Objective,
    Project,
    Task,
)


def build_business_context(business_id: str) -> BusinessContext:
    business = get_business(business_id)
    if business is None:
        raise ValueError(f"Unknown business_id: {business_id}")
    with SessionLocal() as session:
        counts = {
            "knowledge": session.query(Knowledge).filter(Knowledge.business_id == business_id).count(),
            "objectives": session.query(Objective).filter(Objective.business_id == business_id).count(),
            "tasks": session.query(Task).filter(Task.business_id == business_id).count(),
            "events": session.query(Event).filter(Event.business_id == business_id).count(),
            "memories": session.query(Memory).filter(Memory.business_id == business_id).count(),
            "projects": session.query(Project).filter(Project.business_id == business_id).count(),
            "collaborations": session.query(AgentCollaboration).filter(AgentCollaboration.business_id == business_id).count(),
            "executions": session.query(AgentExecution).filter(AgentExecution.business_id == business_id).count(),
            "communication_accounts": session.query(CommunicationAccount).filter(CommunicationAccount.business_id == business_id).count(),
            "messages": session.query(Message).filter(Message.business_id == business_id).count(),
            "message_threads": session.query(MessageThread).filter(MessageThread.business_id == business_id).count(),
            "communication_history": session.query(CommunicationHistory).filter(CommunicationHistory.business_id == business_id).count(),
            "whatsapp_accounts": session.query(WhatsAppAccount).filter(WhatsAppAccount.business_id == business_id).count(),
            "whatsapp_messages": session.query(WhatsAppMessage).filter(WhatsAppMessage.business_id == business_id).count(),
            "whatsapp_conversations": session.query(WhatsAppConversation).filter(WhatsAppConversation.business_id == business_id).count(),
            "whatsapp_templates": session.query(WhatsAppTemplate).filter(WhatsAppTemplate.business_id == business_id).count(),
        }
        latest_event = (
            session.query(Event)
            .filter(Event.business_id == business_id)
            .order_by(Event.timestamp.desc())
            .first()
        )
        latest_objective = (
            session.query(Objective)
            .filter(Objective.business_id == business_id)
            .order_by(Objective.created_at.desc())
            .first()
        )
    return BusinessContext(
        active_business=business,
        counts=counts,
        recent={
            "latest_event": latest_event.event_type if latest_event is not None else None,
            "latest_objective": latest_objective.title if latest_objective is not None else None,
        },
    )

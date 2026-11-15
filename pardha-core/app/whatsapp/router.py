from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

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
from app.whatsapp.service import (
    create_account,
    create_template,
    get_accounts,
    get_conversation,
    get_conversations,
    get_messages,
    get_templates,
    receive_message,
    send_message,
    send_template,
    summarize_whatsapp,
)


router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("/accounts", response_model=WhatsAppAccount, status_code=status.HTTP_201_CREATED)
def create_account_route(account: WhatsAppAccountCreate):
    return create_account(account)


@router.get("/accounts", response_model=list[WhatsAppAccount])
def get_accounts_route(business_id: Optional[str] = Query(default=None)):
    return get_accounts(business_id=business_id)


@router.post("/send", response_model=WhatsAppMessage)
def send_message_route(message: WhatsAppSendRequest):
    try:
        return send_message(message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/template", response_model=WhatsAppMessage)
def send_template_route(message: WhatsAppTemplateRequest):
    try:
        return send_template(message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/receive", response_model=WhatsAppMessage)
def receive_message_route(message: WhatsAppReceiveRequest):
    try:
        return receive_message(message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/templates", response_model=WhatsAppTemplate, status_code=status.HTTP_201_CREATED)
def create_template_route(template: WhatsAppTemplateCreate):
    try:
        return create_template(template)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/templates", response_model=list[WhatsAppTemplate])
def get_templates_route(business_id: Optional[str] = Query(default=None)):
    return get_templates(business_id=business_id)


@router.get("/messages", response_model=list[WhatsAppMessage])
def get_messages_route(
    business_id: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    conversation_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50),
):
    return get_messages(
        business_id=business_id,
        account_id=account_id,
        conversation_id=conversation_id,
        limit=limit,
    )


@router.get("/conversations", response_model=list[WhatsAppConversation])
def get_conversations_route(
    business_id: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50),
):
    return get_conversations(business_id=business_id, account_id=account_id, status=status, limit=limit)


@router.get("/conversations/{conversation_id}", response_model=list[WhatsAppMessage])
def get_conversation_route(conversation_id: str, business_id: Optional[str] = Query(default=None)):
    return get_conversation(conversation_id, business_id=business_id)


@router.get("/summary", response_model=WhatsAppSummary)
def get_summary_route(business_id: Optional[str] = Query(default=None)):
    return summarize_whatsapp(business_id=business_id)

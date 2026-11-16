from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.communications.schemas import (
    CommunicationAccount,
    CommunicationAccountCreate,
    CommunicationHistory,
    InboxSummary,
    Message,
    MessageRequest,
    MessageThread,
)
from app.communications.service import (
    create_account,
    create_draft,
    get_accounts,
    get_history,
    get_threads,
    read_messages,
    search_messages,
    send_message,
    summarize_inbox,
    sync_inbox,
)


router = APIRouter(prefix="/communications", tags=["communications"])


@router.post("/accounts", response_model=CommunicationAccount, status_code=status.HTTP_201_CREATED)
def create_account_route(account: CommunicationAccountCreate):
    return create_account(account)


@router.get("/accounts", response_model=list[CommunicationAccount])
def get_accounts_route(business_id: Optional[str] = Query(default=None)):
    return get_accounts(business_id=business_id)


@router.post("/send", response_model=Message)
def send_message_route(message: MessageRequest):
    try:
        return send_message(message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/draft", response_model=Message)
def create_draft_route(message: MessageRequest):
    try:
        return create_draft(message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/accounts/{account_id}/sync", response_model=list[Message])
def sync_account_route(account_id: str, business_id: Optional[str] = Query(default=None), limit: int = Query(default=25)):
    try:
        return sync_inbox(account_id, business_id=business_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/messages", response_model=list[Message])
def get_messages_route(
    business_id: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    direction: Optional[str] = Query(default=None),
    limit: int = Query(default=50),
):
    return read_messages(
        business_id=business_id,
        account_id=account_id,
        status=status,
        direction=direction,
        limit=limit,
    )


@router.get("/messages/search", response_model=list[Message])
def search_messages_route(
    query: str = Query(default=""),
    business_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50),
):
    return search_messages(query=query, business_id=business_id, limit=limit)


@router.get("/threads", response_model=list[MessageThread])
def get_threads_route(
    business_id: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50),
):
    return get_threads(business_id=business_id, account_id=account_id, limit=limit)


@router.get("/history", response_model=list[CommunicationHistory])
def get_history_route(business_id: Optional[str] = Query(default=None), limit: int = Query(default=50)):
    return get_history(business_id=business_id, limit=limit)


@router.get("/summary", response_model=InboxSummary)
def get_summary_route(business_id: Optional[str] = Query(default=None)):
    return summarize_inbox(business_id=business_id)

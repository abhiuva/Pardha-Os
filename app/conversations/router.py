from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.conversations.schemas import (
    ConversationCreate,
    ConversationDeleteResult,
    ConversationDetail,
    ConversationEngineStatus,
    ConversationExport,
    ConversationHardeningValidationReport,
    ConversationMessageRequest,
    ConversationMessageResponse,
    ExecutiveRoutingValidationReport,
    ConversationSession,
    ConversationUpdate,
    ConversationValidationReport,
    VoiceRuntimeValidationReport,
)
from app.conversations.service import (
    conversation_hardening_validation,
    conversation_engine_status,
    executive_routing_validation,
    conversation_validation,
    create_conversation,
    delete_conversation,
    export_conversation,
    get_conversation,
    list_conversations,
    restore_conversation,
    send_message,
    stream_events,
    update_conversation,
    voice_runtime_validation,
)

router = APIRouter(prefix="/conversations", tags=["conversational-intelligence"])


@router.post("", response_model=ConversationSession, status_code=status.HTTP_201_CREATED)
def create_conversation_route(request: ConversationCreate):
    return create_conversation(request)


@router.get("", response_model=list[ConversationSession])
def list_conversations_route(
    business_id: str | None = Query(default=None),
    search: str = Query(default=""),
    include_archived: bool = Query(default=False),
):
    return list_conversations(business_id=business_id, search=search, include_archived=include_archived)


@router.get("/status", response_model=ConversationEngineStatus)
def conversation_status_route():
    return conversation_engine_status()


@router.get("/validation", response_model=ConversationValidationReport)
def conversation_validation_route():
    return conversation_validation()


@router.get("/hardening-validation", response_model=ConversationHardeningValidationReport)
def conversation_hardening_validation_route():
    return conversation_hardening_validation()


@router.get("/routing-validation", response_model=ExecutiveRoutingValidationReport)
def executive_routing_validation_route():
    return executive_routing_validation()


@router.get("/voice-validation", response_model=VoiceRuntimeValidationReport)
def voice_runtime_validation_route():
    return voice_runtime_validation()


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation_route(conversation_id: str):
    detail = get_conversation(conversation_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return detail


@router.patch("/{conversation_id}", response_model=ConversationSession)
def update_conversation_route(conversation_id: str, request: ConversationUpdate):
    conversation = update_conversation(conversation_id, request)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return conversation


@router.delete("/{conversation_id}", response_model=ConversationDeleteResult)
def delete_conversation_route(conversation_id: str):
    result = delete_conversation(conversation_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return result


@router.post("/{conversation_id}/restore", response_model=ConversationSession)
def restore_conversation_route(conversation_id: str):
    conversation = restore_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return conversation


@router.get("/{conversation_id}/export", response_model=ConversationExport)
def export_conversation_route(conversation_id: str):
    exported = export_conversation(conversation_id)
    if exported is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return exported


@router.post("/{conversation_id}/messages", response_model=ConversationMessageResponse, status_code=status.HTTP_201_CREATED)
def send_conversation_message_route(conversation_id: str, request: ConversationMessageRequest):
    try:
        return send_message(conversation_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/messages", response_model=ConversationMessageResponse, status_code=status.HTTP_201_CREATED)
def send_new_conversation_message_route(request: ConversationMessageRequest):
    return send_message(None, request)


@router.post("/{conversation_id}/stream")
def stream_conversation_message_route(conversation_id: str, request: ConversationMessageRequest):
    return StreamingResponse(_event_stream(conversation_id, request), media_type="application/x-ndjson")


@router.post("/stream")
def stream_new_conversation_message_route(request: ConversationMessageRequest):
    return StreamingResponse(_event_stream(None, request), media_type="application/x-ndjson")


def _event_stream(conversation_id: str | None, request: ConversationMessageRequest):
    for event in stream_events(conversation_id, request):
        yield json.dumps(event) + "\n"

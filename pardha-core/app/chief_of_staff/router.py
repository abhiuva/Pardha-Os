from fastapi import APIRouter, Query, status

from app.chief_of_staff.schemas import (
    ChatRequest,
    ChatResponse,
    ChiefMessage,
    ConversationSummary,
    ExecutiveCommandCenter,
    FounderGoal,
    GoalCreate,
    HelpResponse,
)
from app.chief_of_staff.service import (
    create_goal,
    executive_command_center,
    get_conversation,
    help_answer,
    list_conversations,
    list_goals,
    send_chat,
)

router = APIRouter(prefix="/chief", tags=["chief-of-staff"])


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def chat_route(request: ChatRequest):
    return send_chat(request)


@router.get("/conversations", response_model=list[ConversationSummary])
def conversations_route(business_id: str | None = Query(default=None), business_name: str | None = Query(default=None)):
    return list_conversations(business_id=business_id, business_name=business_name)


@router.get("/conversations/{conversation_id}", response_model=list[ChiefMessage])
def conversation_route(conversation_id: str, business_id: str | None = Query(default=None)):
    return get_conversation(conversation_id=conversation_id, business_id=business_id)


@router.post("/goals", response_model=FounderGoal, status_code=status.HTTP_201_CREATED)
def create_goal_route(request: GoalCreate):
    return create_goal(request)


@router.get("/goals", response_model=list[FounderGoal])
def goals_route(business_id: str | None = Query(default=None), business_name: str | None = Query(default=None)):
    return list_goals(business_id=business_id, business_name=business_name)


@router.get("/executive-command", response_model=ExecutiveCommandCenter)
def executive_command_route(business_id: str | None = Query(default=None), business_name: str | None = Query(default=None)):
    return executive_command_center(business_id=business_id, business_name=business_name)


@router.get("/help", response_model=HelpResponse)
def help_route(question: str = Query(default="")):
    return help_answer(question)

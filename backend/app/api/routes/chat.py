from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.conversation import Conversation, Message, MessageRole
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    ConversationListItem,
)
from app.services.audit import log_action
from app.agents.orchestrator import Orchestrator

router = APIRouter(prefix="/chat", tags=["Chat"])

orchestrator = Orchestrator()


@router.post("/", response_model=ChatResponse)
async def send_message(
    data: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Get or create conversation
    if data.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == data.conversation_id,
                Conversation.user_id == current_user.id,
            )
            .first()
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
    else:
        conversation = Conversation(
            user_id=current_user.id,
            title=data.message[:80],
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=data.message,
    )
    db.add(user_msg)
    db.commit()

    # Get conversation history for context
    history = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
        .all()
    )

    # Process through orchestrator
    result = await orchestrator.process(
        message=data.message,
        user=current_user,
        history=[(m.role.value, m.content) for m in history[:-1]],  # exclude last
    )

    # Save assistant response
    assistant_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=result["response"],
        agent_used=result.get("agent_used"),
    )
    db.add(assistant_msg)
    db.commit()

    # Audit log
    log_action(
        db,
        user_id=current_user.id,
        action="chat_query",
        resource="chat",
        detail=f"Consulta: {data.message[:200]}",
        agent_used=result.get("agent_used"),
        ip_address=request.client.host if request.client else None,
    )

    return ChatResponse(
        message=result["response"],
        conversation_id=conversation.id,
        agent_used=result.get("agent_used"),
        metadata=result.get("metadata"),
    )


@router.get("/conversations", response_model=list[ConversationListItem])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
        .all()
    )

    result = []
    for conv in conversations:
        count = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .count()
        )
        result.append(
            ConversationListItem(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=count,
            )
        )
    return result


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return conversation


@router.patch("/conversations/{conversation_id}")
def update_conversation(
    conversation_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    if "title" in data:
        conversation.title = data["title"][:200]
        db.commit()

    return {"detail": "Conversación actualizada"}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    db.delete(conversation)
    db.commit()
    return {"detail": "Conversación eliminada"}

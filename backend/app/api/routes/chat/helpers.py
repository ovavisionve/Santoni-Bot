"""Shared conversation helpers used by chat sub-routers."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message, MessageRole


def _get_or_create_conversation(
    db: Session, user_id: int, conversation_id: int | None, title: str
) -> Conversation:
    """Get existing conversation or create a new one."""
    if conversation_id:
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )
        if not conv:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        return conv
    conv = Conversation(user_id=user_id, title=title[:80])
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _get_history(db: Session, conversation_id: int, limit: int = 40) -> list[tuple[str, str]]:
    """Get recent conversation history as (role, content) tuples."""
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit + 1)  # +1 for the user message we just saved
        .all()
    )
    messages.reverse()
    return [(m.role.value, m.content) for m in messages[:-1]] if len(messages) > 1 else []


def _get_last_agent(db: Session, conversation_id: int) -> str | None:
    """Get the agent used in the last bot response for context continuity.

    IMPORTANTE (14/Abr/2026): excluimos "sql_direct" del historial porque
    SQL Directo NO es un agente — es un camino de ejecución paralelo.
    Si una pregunta fue respondida por SQL Directo y el usuario hace un
    follow-up ("dame en dólares"), queremos heredar el agente CLÁSICO
    anterior (ventas, finanzas, etc.) que sí sabe interpretar el contexto
    de moneda.
    """
    last_bot_msg = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == MessageRole.ASSISTANT,
            Message.agent_used.isnot(None),
            Message.agent_used != "general",
            Message.agent_used != "sql_direct",
        )
        .order_by(Message.created_at.desc())
        .first()
    )
    return last_bot_msg.agent_used if last_bot_msg else None

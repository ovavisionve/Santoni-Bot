import json
import logging
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
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
from app.services.cache import (
    get_cached_response,
    set_cached_response,
    get_data_timestamp,
)
from app.middleware.access_control import enforce_access_controls
from app.agents.orchestrator import Orchestrator

logger = logging.getLogger("santonibot.chat")

router = APIRouter(prefix="/chat", tags=["Chat"])

orchestrator = Orchestrator()


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
    # Reverse to chronological, skip the last user message
    messages.reverse()
    return [(m.role.value, m.content) for m in messages[:-1]] if len(messages) > 1 else []


def _get_last_agent(db: Session, conversation_id: int) -> str | None:
    """Get the agent used in the last bot response for context continuity."""
    last_bot_msg = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == MessageRole.ASSISTANT,
            Message.agent_used.isnot(None),
            Message.agent_used != "general",
        )
        .order_by(Message.created_at.desc())
        .first()
    )
    return last_bot_msg.agent_used if last_bot_msg else None


# ──────────────────────────────────────────────────────────────
# Streaming endpoint (SSE) — primary, fast
# ──────────────────────────────────────────────────────────────

@router.post("/stream")
async def stream_message(
    data: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream response tokens via Server-Sent Events (SSE)."""

    # Access control: business hours + network
    enforce_access_controls(request, current_user.role.value)

    # Cannot stream document analysis (needs special handling)
    if data.file_id:
        return await send_message(data, request, current_user, db)

    conversation = _get_or_create_conversation(
        db, current_user.id, data.conversation_id, data.message
    )

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=data.message,
    )
    db.add(user_msg)
    db.commit()

    history = _get_history(db, conversation.id)
    last_agent = _get_last_agent(db, conversation.id)
    agent_name, routing_score, match_type = await orchestrator.get_stream_agent_name(data.message, current_user, last_agent=last_agent)

    # Send initial metadata
    conv_id = conversation.id
    user_id = current_user.id
    message_text = data.message
    ip_addr = request.client.host if request.client else None

    # Check cache before streaming
    cached = get_cached_response(message_text, agent_name)
    data_ts = get_data_timestamp()

    async def event_generator():
        full_response = []

        # First event: metadata (conversation_id, agent, timestamp, routing score)
        yield f"data: {json.dumps({'type': 'meta', 'conversation_id': conv_id, 'agent': agent_name, 'timestamp': data_ts, 'routing_score': routing_score})}\n\n"

        # If cached, send the full response as a single token
        if cached:
            full_response.append(cached["response"])
            yield f"data: {json.dumps({'type': 'token', 'content': cached['response']})}\n\n"
        else:
            try:
                async for token in orchestrator.stream(
                    message=message_text,
                    user=current_user,
                    history=history,
                    last_agent=last_agent,
                ):
                    full_response.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            except Exception as exc:
                logger.error("Streaming error: %s: %s", type(exc).__name__, exc, exc_info=True)
                error_msg = f"Error al consultar el modelo de IA: {type(exc).__name__}"
                yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
                full_response.append(error_msg)

        # Save to cache (only non-cached, non-error responses)
        complete_text = "".join(full_response)
        if not cached and "Error al consultar" not in complete_text:
            set_cached_response(message_text, agent_name, complete_text, agent_name)

        # Save complete response to DB
        try:
            save_db = SessionLocal()
            try:
                # Compute confidence score for streamed response
                from app.agents.orchestrator import compute_confidence_score
                has_data = bool(complete_text) and "Error al consultar" not in complete_text
                conf_score, score_breakdown = compute_confidence_score(
                    routing_score, has_data, agent_name,
                )
                score_breakdown["match_type"] = match_type
                meta_dict = {
                    "confidence_score": conf_score,
                    "score_breakdown": score_breakdown,
                    "match_type": match_type,
                }
                assistant_msg = Message(
                    conversation_id=conv_id,
                    role=MessageRole.ASSISTANT,
                    content=complete_text,
                    agent_used=agent_name,
                    confidence_score=conf_score,
                    metadata_json=json.dumps(meta_dict),
                )
                save_db.add(assistant_msg)
                save_db.commit()
                save_db.refresh(assistant_msg)
                msg_id = assistant_msg.id

                log_action(
                    save_db,
                    user_id=user_id,
                    action="chat_query",
                    resource="chat",
                    detail=f"Consulta: {message_text}",
                    agent_used=agent_name,
                    ip_address=ip_addr,
                )
            finally:
                save_db.close()
        except Exception as save_exc:
            logger.error("Error saving streamed response: %s", save_exc)
            msg_id = 0

        # Final event: done signal with message_id
        yield f"data: {json.dumps({'type': 'done', 'message_id': msg_id, 'conversation_id': conv_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


# ──────────────────────────────────────────────────────────────
# Non-streaming endpoint (fallback, document analysis)
# ──────────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponse)
async def send_message(
    data: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Access control: business hours + network
    enforce_access_controls(request, current_user.role.value)

    conversation = _get_or_create_conversation(
        db, current_user.id, data.conversation_id, data.message
    )

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=data.message,
    )
    db.add(user_msg)
    db.commit()

    history = _get_history(db, conversation.id)
    last_agent = _get_last_agent(db, conversation.id)

    # Read attached document if present
    document = None
    if data.file_id:
        from app.services.document_service import read_document
        document = read_document(data.file_id)
        if document:
            logger.info("Document attached: %s (%s)", document.get("filename"), document["type"])

    try:
        result = await orchestrator.process(
            message=data.message,
            user=current_user,
            history=history,
            document=document,
            last_agent=last_agent,
        )
    except Exception as exc:
        logger.error(
            "Error processing chat message: %s: %s",
            type(exc).__name__, exc, exc_info=True,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Error al consultar el modelo de IA: {type(exc).__name__}: {exc}",
        )

    # Save assistant response with confidence score
    conf_score = result.get("confidence_score")
    score_breakdown = result.get("score_breakdown")
    metadata = result.get("metadata") or {}
    meta_dict = {
        "confidence_score": conf_score,
        "score_breakdown": score_breakdown,
        **metadata,
    }
    assistant_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=result["response"],
        agent_used=result.get("agent_used"),
        confidence_score=conf_score,
        metadata_json=json.dumps(meta_dict) if meta_dict else None,
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    action = "access_denied" if (metadata.get("classification") == "no_access" or metadata.get("access_denied")) else "chat_query"
    log_action(
        db,
        user_id=current_user.id,
        action=action,
        resource="chat",
        detail=f"{'ACCESO DENEGADO - ' if action == 'access_denied' else ''}Consulta: {data.message}",
        agent_used=result.get("agent_used"),
        ip_address=request.client.host if request.client else None,
    )

    return ChatResponse(
        message=result["response"],
        message_id=assistant_msg.id,
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


# ──────────────────────────────────────────────────────────────
# Export endpoints — user downloads their own conversations
# ──────────────────────────────────────────────────────────────

def _build_conversation_txt(
    conv: Conversation,
    messages: list[Message],
    user: User,
) -> str:
    """Build plain-text export for a single conversation."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"CONVERSACIÓN: {conv.title}")
    lines.append(f"Usuario: {user.full_name} (@{user.username})")
    created = conv.created_at.strftime("%d/%m/%Y %H:%M") if conv.created_at else "?"
    lines.append(f"Fecha: {created}")
    lines.append(f"Mensajes: {len(messages)}")
    lines.append("=" * 70)
    lines.append("")

    for m in messages:
        ts = m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else ""
        role_label = "USUARIO" if m.role.value == "user" else f"BOT [{m.agent_used or 'general'}]"
        lines.append(f"[{ts}] {role_label}:")
        lines.append(m.content)
        lines.append("")

    return "\n".join(lines)


def _build_conversation_pdf(
    conv: Conversation,
    messages: list[Message],
    user: User,
) -> BytesIO:
    """Build PDF export for a single conversation using ReportLab."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=20 * mm, rightMargin=20 * mm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ConvTitle", parent=styles["Heading1"],
        fontSize=14, textColor=HexColor("#042387"),
    )
    meta_style = ParagraphStyle(
        "Meta", parent=styles["Normal"],
        fontSize=9, textColor=HexColor("#888888"),
    )
    user_style = ParagraphStyle(
        "UserMsg", parent=styles["Normal"],
        fontSize=9, leftIndent=10, textColor=HexColor("#333333"), spaceAfter=4,
    )
    bot_style = ParagraphStyle(
        "BotMsg", parent=styles["Normal"],
        fontSize=9, leftIndent=10, textColor=HexColor("#042387"), spaceAfter=4,
    )

    story = []
    story.append(Paragraph("ALIMENTOS SANTONI, C.A.", title_style))
    created = conv.created_at.strftime("%d/%m/%Y %H:%M") if conv.created_at else "?"
    story.append(Paragraph(f"{conv.title} — {created}", meta_style))
    story.append(Paragraph(
        f"Usuario: {user.full_name} (@{user.username}) | "
        f"Exportado: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
        meta_style,
    ))
    story.append(Spacer(1, 12))

    for m in messages:
        ts = m.created_at.strftime("%H:%M") if m.created_at else ""
        content = (m.content or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if len(content) > 3000:
            content = content[:3000] + "... [truncado]"
        content = content.replace("\n", "<br/>")
        if m.role.value == "user":
            story.append(Paragraph(f"<b>[{ts}] USUARIO:</b><br/>{content}", user_style))
        else:
            agent = m.agent_used or "general"
            story.append(Paragraph(f"<b>[{ts}] BOT [{agent}]:</b><br/>{content}", bot_style))

    doc.build(story)
    buf.seek(0)
    return buf


@router.get("/conversations/{conversation_id}/export")
def export_conversation(
    conversation_id: int,
    format: str = Query("txt", pattern="^(txt|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a single conversation as TXT or PDF (user downloads their own)."""
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

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
        .all()
    )

    filename_base = f"conversacion_{conversation.id}_{datetime.now().strftime('%Y%m%d')}"

    if format == "txt":
        full_text = _build_conversation_txt(conversation, messages, current_user)
        buf = BytesIO(full_text.encode("utf-8"))
        return StreamingResponse(
            buf,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.txt"'},
        )

    # PDF format
    try:
        buf = _build_conversation_pdf(conversation, messages, current_user)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
        )
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="ReportLab no instalado. Usa formato TXT.",
        )


@router.get("/conversations/export-all")
def export_all_conversations(
    format: str = Query("txt", pattern="^(txt|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export ALL conversations of the current user as TXT or PDF."""
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at)
        .all()
    )

    filename_base = f"conversaciones_{current_user.username}_{datetime.now().strftime('%Y%m%d')}"

    if format == "txt":
        lines: list[str] = []
        lines.append("=" * 70)
        lines.append(f"HISTORIAL DE CONVERSACIONES - {current_user.full_name} (@{current_user.username})")
        lines.append(f"Exportado: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}")
        lines.append(f"Total conversaciones: {len(conversations)}")
        lines.append("=" * 70)
        lines.append("")

        for conv in conversations:
            msgs = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at)
                .all()
            )
            created = conv.created_at.strftime("%d/%m/%Y %H:%M") if conv.created_at else "?"
            lines.append(f"--- Conversación: {conv.title} ({created}) ---")
            lines.append("")
            for m in msgs:
                ts = m.created_at.strftime("%H:%M") if m.created_at else ""
                role_label = "USUARIO" if m.role.value == "user" else f"BOT [{m.agent_used or 'general'}]"
                lines.append(f"[{ts}] {role_label}:")
                lines.append(m.content)
                lines.append("")
            lines.append("")

        full_text = "\n".join(lines)
        buf = BytesIO(full_text.encode("utf-8"))
        return StreamingResponse(
            buf,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.txt"'},
        )

    # PDF format
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=20 * mm, rightMargin=20 * mm)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "ConvTitle", parent=styles["Heading1"],
            fontSize=14, textColor=HexColor("#042387"),
        )
        header_style = ParagraphStyle(
            "ConvHeader", parent=styles["Heading2"],
            fontSize=11, textColor=HexColor("#E06400"), spaceAfter=6,
        )
        user_style = ParagraphStyle(
            "UserMsg", parent=styles["Normal"],
            fontSize=9, leftIndent=10, textColor=HexColor("#333333"), spaceAfter=4,
        )
        bot_style = ParagraphStyle(
            "BotMsg", parent=styles["Normal"],
            fontSize=9, leftIndent=10, textColor=HexColor("#042387"), spaceAfter=4,
        )
        meta_style = ParagraphStyle(
            "Meta", parent=styles["Normal"],
            fontSize=8, textColor=HexColor("#888888"),
        )

        story = []
        story.append(Paragraph("ALIMENTOS SANTONI, C.A.", title_style))
        story.append(Paragraph(
            f"Historial de conversaciones - {current_user.full_name} (@{current_user.username})",
            meta_style,
        ))
        story.append(Paragraph(
            f"Exportado: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')} | "
            f"Total: {len(conversations)} conversaciones",
            meta_style,
        ))
        story.append(Spacer(1, 12))

        for conv in conversations:
            msgs = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at)
                .all()
            )
            created = conv.created_at.strftime("%d/%m/%Y %H:%M") if conv.created_at else "?"
            story.append(Paragraph(f"{conv.title} ({created})", header_style))
            for m in msgs:
                ts = m.created_at.strftime("%H:%M") if m.created_at else ""
                content = (m.content or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                if len(content) > 2000:
                    content = content[:2000] + "... [truncado]"
                content = content.replace("\n", "<br/>")
                if m.role.value == "user":
                    story.append(Paragraph(f"<b>[{ts}] USUARIO:</b><br/>{content}", user_style))
                else:
                    agent = m.agent_used or "general"
                    story.append(Paragraph(f"<b>[{ts}] BOT [{agent}]:</b><br/>{content}", bot_style))
            story.append(Spacer(1, 10))

        doc.build(story)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.pdf"'},
        )
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="ReportLab no instalado. Usa formato TXT.",
        )

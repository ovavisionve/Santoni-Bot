"""Export single / all conversations as TXT or PDF."""

from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.conversation import Conversation, Message


router = APIRouter()


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


def _build_all_conversations_pdf(
    conversations: list[Conversation],
    user: User,
    db: Session,
) -> BytesIO:
    """Build PDF export of every conversation for a user."""
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
        f"Historial de conversaciones - {user.full_name} (@{user.username})",
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
    return buf


def _build_all_conversations_txt(
    conversations: list[Conversation],
    user: User,
    db: Session,
) -> str:
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"HISTORIAL DE CONVERSACIONES - {user.full_name} (@{user.username})")
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

    return "\n".join(lines)


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
        full_text = _build_all_conversations_txt(conversations, current_user, db)
        buf = BytesIO(full_text.encode("utf-8"))
        return StreamingResponse(
            buf,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.txt"'},
        )

    try:
        buf = _build_all_conversations_pdf(conversations, current_user, db)
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

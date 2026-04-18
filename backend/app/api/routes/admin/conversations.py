"""Admin endpoints: user conversations listing and export."""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Float, text

from app.database import get_db
from app.middleware.auth import require_admin, require_supervisor_or_admin
from app.models.user import User
from app.services.audit import log_action
import json
from datetime import datetime, timezone
from io import BytesIO
from fastapi.responses import StreamingResponse
from app.models.conversation import Conversation, Message

router = APIRouter(prefix="/admin", tags=["Administración"])

@router.get("/users/{user_id}/conversations")
def get_user_conversations(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all conversations for a user (admin audit view)."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    result = []
    for conv in conversations:
        msgs = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
            .all()
        )
        result.append({
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "message_count": len(msgs),
            "messages": [
                {
                    "role": m.role.value,
                    "content": m.content,
                    "agent_used": m.agent_used,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in msgs
            ],
        })

    return {
        "user": {
            "id": target.id,
            "username": target.username,
            "full_name": target.full_name,
            "department": target.department.value if target.department else None,
        },
        "conversations": result,
        "total": len(result),
    }


@router.get("/users/{user_id}/conversations/export")
def export_user_conversations(
    user_id: int,
    format: str = Query("txt", regex="^(txt|pdf)$"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Export all conversations for a user as TXT or PDF (admin audit)."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at)
        .all()
    )

    # Build conversation text
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"HISTORIAL DE CONVERSACIONES - {target.full_name} (@{target.username})")
    lines.append(f"Departamento: {target.department.value if target.department else 'N/A'}")
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
    filename_base = f"conversaciones_{target.username}_{datetime.now().strftime('%Y%m%d')}"

    if format == "txt":
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
            f"Historial de conversaciones - {target.full_name} (@{target.username})",
            meta_style,
        ))
        story.append(Paragraph(
            f"Departamento: {target.department.value if target.department else 'N/A'} | "
            f"Exportado: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
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
                # Escape HTML special chars for ReportLab
                content = (m.content or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                # Truncate very long messages for PDF readability
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


# ──────────────────────────────────────────────────────────────
# Confidence Score Report
# ──────────────────────────────────────────────────────────────


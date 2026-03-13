from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.conversation import Message
from app.services.export_service import export_to_csv, export_to_excel, export_to_pdf, export_to_docx

router = APIRouter(prefix="/export", tags=["Exportación"])


@router.get("/message/{message_id}")
def export_message(
    message_id: int,
    format: str = Query(..., pattern="^(csv|excel|pdf|docx)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a specific assistant message in CSV, Excel, or PDF format."""
    message = (
        db.query(Message)
        .filter(Message.id == message_id)
        .first()
    )
    if not message:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")

    # Verify ownership through conversation
    from app.models.conversation import Conversation

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == message.conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=403, detail="No autorizado")

    content = message.content
    agent = message.agent_used

    if format == "csv":
        data = export_to_csv(content, agent)
        return Response(
            content=data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="santonibot_reporte.csv"'
            },
        )
    elif format == "excel":
        data = export_to_excel(content, agent)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="santonibot_reporte.xlsx"'
            },
        )
    elif format == "pdf":
        data = export_to_pdf(content, agent)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="santonibot_reporte.pdf"'
            },
        )
    elif format == "docx":
        data = export_to_docx(content, agent)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="santonibot_reporte.docx"'
            },
        )

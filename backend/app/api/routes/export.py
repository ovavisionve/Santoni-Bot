import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.conversation import Message
from app.services.export_service import export_to_csv, export_to_excel, export_to_pdf, export_to_docx

logger = logging.getLogger("santonibot.export")

router = APIRouter(prefix="/export", tags=["Exportación"])

_FORMAT_CONFIG = {
    "csv": {
        "fn": export_to_csv,
        "media": "text/csv",
        "ext": "csv",
    },
    "excel": {
        "fn": export_to_excel,
        "media": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ext": "xlsx",
    },
    "pdf": {
        "fn": export_to_pdf,
        "media": "application/pdf",
        "ext": "pdf",
    },
    "docx": {
        "fn": export_to_docx,
        "media": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "ext": "docx",
    },
}


@router.get("/message/{message_id}")
def export_message(
    message_id: int,
    format: str = Query(..., pattern="^(csv|excel|pdf|docx)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a specific assistant message in CSV, Excel, PDF, or Word format."""
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

    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="El mensaje no tiene contenido para exportar")

    cfg = _FORMAT_CONFIG.get(format)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"Formato no soportado: {format}")

    try:
        data = cfg["fn"](content, agent)
    except Exception as exc:
        logger.error(
            "Error generando export %s para mensaje %d: %s: %s",
            format, message_id, type(exc).__name__, exc, exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar el archivo {format}: {type(exc).__name__}",
        )

    return Response(
        content=data,
        media_type=cfg["media"],
        headers={
            "Content-Disposition": f'attachment; filename="santonibot_reporte.{cfg["ext"]}"'
        },
    )

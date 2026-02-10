"""
Document upload endpoint for attaching files to chat queries.

Currently a placeholder that stores documents temporarily.
When Claude API is enabled (AI_PROVIDER=anthropic), documents will be
sent alongside the user's message for analysis (PDF, Excel, images, etc.)

With Groq (Llama), only text extraction is supported as a fallback.
"""

import os
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.config import get_settings

logger = logging.getLogger("santonibot.documents")

router = APIRouter(prefix="/documents", tags=["Documentos"])

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".csv", ".txt", ".doc", ".docx",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
}

UPLOAD_DIR = "/tmp/santonibot_uploads"


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a document for use in the next chat query.

    Supported formats: PDF, Excel, CSV, TXT, Word, images (PNG, JPG)
    Max size: 10MB

    Note: Full document analysis requires Claude API (AI_PROVIDER=anthropic).
    With Groq, only basic text extraction is available.
    """
    settings = get_settings()

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: {ext}. Formatos permitidos: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Archivo muy grande ({len(content) / 1024 / 1024:.1f}MB). Máximo: 10MB",
        )

    # Store temporarily
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{current_user.id}_{timestamp}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(
        "Document uploaded: %s (%d bytes) by user %s",
        file.filename,
        len(content),
        current_user.username,
    )

    # Determine capabilities based on provider
    can_analyze = settings.ai_provider == "anthropic" and settings.anthropic_api_key

    return {
        "file_id": safe_name,
        "filename": file.filename,
        "size": len(content),
        "extension": ext,
        "can_analyze_full": can_analyze,
        "message": (
            "Documento recibido. Puedes hacer tu consulta y el documento será analizado."
            if can_analyze
            else "Documento recibido. Para análisis completo de documentos se requiere Claude API. "
            "Con Groq solo se puede extraer texto básico."
        ),
    }


@router.get("/capabilities")
def get_document_capabilities(
    current_user: User = Depends(get_current_user),
):
    """Return current document analysis capabilities based on AI provider."""
    settings = get_settings()

    return {
        "provider": settings.ai_provider,
        "can_upload": True,
        "can_analyze_documents": settings.ai_provider == "anthropic",
        "can_analyze_images": settings.ai_provider == "anthropic",
        "supported_formats": sorted(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024,
    }

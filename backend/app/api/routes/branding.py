"""Branding & file upload endpoints.

Handles:
- App-wide settings (company name, logo, colors) for self-service customization
- Avatar uploads for users
- Serving uploaded files
"""
import os
import uuid
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.middleware.auth import get_current_user, require_superadmin
from app.models.user import User
from app.models.settings import AppSettings
from app.services.audit import log_action

router = APIRouter(tags=["Personalización"])

UPLOAD_DIR = Path("/app/uploads")
AVATAR_DIR = UPLOAD_DIR / "avatars"
BRANDING_DIR = UPLOAD_DIR / "branding"

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/svg+xml"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Default branding values
DEFAULT_BRANDING = {
    "company_name": "SantoniBot",
    "company_subtitle": "Sistema Inteligente de Análisis",
    "primary_color": "#e86c25",
    "logo_url": "",
    "login_logo_url": "",
}


class BrandingUpdate(BaseModel):
    company_name: str | None = None
    company_subtitle: str | None = None
    primary_color: str | None = None


# ─── Branding Endpoints ────────────────────────────────────────


@router.get("/settings/branding")
def get_branding(db: Session = Depends(get_db)):
    """Public endpoint - returns branding settings for the UI."""
    rows = db.query(AppSettings).filter(
        AppSettings.key.in_(DEFAULT_BRANDING.keys())
    ).all()

    result = dict(DEFAULT_BRANDING)
    for row in rows:
        result[row.key] = row.value

    return result


@router.put("/settings/branding")
def update_branding(
    data: BrandingUpdate,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    """Admin-only: update branding text settings."""
    updated = {}
    for key, value in data.model_dump(exclude_none=True).items():
        setting = db.query(AppSettings).filter(AppSettings.key == key).first()
        if setting:
            setting.value = value
        else:
            db.add(AppSettings(key=key, value=value))
        updated[key] = value

    db.commit()

    log_action(
        db,
        user_id=admin.id,
        action="branding_updated",
        resource="settings",
        detail=f"Campos actualizados: {', '.join(updated.keys())}",
    )

    return {"message": "Configuración actualizada", "updated": updated}


@router.post("/settings/branding/logo")
async def upload_logo(
    file: UploadFile = File(...),
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    """Admin-only: upload company logo."""
    return await _save_branding_image(file, "logo_url", admin, db)


@router.post("/settings/branding/login-logo")
async def upload_login_logo(
    file: UploadFile = File(...),
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    """Admin-only: upload login page logo."""
    return await _save_branding_image(file, "login_logo_url", admin, db)


async def _save_branding_image(
    file: UploadFile,
    setting_key: str,
    admin: User,
    db: Session,
):
    _validate_image(file)

    BRANDING_DIR.mkdir(parents=True, exist_ok=True)
    ext = _get_extension(file.filename or "image.png")
    filename = f"{setting_key}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = BRANDING_DIR / filename

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    url = f"/api/uploads/branding/{filename}"

    setting = db.query(AppSettings).filter(AppSettings.key == setting_key).first()
    if setting:
        # Delete old file
        _delete_old_file(setting.value)
        setting.value = url
    else:
        db.add(AppSettings(key=setting_key, value=url))
    db.commit()

    log_action(
        db,
        user_id=admin.id,
        action="logo_uploaded",
        resource="settings",
        detail=f"{setting_key} actualizado",
    )

    return {"url": url, "message": "Logo actualizado"}


# ─── Avatar Endpoints ──────────────────────────────────────────


@router.post("/auth/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload or update the current user's avatar."""
    _validate_image(file)

    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    ext = _get_extension(file.filename or "avatar.png")
    filename = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = AVATAR_DIR / filename

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Delete old avatar
    if current_user.avatar_url:
        _delete_old_file(current_user.avatar_url)

    url = f"/api/uploads/avatars/{filename}"
    current_user.avatar_url = url
    db.commit()

    return {"url": url, "message": "Avatar actualizado"}


@router.delete("/auth/avatar")
def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove the current user's avatar."""
    if current_user.avatar_url:
        _delete_old_file(current_user.avatar_url)
        current_user.avatar_url = None
        db.commit()
    return {"message": "Avatar eliminado"}


# ─── File Serving ──────────────────────────────────────────────


@router.get("/uploads/{category}/{filename}")
def serve_upload(category: str, filename: str):
    """Serve uploaded files (avatars, branding)."""
    if category not in ("avatars", "branding"):
        raise HTTPException(status_code=404, detail="Not found")

    # Prevent path traversal
    safe_filename = Path(filename).name
    filepath = UPLOAD_DIR / category / safe_filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(filepath)


# ─── Helpers ───────────────────────────────────────────────────


def _validate_image(file: UploadFile):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido. Permitidos: JPEG, PNG, WebP, SVG",
        )
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="El archivo excede el tamaño máximo de 5MB",
        )


def _get_extension(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return ext if ext else ".png"


def _delete_old_file(url: str):
    """Try to delete an old upload by its URL path."""
    if not url or not url.startswith("/api/uploads/"):
        return
    relative = url.replace("/api/uploads/", "")
    filepath = UPLOAD_DIR / relative
    try:
        if filepath.exists():
            filepath.unlink()
    except Exception:
        pass

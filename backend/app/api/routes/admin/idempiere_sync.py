"""Admin endpoints: capabilities, iDempiere users, role sync, bulk import."""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Float, text

from app.database import get_db
from app.middleware.auth import require_admin, require_supervisor_or_admin
from app.models.user import User
from app.services.audit import log_action
from app.database import IdempiereSession
from app.services.idempiere_role_sync import (
    sync_user_permissions,
    sync_all_user_permissions,
    list_idempiere_users,
    preview_role_mapping,
    bulk_import_idempiere_users,
)
from app.services.window_capability_map import get_all_capabilities

router = APIRouter(prefix="/admin", tags=["Administración"])

@router.get("/capabilities")
def list_capabilities(
    admin: User = Depends(require_admin),
):
    """List all bot capabilities (query types) and their keywords."""
    caps = get_all_capabilities()
    return {"total": len(caps), "capabilities": caps}


@router.get("/idempiere-users")
def get_idempiere_users_list(
    admin: User = Depends(require_admin),
):
    """List iDempiere users with their roles (for linking to bot users)."""
    try:
        users = list_idempiere_users()
        return {"total": len(users), "users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando iDempiere: {e}")


@router.get("/role-sync/preview/{ad_user_id}")
def preview_role_sync(
    ad_user_id: int,
    admin: User = Depends(require_admin),
):
    """Preview what bot permissions would be assigned for an iDempiere user.

    Call this before linking a bot user to verify the mapping is correct.
    """
    try:
        return preview_role_mapping(ad_user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")


@router.post("/role-sync/user/{user_id}")
def sync_single_user_roles(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Sync a single bot user's permissions from their iDempiere roles.

    The user must have ad_user_id set (linked to iDempiere).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    result = sync_user_permissions(db, user)

    log_action(
        db,
        user_id=admin.id,
        action="role_sync",
        resource="security",
        detail=(
            f"Sync roles para {result.username}: "
            f"{result.departments_before} → {result.departments_after} "
            f"({result.status})"
        ),
    )

    return {
        "user_id": result.user_id,
        "username": result.username,
        "ad_user_id": result.ad_user_id,
        "status": result.status,
        "detail": result.detail,
        "capabilities_count": result.capabilities_count,
        "departments": {
            "before": result.departments_before,
            "after": result.departments_after,
        },
        "org_ids": {
            "before": result.org_ids_before,
            "after": result.org_ids_after,
        },
    }


@router.post("/role-sync/all")
def sync_all_users_roles(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Sync permissions for ALL bot users linked to iDempiere.

    Only processes users with ad_user_id set and is_active=true.
    """
    results = sync_all_user_permissions(db)

    log_action(
        db,
        user_id=admin.id,
        action="role_sync_all",
        resource="security",
        detail=f"Sync masivo: {len(results)} usuarios procesados",
    )

    synced = [r for r in results if r.status == "synced"]
    errors = [r for r in results if r.status == "error"]
    no_roles = [r for r in results if r.status == "no_roles_found"]

    return {
        "total_processed": len(results),
        "synced": len(synced),
        "errors": len(errors),
        "no_roles_found": len(no_roles),
        "results": [
            {
                "user_id": r.user_id,
                "username": r.username,
                "ad_user_id": r.ad_user_id,
                "status": r.status,
                "detail": r.detail,
                "capabilities_count": r.capabilities_count,
                "departments_after": r.departments_after,
                "org_ids_after": r.org_ids_after,
            }
            for r in results
        ],
    }


@router.post("/bulk-import")
def bulk_import_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Import ALL iDempiere users with roles into the bot (inactive).

    - Deduplicates by person name (same person with multiple ad_user_ids)
    - Picks the ad_user_id with the most roles as primary
    - Generates usernames (first initial + last name)
    - Creates all users as INACTIVE with temp password
    - Syncs permissions from iDempiere automatically
    - Skips users already in the bot

    After import, activate users from the admin panel as needed.
    """
    try:
        result = bulk_import_idempiere_users(db)

        log_action(
            db,
            user_id=admin.id,
            action="bulk_import",
            resource="security",
            detail=(
                f"Importación masiva: {result['created']} creados, "
                f"{result['skipped']} omitidos, {result['errors']} errores"
            ),
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en importación: {e}")


# ─────────────────────────────────────────────────────────────────────
# SQL Audit Log (14/Abr/2026)
# ─────────────────────────────────────────────────────────────────────
# Cada query que pasa por SQL Directo queda registrada con el SQL
# generado, modificado por enforcement, filas devueltas, tiempo, etc.
# Sirve para diagnosticar bugs cuando el bot devuelve un número raro:
# se busca la entrada por mensaje, se ve el SQL completo y se decide
# si el fix es de catálogo, de prompt, o de enforcement.


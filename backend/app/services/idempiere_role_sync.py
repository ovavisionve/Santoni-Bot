"""Synchronize iDempiere roles → SantoniBot user permissions.

Maps iDempiere ad_role assignments to bot departments, organization access,
and sensitivity levels.  Only reads from iDempiere (read-only connection).

Usage:
    from app.services.idempiere_role_sync import sync_user_permissions
    result = sync_user_permissions(db, user)          # single user
    results = sync_all_user_permissions(db)            # all linked users
"""

import logging
from typing import NamedTuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import IdempiereSession
from app.models.user import User, Department, UserRole

logger = logging.getLogger("santonibot.role_sync")

# ─── iDempiere Role → Bot Department mapping ──────────────────
#
# Each tuple: (iDempiere role name pattern (lowercased), bot department)
# Patterns are matched with "in" (substring), checked in order.
# First match wins per role, but a user can accumulate multiple departments.

_ROLE_DEPARTMENT_MAP: list[tuple[str, str]] = [
    # Contabilidad (BEFORE compras - "contabilidadcompras" contains "compras")
    ("contabilidadcompras", "contabilidad"),
    ("contabilidad", "contabilidad"),

    # Compras insumos
    ("comprasadmininproa", "compras_insumos"),
    ("comprasrepuestos", "compras_insumos"),
    ("compras", "compras_insumos"),

    # Compras productores (recepción materia prima)
    ("recepcionadmininproa", "compras_productores"),
    ("recepcionuserinproa", "compras_productores"),
    ("recepcion", "compras_productores"),

    # Ventas
    ("ventasadmininproa", "ventas"),
    ("subgerenciaventas", "ventas"),
    ("ventas", "ventas"),

    # RRHH / Nómina / Talento Humano
    ("nomina", "rrhh"),
    ("asistente nomina", "rrhh"),
    ("recursos humanos", "rrhh"),
    ("talento humano", "rrhh"),

    # Finanzas / Tesorería
    ("tesoreriaadmin", "finanzas"),
    ("asistente tesoreria", "finanzas"),
    ("tesoreria", "finanzas"),

    # Producción
    ("produccion planta", "produccion"),
    ("produccion", "produccion"),

    # Almacén → produccion (inventario)
    ("almacenista", "produccion"),
]

# Roles that grant "all departments" (admin-level in iDempiere)
_ADMIN_ROLES = {
    "superuser",
    "system administrator",
    "gerencia general",
    "gerente general",
}

# Department → sensitivity level
_DEPT_SENSITIVITY: dict[str, int] = {
    "ventas": 0,
    "produccion": 0,
    "compras_insumos": 0,
    "compras_productores": 0,
    "contabilidad": 1,
    "finanzas": 1,
    "rrhh": 2,
}


class SyncResult(NamedTuple):
    user_id: int
    username: str
    ad_user_id: int | None
    departments_before: str
    departments_after: str
    org_ids_before: str | None
    org_ids_after: str | None
    status: str  # "synced", "no_ad_user_id", "no_roles_found", "error"
    detail: str


def _map_roles_to_departments(role_names: list[str]) -> set[str]:
    """Map a list of iDempiere role names to bot department names."""
    departments: set[str] = set()
    for role_name in role_names:
        role_lower = role_name.lower().strip()
        # Check admin roles
        if role_lower in _ADMIN_ROLES:
            return {d.value for d in Department}  # all departments
        # Check mapping
        for pattern, dept in _ROLE_DEPARTMENT_MAP:
            if pattern in role_lower:
                departments.add(dept)
                break  # first match per role wins
    return departments


def _get_user_roles(ide_session, ad_user_id: int) -> list[str]:
    """Query iDempiere for the roles assigned to a user."""
    rows = ide_session.execute(text("""
        SELECT r.name
        FROM adempiere.ad_user_roles ur
        JOIN adempiere.ad_role r ON ur.ad_role_id = r.ad_role_id
        WHERE ur.ad_user_id = :uid AND ur.isactive = 'Y' AND r.isactive = 'Y'
        ORDER BY r.name
    """), {"uid": ad_user_id}).fetchall()
    return [row[0] for row in rows]


def _get_user_org_ids(ide_session, ad_user_id: int) -> list[int]:
    """Query iDempiere for the organizations accessible via user's roles."""
    rows = ide_session.execute(text("""
        SELECT DISTINCT roa.ad_org_id
        FROM adempiere.ad_user_roles ur
        JOIN adempiere.ad_role_orgaccess roa ON ur.ad_role_id = roa.ad_role_id
        WHERE ur.ad_user_id = :uid
          AND ur.isactive = 'Y'
          AND roa.isactive = 'Y'
          AND roa.ad_org_id > 0
        ORDER BY roa.ad_org_id
    """), {"uid": ad_user_id}).fetchall()
    return [row[0] for row in rows]


def _get_idempiere_user_name(ide_session, ad_user_id: int) -> str | None:
    """Get the name of an iDempiere user by ID."""
    row = ide_session.execute(text(
        "SELECT name FROM adempiere.ad_user WHERE ad_user_id = :uid"
    ), {"uid": ad_user_id}).fetchone()
    return row[0] if row else None


def sync_user_permissions(db: Session, user: User) -> SyncResult:
    """Sync a single bot user's permissions from their iDempiere roles.

    Reads the user's ad_user_id, queries iDempiere for their roles and
    org access, maps roles → departments, and updates the user record.
    """
    if not user.ad_user_id:
        return SyncResult(
            user_id=user.id,
            username=user.username,
            ad_user_id=None,
            departments_before=_format_departments(user),
            departments_after=_format_departments(user),
            org_ids_before=user.allowed_org_ids,
            org_ids_after=user.allowed_org_ids,
            status="no_ad_user_id",
            detail="Usuario no vinculado a iDempiere (ad_user_id vacío)",
        )

    departments_before = _format_departments(user)
    org_ids_before = user.allowed_org_ids

    ide = IdempiereSession()
    try:
        # 1. Get iDempiere role names
        role_names = _get_user_roles(ide, user.ad_user_id)
        if not role_names:
            return SyncResult(
                user_id=user.id,
                username=user.username,
                ad_user_id=user.ad_user_id,
                departments_before=departments_before,
                departments_after=departments_before,
                org_ids_before=org_ids_before,
                org_ids_after=org_ids_before,
                status="no_roles_found",
                detail=f"No se encontraron roles activos para ad_user_id={user.ad_user_id}",
            )

        # 2. Map roles → departments
        mapped_depts = _map_roles_to_departments(role_names)
        is_admin_level = mapped_depts == {d.value for d in Department}

        # 3. Get org access
        org_ids = _get_user_org_ids(ide, user.ad_user_id)

        # 4. Update user record
        if is_admin_level:
            # User has admin-level iDempiere role → give admin bot role
            user.role = UserRole.ADMINISTRADOR
            user.allowed_org_ids = None  # all orgs
            user.extra_departments = None
            # sensitivity: max
            user.sensitivity_level = 2
        elif mapped_depts:
            dept_list = sorted(mapped_depts)
            # Primary department = first one
            primary = dept_list[0]
            extras = dept_list[1:]

            user.department = Department(primary)
            user.extra_departments = ",".join(extras) if extras else None

            # Org IDs from iDempiere role-org mapping
            if org_ids:
                user.allowed_org_ids = ",".join(str(o) for o in org_ids)
            # else: keep existing (don't remove if iDempiere has no org restrictions)

            # Sensitivity = max of all departments
            user.sensitivity_level = max(
                _DEPT_SENSITIVITY.get(d, 0) for d in dept_list
            )

            # If user currently has a role lower than supervisor and has 2+ depts,
            # upgrade to supervisor (multi-department access)
            if len(dept_list) > 1 and user.role == UserRole.USUARIO:
                user.role = UserRole.SUPERVISOR

        db.commit()

        departments_after = _format_departments(user)
        org_ids_after = user.allowed_org_ids

        logger.info(
            "Synced user %s (ad_user_id=%s): roles=%s → depts=%s, orgs=%s",
            user.username, user.ad_user_id, role_names, departments_after, org_ids_after,
        )

        return SyncResult(
            user_id=user.id,
            username=user.username,
            ad_user_id=user.ad_user_id,
            departments_before=departments_before,
            departments_after=departments_after,
            org_ids_before=org_ids_before,
            org_ids_after=org_ids_after,
            status="synced",
            detail=f"Roles iDempiere: {', '.join(role_names)}",
        )

    except Exception as e:
        logger.error("Error syncing user %s: %s", user.username, e, exc_info=True)
        db.rollback()
        return SyncResult(
            user_id=user.id,
            username=user.username,
            ad_user_id=user.ad_user_id,
            departments_before=departments_before,
            departments_after=departments_before,
            org_ids_before=org_ids_before,
            org_ids_after=org_ids_before,
            status="error",
            detail=str(e),
        )
    finally:
        ide.close()


def sync_all_user_permissions(db: Session) -> list[SyncResult]:
    """Sync permissions for all bot users that have an ad_user_id."""
    users = db.query(User).filter(
        User.ad_user_id.isnot(None),
        User.is_active == True,
    ).all()

    results = []
    for user in users:
        result = sync_user_permissions(db, user)
        results.append(result)

    return results


def list_idempiere_users() -> list[dict]:
    """List all iDempiere users for the admin to pick from when linking."""
    ide = IdempiereSession()
    try:
        rows = ide.execute(text("""
            SELECT u.ad_user_id, u.name, u.email,
                   string_agg(DISTINCT r.name, ', ' ORDER BY r.name) AS roles
            FROM adempiere.ad_user u
            LEFT JOIN adempiere.ad_user_roles ur
                ON ur.ad_user_id = u.ad_user_id AND ur.isactive = 'Y'
            LEFT JOIN adempiere.ad_role r
                ON r.ad_role_id = ur.ad_role_id AND r.isactive = 'Y'
            WHERE u.isactive = 'Y'
              AND u.ad_user_id > 0
              AND u.name NOT IN ('System', 'SuperUser', 'GardenAdmin', 'GardenUser')
            GROUP BY u.ad_user_id, u.name, u.email
            ORDER BY u.name
        """)).fetchall()
        return [
            {
                "ad_user_id": row[0],
                "name": row[1],
                "email": row[2],
                "roles": row[3] or "",
            }
            for row in rows
        ]
    finally:
        ide.close()


def preview_role_mapping(ad_user_id: int) -> dict:
    """Preview what permissions would be assigned for a given iDempiere user.

    Useful for the admin to verify before linking a bot user.
    """
    ide = IdempiereSession()
    try:
        ide_name = _get_idempiere_user_name(ide, ad_user_id)
        role_names = _get_user_roles(ide, ad_user_id)
        org_ids = _get_user_org_ids(ide, ad_user_id)

        # Get org names for display
        org_names = []
        if org_ids:
            placeholders = ", ".join(f":o{i}" for i in range(len(org_ids)))
            params = {f"o{i}": oid for i, oid in enumerate(org_ids)}
            rows = ide.execute(text(
                f"SELECT ad_org_id, name FROM adempiere.ad_org "
                f"WHERE ad_org_id IN ({placeholders})"
            ), params).fetchall()
            org_names = [{"id": r[0], "name": r[1]} for r in rows]

        mapped_depts = _map_roles_to_departments(role_names)
        is_admin = mapped_depts == {d.value for d in Department}

        max_sensitivity = max(
            (_DEPT_SENSITIVITY.get(d, 0) for d in mapped_depts), default=0
        )

        return {
            "ad_user_id": ad_user_id,
            "idempiere_name": ide_name,
            "idempiere_roles": role_names,
            "mapped_departments": sorted(mapped_depts),
            "is_admin_level": is_admin,
            "organizations": org_names,
            "org_ids": org_ids,
            "sensitivity_level": 2 if is_admin else max_sensitivity,
            "suggested_role": "administrador" if is_admin else (
                "supervisor" if len(mapped_depts) > 1 else "usuario"
            ),
        }
    finally:
        ide.close()


def _format_departments(user: User) -> str:
    """Format user's departments as readable string."""
    deps = [user.department.value] if user.department else []
    if user.extra_departments:
        deps.extend(d.strip() for d in user.extra_departments.split(",") if d.strip())
    return ", ".join(deps) if deps else "(ninguno)"

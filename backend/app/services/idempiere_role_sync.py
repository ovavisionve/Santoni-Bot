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
from app.services.window_capability_map import (
    CAPABILITIES,
    get_capabilities_for_windows,
    get_capabilities_for_tables,
    get_agents_for_capabilities,
    get_all_keywords_for_capabilities,
)

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
    capabilities_count: int
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


def _get_user_window_names(ide_session, ad_user_id: int) -> list[str]:
    """Query iDempiere for the window names accessible via user's roles."""
    rows = ide_session.execute(text("""
        SELECT DISTINCT w.name
        FROM adempiere.ad_user_roles ur
        JOIN adempiere.ad_window_access wa ON ur.ad_role_id = wa.ad_role_id
        JOIN adempiere.ad_window w ON wa.ad_window_id = w.ad_window_id
        WHERE ur.ad_user_id = :uid
          AND ur.isactive = 'Y'
          AND wa.isactive = 'Y'
          AND w.isactive = 'Y'
        ORDER BY w.name
    """), {"uid": ad_user_id}).fetchall()
    return [row[0] for row in rows]


def _get_user_table_names(ide_session, ad_user_id: int) -> list[str]:
    """Query iDempiere for the table names accessible via user's window→tab access."""
    rows = ide_session.execute(text("""
        SELECT DISTINCT t.tablename
        FROM adempiere.ad_user_roles ur
        JOIN adempiere.ad_window_access wa ON ur.ad_role_id = wa.ad_role_id
        JOIN adempiere.ad_tab tab ON tab.ad_window_id = wa.ad_window_id
        JOIN adempiere.ad_table t ON tab.ad_table_id = t.ad_table_id
        WHERE ur.ad_user_id = :uid
          AND ur.isactive = 'Y'
          AND wa.isactive = 'Y'
          AND tab.isactive = 'Y'
          AND t.isactive = 'Y'
        ORDER BY t.tablename
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
            capabilities_count=0,
            status="no_ad_user_id",
            detail="Usuario no vinculado a iDempiere (ad_user_id vacío)",
        )

    departments_before = _format_departments(user)
    org_ids_before = user.allowed_org_ids

    ide = IdempiereSession()
    try:
        # Use ALL ad_user_ids for this person (multi-org combined permissions)
        all_user_ids = user.all_idempiere_user_ids
        if not all_user_ids:
            all_user_ids = [user.ad_user_id]

        # 1. Get iDempiere role names from ALL ad_user_ids
        role_names: list[str] = []
        for uid in all_user_ids:
            role_names.extend(_get_user_roles(ide, uid))
        role_names = sorted(set(role_names))  # deduplicate

        if not role_names:
            return SyncResult(
                user_id=user.id,
                username=user.username,
                ad_user_id=user.ad_user_id,
                departments_before=departments_before,
                departments_after=departments_before,
                org_ids_before=org_ids_before,
                org_ids_after=org_ids_before,
                capabilities_count=0,
                status="no_roles_found",
                detail=f"No se encontraron roles activos para ad_user_ids={all_user_ids}",
            )

        # 2. Map roles → departments
        mapped_depts = _map_roles_to_departments(role_names)
        is_admin_level = mapped_depts == {d.value for d in Department}

        # 3. Get org access from ALL ad_user_ids
        org_ids: list[int] = []
        for uid in all_user_ids:
            org_ids.extend(_get_user_org_ids(ide, uid))
        org_ids = sorted(set(org_ids))

        # 4. Get window/table access from ALL ad_user_ids (COMBINED PERMISSIONS)
        window_names: list[str] = []
        table_names: list[str] = []
        for uid in all_user_ids:
            window_names.extend(_get_user_window_names(ide, uid))
            table_names.extend(_get_user_table_names(ide, uid))
        window_names = sorted(set(window_names))
        table_names = sorted(set(table_names))

        # Compute capabilities from both windows and tables
        caps_from_windows = get_capabilities_for_windows(window_names)
        caps_from_tables = get_capabilities_for_tables(table_names)
        all_capabilities = caps_from_windows | caps_from_tables

        if is_admin_level:
            # Admin gets ALL capabilities
            all_capabilities = set(CAPABILITIES.keys())

        # Derive departments from capabilities (more precise than role name matching)
        cap_agents = get_agents_for_capabilities(all_capabilities)
        if cap_agents:
            # Use capability-derived departments (more precise)
            mapped_depts = cap_agents

        # 5. Update user record
        if is_admin_level:
            user.role = UserRole.ADMINISTRADOR
            user.allowed_org_ids = None
            user.extra_departments = None
            user.sensitivity_level = 2
            user.allowed_capabilities = None  # NULL = all capabilities
        elif mapped_depts:
            dept_list = sorted(mapped_depts)
            primary = dept_list[0]
            extras = dept_list[1:]

            user.department = Department(primary)
            user.extra_departments = ",".join(extras) if extras else None

            if org_ids:
                user.allowed_org_ids = ",".join(str(o) for o in org_ids)

            user.sensitivity_level = max(
                _DEPT_SENSITIVITY.get(d, 0) for d in dept_list
            )

            # Store granular capabilities
            user.allowed_capabilities = ",".join(sorted(all_capabilities)) if all_capabilities else None

            if len(dept_list) > 1 and user.role == UserRole.USUARIO:
                user.role = UserRole.SUPERVISOR

        db.commit()

        departments_after = _format_departments(user)
        org_ids_after = user.allowed_org_ids

        logger.info(
            "Synced user %s (ad_user_ids=%s): roles=%s → depts=%s, "
            "capabilities=%d, windows=%d, tables=%d, orgs=%s",
            user.username, all_user_ids, role_names, departments_after,
            len(all_capabilities), len(window_names), len(table_names), org_ids_after,
        )

        return SyncResult(
            user_id=user.id,
            username=user.username,
            ad_user_id=user.ad_user_id,
            departments_before=departments_before,
            departments_after=departments_after,
            org_ids_before=org_ids_before,
            org_ids_after=org_ids_after,
            capabilities_count=len(all_capabilities),
            status="synced",
            detail=(
                f"Roles: {', '.join(role_names)} ({len(all_user_ids)} ad_user_ids) | "
                f"Ventanas: {len(window_names)} | "
                f"Capacidades: {len(all_capabilities)}"
            ),
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
            capabilities_count=0,
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

    Shows roles, windows, capabilities, departments, and organizations.
    Useful for the admin to verify before linking a bot user.
    """
    ide = IdempiereSession()
    try:
        ide_name = _get_idempiere_user_name(ide, ad_user_id)
        role_names = _get_user_roles(ide, ad_user_id)
        org_ids = _get_user_org_ids(ide, ad_user_id)
        window_names = _get_user_window_names(ide, ad_user_id)
        table_names = _get_user_table_names(ide, ad_user_id)

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

        # Compute capabilities
        caps_from_windows = get_capabilities_for_windows(window_names)
        caps_from_tables = get_capabilities_for_tables(table_names)
        all_caps = caps_from_windows | caps_from_tables

        mapped_depts = _map_roles_to_departments(role_names)
        is_admin = mapped_depts == {d.value for d in Department}

        if is_admin:
            all_caps = set(CAPABILITIES.keys())

        # Derive departments from capabilities
        cap_agents = get_agents_for_capabilities(all_caps)
        if cap_agents:
            mapped_depts = cap_agents

        max_sensitivity = max(
            (_DEPT_SENSITIVITY.get(d, 0) for d in mapped_depts), default=0
        )

        # Build capability detail list
        cap_details = []
        for cap_id in sorted(all_caps):
            cap = CAPABILITIES.get(cap_id)
            if cap:
                cap_details.append({
                    "id": cap.id,
                    "agent": cap.agent,
                    "display_name": cap.display_name,
                    "keywords_count": len(cap.keywords),
                })

        return {
            "ad_user_id": ad_user_id,
            "idempiere_name": ide_name,
            "idempiere_roles": role_names,
            "idempiere_windows": len(window_names),
            "idempiere_tables": len(table_names),
            "mapped_departments": sorted(mapped_depts),
            "capabilities": cap_details,
            "capabilities_count": len(all_caps),
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


def bulk_import_idempiere_users(db: Session) -> dict:
    """Import ALL iDempiere users with roles into the bot as inactive users.

    Groups by person name to deduplicate (same person may have multiple
    ad_user_ids across iDempiere clients).  Picks the ad_user_id with the
    most roles as the primary.  Skips users already in the bot (by ad_user_id
    or generated username).

    Returns summary with created, skipped, error counts.
    """
    from app.services.auth import hash_password
    import unicodedata
    import secrets
    import string

    ide = IdempiereSession()
    try:
        # Fetch all users with at least one active role
        rows = ide.execute(text("""
            SELECT u.ad_user_id, u.name, u.email,
                   string_agg(DISTINCT r.name, ', ' ORDER BY r.name) AS roles,
                   COUNT(DISTINCT r.ad_role_id) AS role_count
            FROM adempiere.ad_user u
            JOIN adempiere.ad_user_roles ur
                ON ur.ad_user_id = u.ad_user_id AND ur.isactive = 'Y'
            JOIN adempiere.ad_role r
                ON r.ad_role_id = ur.ad_role_id AND r.isactive = 'Y'
            WHERE u.isactive = 'Y'
              AND u.ad_user_id > 0
              AND u.name NOT IN ('System', 'SuperUser', 'GardenAdmin', 'GardenUser')
            GROUP BY u.ad_user_id, u.name, u.email
            ORDER BY u.name
        """)).fetchall()
    finally:
        ide.close()

    # Group by normalized name → pick best ad_user_id
    from collections import defaultdict
    people: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        ad_user_id, name, email, roles, role_count = row
        norm_name = _normalize_name(name)
        if not norm_name or len(norm_name) < 2:
            continue
        people[norm_name].append({
            "ad_user_id": ad_user_id,
            "name": name,
            "email": email,
            "roles": roles,
            "role_count": role_count,
        })

    # Get existing ad_user_ids and usernames to skip
    existing_ad_ids = {
        r[0] for r in db.query(User.ad_user_id).filter(
            User.ad_user_id.isnot(None)
        ).all()
    }
    existing_usernames = {
        r[0].lower() for r in db.query(User.username).all()
    }
    existing_emails = {
        r[0].lower() for r in db.query(User.email).all()
    }

    created = []
    skipped = []
    errors = []
    default_password = hash_password("SantoniTemp2026!")

    for norm_name, entries in people.items():
        # Pick the entry with the most roles
        best = max(entries, key=lambda e: e["role_count"])
        ad_user_id = best["ad_user_id"]
        full_name = best["name"].strip()
        email = best["email"]

        # Skip if ad_user_id already linked
        if ad_user_id in existing_ad_ids:
            skipped.append({
                "name": full_name,
                "ad_user_id": ad_user_id,
                "reason": "ad_user_id ya vinculado",
            })
            continue

        # Also check if ANY of this person's ad_user_ids are already linked
        all_ids = {e["ad_user_id"] for e in entries}
        if all_ids & existing_ad_ids:
            skipped.append({
                "name": full_name,
                "ad_user_id": ad_user_id,
                "reason": "persona ya tiene otro ad_user_id vinculado",
            })
            continue

        # Generate username
        username = _generate_username(full_name)

        # Build comma-separated list of ALL ad_user_ids for this person
        all_ids_str = ",".join(str(e["ad_user_id"]) for e in entries)

        # If username matches an existing user WITHOUT ad_user_id, link them
        existing_user = db.query(User).filter(
            User.username == username,
            User.ad_user_id.is_(None),
        ).first()
        if existing_user:
            existing_user.ad_user_id = ad_user_id
            existing_user.all_ad_user_ids = all_ids_str
            existing_ad_ids.add(ad_user_id)
            db.flush()
            created.append({
                "id": existing_user.id,
                "username": username,
                "full_name": full_name,
                "ad_user_id": ad_user_id,
                "all_ad_user_ids": all_ids_str,
                "roles": best["roles"],
                "department": existing_user.department.value,
                "linked_existing": True,
            })
            continue

        # Ensure username uniqueness
        base_username = username
        counter = 1
        while username.lower() in existing_usernames:
            username = f"{base_username}{counter}"
            counter += 1
        existing_usernames.add(username.lower())

        # Generate email if missing
        if not email or email.lower() in existing_emails:
            email = f"{username}@santonibot.local"
        # Ensure email uniqueness
        base_email = email
        counter = 1
        while email.lower() in existing_emails:
            name_part, domain = base_email.rsplit("@", 1)
            email = f"{name_part}{counter}@{domain}"
            counter += 1
        existing_emails.add(email.lower())

        # Determine initial department from roles
        role_names = [r.strip() for r in best["roles"].split(",")]
        mapped_depts = _map_roles_to_departments(role_names)
        is_admin = mapped_depts == {d.value for d in Department}

        if is_admin:
            dept = Department.VENTAS  # placeholder, will be overridden by sync
            bot_role = UserRole.ADMINISTRADOR
        elif mapped_depts:
            dept_list = sorted(mapped_depts)
            dept = Department(dept_list[0])
            bot_role = UserRole.SUPERVISOR if len(dept_list) > 1 else UserRole.USUARIO
        else:
            dept = Department.VENTAS  # fallback
            bot_role = UserRole.USUARIO

        try:
            user = User(
                email=email,
                username=username,
                full_name=full_name,
                hashed_password=default_password,
                role=bot_role,
                department=dept,
                extra_departments=",".join(sorted(mapped_depts - {dept.value})) if len(mapped_depts) > 1 else None,
                ad_user_id=ad_user_id,
                all_ad_user_ids=all_ids_str,
                is_active=False,
                sensitivity_level=0,
            )
            db.add(user)
            db.flush()  # get user.id

            # Track the ad_user_id as existing
            existing_ad_ids.add(ad_user_id)

            created.append({
                "id": user.id,
                "username": username,
                "full_name": full_name,
                "ad_user_id": ad_user_id,
                "roles": best["roles"],
                "department": dept.value,
            })
        except Exception as e:
            db.rollback()
            errors.append({
                "name": full_name,
                "ad_user_id": ad_user_id,
                "error": str(e),
            })
            logger.error("Error creating user %s: %s", full_name, e)

    # Commit all created users
    if created:
        db.commit()

    # Now sync permissions for all newly created users
    synced_count = 0
    sync_errors = 0
    for entry in created:
        try:
            user = db.query(User).filter(User.id == entry["id"]).first()
            if user:
                result = sync_user_permissions(db, user)
                if result.status == "synced":
                    synced_count += 1
                    entry["capabilities_count"] = result.capabilities_count
                    entry["department"] = result.departments_after
                else:
                    entry["sync_status"] = result.status
        except Exception as e:
            sync_errors += 1
            logger.error("Error syncing imported user %s: %s", entry["username"], e)

    return {
        "total_idempiere_users_with_roles": len(rows),
        "unique_people": len(people),
        "created": len(created),
        "skipped": len(skipped),
        "errors": len(errors),
        "synced": synced_count,
        "sync_errors": sync_errors,
        "default_password": "SantoniTemp2026!",
        "note": "Todos los usuarios importados están INACTIVOS. Active desde el panel admin.",
        "created_users": created[:50],  # limit response size
        "skipped_users": skipped[:50],
        "error_details": errors,
    }


def _normalize_name(name: str) -> str:
    """Normalize a name for deduplication: lowercase, strip accents, remove non-alpha."""
    import unicodedata
    name = name.strip().upper()
    # Remove accents
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Keep only letters and spaces
    clean = "".join(c for c in ascii_name if c.isalpha() or c == " ")
    return " ".join(clean.split())  # normalize whitespace


def _generate_username(full_name: str) -> str:
    """Generate a username from a full name: first initial + last name.

    Examples:
      JOHAN ALVAREZ → jalvarez
      EMELIN SALAS → esalas
      LENNY MERCEDES SILVA DE GIRALDO → lsilva
      AdminMaiz → adminmaiz
    """
    import unicodedata
    # Remove accents
    nfkd = unicodedata.normalize("NFKD", full_name.strip())
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Keep only letters and spaces
    clean = "".join(c for c in ascii_name if c.isalpha() or c == " ")
    parts = clean.split()

    if not parts:
        return "user"

    # Filter out common connectors
    skip_words = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "Y"}

    if len(parts) == 1:
        return parts[0].lower()

    first_initial = parts[0][0].lower()

    # Find first "last name" (skip given names — take from position 1+,
    # skipping connectors)
    # Heuristic: if name has 2 parts, use second. If 3+, try second as last name.
    # If it's a connector, try third.
    for part in parts[1:]:
        if part.upper() not in skip_words:
            return f"{first_initial}{part.lower()}"

    # Fallback: just first initial + second word
    return f"{first_initial}{parts[1].lower()}"


def _format_departments(user: User) -> str:
    """Format user's departments as readable string."""
    deps = [user.department.value] if user.department else []
    if user.extra_departments:
        deps.extend(d.strip() for d in user.extra_departments.split(",") if d.strip())
    return ", ".join(deps) if deps else "(ninguno)"

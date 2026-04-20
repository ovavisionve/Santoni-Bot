"""Role → department mapping rules, sensitivity table, and name normalization helpers."""

import unicodedata
from typing import NamedTuple

from app.models.user import Department, User

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
        if role_lower in _ADMIN_ROLES:
            return {d.value for d in Department}
        for pattern, dept in _ROLE_DEPARTMENT_MAP:
            if pattern in role_lower:
                departments.add(dept)
                break
    return departments


def _format_departments(user: User) -> str:
    """Format user's departments as readable string."""
    deps = [user.department.value] if user.department else []
    if user.extra_departments:
        deps.extend(d.strip() for d in user.extra_departments.split(",") if d.strip())
    return ", ".join(deps) if deps else "(ninguno)"


def _normalize_name(name: str) -> str:
    """Normalize a name for deduplication: lowercase, strip accents, remove non-alpha."""
    name = name.strip().upper()
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    clean = "".join(c for c in ascii_name if c.isalpha() or c == " ")
    return " ".join(clean.split())


def _generate_username(full_name: str) -> str:
    """Generate a username from a full name: first initial + last name.

    Examples:
      JOHAN ALVAREZ → jalvarez
      EMELIN SALAS → esalas
      LENNY MERCEDES SILVA DE GIRALDO → lsilva
      AdminMaiz → adminmaiz
    """
    nfkd = unicodedata.normalize("NFKD", full_name.strip())
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    clean = "".join(c for c in ascii_name if c.isalpha() or c == " ")
    parts = clean.split()

    if not parts:
        return "user"

    skip_words = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "Y"}

    if len(parts) == 1:
        return parts[0].lower()

    first_initial = parts[0][0].lower()

    for part in parts[1:]:
        if part.upper() not in skip_words:
            return f"{first_initial}{part.lower()}"

    return f"{first_initial}{parts[1].lower()}"

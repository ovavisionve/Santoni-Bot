"""HR query wrappers: employees, payroll, attendance, etc."""

import logging

from sqlalchemy import text

from app.database import SessionLocal
from .core import _is_production, _rows_to_dicts, _convert_value

logger = logging.getLogger("santonibot.query_service")

def build_employee_summary(org_ids: list[int] | None = None) -> dict:
    """Employee summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_employee_summary as _prod
        return _prod(org_ids=org_ids)

    db = SessionLocal()
    try:
        totals_q = text(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN activo THEN 1 ELSE 0 END) AS activos, "
            "SUM(CASE WHEN NOT activo THEN 1 ELSE 0 END) AS inactivos "
            "FROM demo_empleados"
        )
        row = db.execute(totals_q).fetchone()
        totals = {
            "total": row[0] if row else 0,
            "activos": row[1] if row else 0,
            "inactivos": row[2] if row else 0,
        }

        by_dept_q = text(
            "SELECT departamento, COUNT(*) AS total, "
            "SUM(CASE WHEN activo THEN 1 ELSE 0 END) AS activos "
            "FROM demo_empleados GROUP BY departamento ORDER BY total DESC"
        )
        by_dept = [
            {"departamento": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_dept_q).fetchall()
        ]

        return {
            "totales": totals,
            "por_departamento": by_dept,
        }
    finally:
        db.close()


def build_birthday_list(
    mes: int | None = None,
    org_ids: list[int] | None = None,
) -> list[dict]:
    """Birthday list - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_birthday_list as _prod
        return _prod(mes=mes, org_ids=org_ids)
    return []


def build_employee_list(
    org_ids: list[int] | None = None,
    cargo_search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Employee list - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_employee_list as _prod
        return _prod(
            org_ids=org_ids, cargo_search=cargo_search,
            date_from=date_from, date_to=date_to,
        )

    db = SessionLocal()
    try:
        q = text(
            "SELECT nombre, '' AS codigo, departamento AS organizacion, "
            "CASE WHEN activo THEN 'Activo' ELSE 'Inactivo' END AS estado, "
            "'' AS fecha_ingreso "
            "FROM demo_empleados ORDER BY nombre LIMIT 50"
        )
        return [
            {
                "nombre": r[0], "codigo": r[1], "organizacion": r[2],
                "estado": r[3], "fecha_ingreso": r[4],
            }
            for r in db.execute(q).fetchall()
        ]
    finally:
        db.close()


def build_payroll_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Payroll summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_payroll_summary as _prod
        return _prod(mes=mes, anio=anio, org_ids=org_ids, date_from=date_from, date_to=date_to)

    # Demo fallback
    return {
        "totales": {
            "total_procesos": 0,
            "empleados_procesados": 0,
            "total_devengado": 0.0,
            "total_deducciones": 0.0,
            "neto_a_pagar": 0.0,
        },
        "por_tipo_nomina": [],
        "conceptos_principales": [],
    }


def build_attendance_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Attendance/absence summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_attendance_summary as _prod
        return _prod(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
        )

    # Demo fallback
    return {
        "totales": {
            "empleados_activos": 0,
            "empleados_con_ausencias": 0,
            "tasa_ausentismo_pct": 0.0,
            "conceptos_encontrados": 0,
            "nota": "Datos de ausentismo no disponibles en modo demo.",
        },
        "por_concepto": [],
        "por_organizacion": [],
    }


def build_turnover_summary(
    anio: int | None = None,
    org_ids: list[int] | None = None,
) -> dict:
    """Turnover/rotation summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_turnover_summary as _prod
        return _prod(anio=anio, org_ids=org_ids)

    # Demo fallback
    return {
        "anio": anio,
        "totales": {
            "empleados_activos": 0,
            "bajas": 0,
            "tasa_rotacion_pct": 0.0,
        },
        "por_organizacion": [],
    }


def build_vacation_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Vacation summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_vacation_summary as _prod
        return _prod(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
        )

    # Demo fallback
    return {
        "totales": {
            "total_empleados": 0,
            "total_monto": 0.0,
            "total_ocurrencias": 0,
            "nota": "Datos de vacaciones no disponibles en modo demo.",
        },
        "por_concepto": [],
        "por_organizacion": [],
        "detalle_empleados": [],
    }


# ---------------------------------------------------------------------------
# Pre-built queries: COMPRAS INSUMOS (Supply Purchases)
# ---------------------------------------------------------------------------


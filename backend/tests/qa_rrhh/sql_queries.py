"""
Queries SQL de verificación contra iDempiere para el agente RRHH.

Tablas clave:
  - hr_employee: empleados (isactive='Y', enddate IS NULL = activo)
  - c_bpartner: datos del tercero (nombre, birthday)
  - ad_org: organización
  - hr_department: departamento RRHH
  - lve_empleadosactivos: view oficial LVE con datos consolidados
"""

from datetime import date
from typing import Any

from sqlalchemy import text

from app.database import IdempiereSession


def employee_count_total() -> dict[str, Any]:
    """Total de empleados activos (DISTINCT c_bpartner_id).

    Misma lógica que build_employee_summary: solo filtra isactive='Y'
    en hr_employee y c_bpartner, SIN filtrar por enddate.
    """
    sql = text("""
        SELECT COUNT(DISTINCT e.c_bpartner_id) AS total_empleados
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        WHERE e.isactive = 'Y'
          AND bp.isactive = 'Y'
    """)
    db = IdempiereSession()
    try:
        row = db.execute(sql).fetchone()
        return {
            "label": "Empleados activos total",
            "total": row[0] if row else 0,
        }
    finally:
        db.close()


def employee_count_by_org() -> dict[str, Any]:
    """Empleados activos por organización."""
    sql = text("""
        SELECT o.name AS organizacion,
               COUNT(DISTINCT e.c_bpartner_id) AS empleados
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id
        WHERE e.isactive = 'Y'
          AND bp.isactive = 'Y'
        GROUP BY o.name
        ORDER BY empleados DESC
    """)
    db = IdempiereSession()
    try:
        rows = db.execute(sql).fetchall()
        return {
            "label": "Empleados por organización",
            "by_org": [{"organizacion": r[0], "empleados": r[1]} for r in rows],
        }
    finally:
        db.close()


def birthday_list_month(mes: int) -> dict[str, Any]:
    """Cumpleañeros de un mes específico.

    Birthday está en ad_user.birthday (no c_bpartner.birthday).
    Usa LATERAL subquery como build_birthday_list para un solo
    birthday por c_bpartner_id.
    """
    sql = text("""
        SELECT DISTINCT ON (bp.c_bpartner_id)
               bp.name AS nombre,
               EXTRACT(DAY FROM bday.birthday)::int AS dia
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        JOIN LATERAL (
            SELECT u.birthday FROM adempiere.ad_user u
            WHERE u.c_bpartner_id = bp.c_bpartner_id
              AND u.birthday IS NOT NULL
            ORDER BY u.ad_user_id
            LIMIT 1
        ) bday ON TRUE
        WHERE e.isactive = 'Y'
          AND bp.isactive = 'Y'
          AND EXTRACT(MONTH FROM bday.birthday) = :mes
        ORDER BY bp.c_bpartner_id, dia, nombre
    """)
    db = IdempiereSession()
    try:
        rows = db.execute(sql, {"mes": mes}).fetchall()
        return {
            "label": f"Cumpleañeros del mes {mes}",
            "total": len(rows),
            "names": [r[0] for r in rows[:5]],
        }
    finally:
        db.close()


def payroll_month(mes: int, anio: int) -> dict[str, Any]:
    """Resumen de nómina de un mes (hr_movement totales)."""
    sql = text("""
        SELECT
            COUNT(DISTINCT hm.c_bpartner_id) AS empleados,
            COUNT(*) AS movimientos,
            COALESCE(SUM(CASE WHEN hm.amount > 0 THEN hm.amount ELSE 0 END), 0) AS total_devengado,
            COALESCE(SUM(CASE WHEN hm.amount < 0 THEN ABS(hm.amount) ELSE 0 END), 0) AS total_deducciones
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hm.hr_process_id = hp.hr_process_id
        WHERE hp.docstatus IN ('CO', 'CL')
          AND EXTRACT(MONTH FROM hp.dateacct) = :mes
          AND EXTRACT(YEAR FROM hp.dateacct) = :anio
    """)
    db = IdempiereSession()
    try:
        row = db.execute(sql, {"mes": mes, "anio": anio}).fetchone()
        return {
            "label": f"Nómina {mes:02d}/{anio}",
            "empleados": row[0] if row else 0,
            "movimientos": row[1] if row else 0,
            "total_devengado": float(row[2]) if row else 0,
            "total_deducciones": float(row[3]) if row else 0,
        }
    finally:
        db.close()

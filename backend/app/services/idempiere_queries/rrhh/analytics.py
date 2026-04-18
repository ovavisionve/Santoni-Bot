"""Turnover (rotación) + vacation (vacaciones) HR analytics queries."""

from datetime import datetime

from sqlalchemy import text

from ..common import _add_date_filter, _add_org_filter, _get_session


def build_turnover_summary(
    anio: int | None = None,
    org_ids: list[int] | None = None,
) -> dict:
    """Employee turnover (rotation) from hr_employee enddate.

    Counts employees whose enddate falls within the given year as 'bajas'.
    Calculates turnover rate = bajas / total_activos * 100.
    """
    if not anio:
        anio = datetime.now().year

    db = _get_session(anio=anio)
    try:
        conditions = [
            "e.isactive = 'N'",
            "e.enddate >= :year_start",
            "e.enddate < :year_end",
        ]
        params: dict = {
            "year_start": f"{anio}-01-01",
            "year_end": f"{anio + 1}-01-01",
        }
        _add_org_filter(conditions, params, org_ids, "e")
        where = " AND ".join(conditions)

        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS bajas "
            f"FROM adempiere.hr_employee e "
            f"LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY bajas DESC"
        )
        by_org = [
            {"organizacion": r[0], "bajas": r[1]}
            for r in db.execute(by_org_q, params).fetchall()
        ]
        total_bajas = sum(r["bajas"] for r in by_org)

        emp_conditions = ["1=1"]
        emp_params: dict = {}
        _add_org_filter(emp_conditions, emp_params, org_ids, "e")
        emp_where = " AND ".join(emp_conditions)
        emp_q = text(
            f"SELECT COUNT(DISTINCT e.c_bpartner_id) "
            f"FROM adempiere.hr_employee e "
            f"WHERE e.isactive = 'Y' AND {emp_where}"
        )
        emp_row = db.execute(emp_q, emp_params).fetchone()
        total_activos = emp_row[0] if emp_row else 0

        tasa = (total_bajas / total_activos * 100) if total_activos else 0

        return {
            "anio": anio,
            "totales": {
                "empleados_activos": total_activos,
                "bajas": total_bajas,
                "tasa_rotacion_pct": round(tasa, 2),
            },
            "por_organizacion": by_org,
        }
    finally:
        db.close()


def build_vacation_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Vacation data from hr_movement concepts containing 'vacacion' or 'bono vacacional'."""
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "hp.docstatus IN ('CO', 'CL')",
            "hp.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "hm")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "hp.dateacct")

        vacation_terms = ["%vacacion%", "%bono vacacional%", "%dias disfrut%"]
        like_clauses = " OR ".join(
            f"LOWER(hc.name) LIKE :vac_{i}" for i in range(len(vacation_terms))
        )
        conditions.append(f"({like_clauses})")
        for i, term in enumerate(vacation_terms):
            params[f"vac_{i}"] = term

        where = " AND ".join(conditions)

        totals_q = text(
            f"SELECT COUNT(DISTINCT hm.c_bpartner_id) AS total_empleados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS total_monto, "
            f"COUNT(*) AS total_ocurrencias "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_empleados": row[0] if row else 0,
            "total_monto": float(row[1]) if row else 0.0,
            "total_ocurrencias": row[2] if row else 0,
        }

        if totals["total_empleados"] == 0:
            totals["nota"] = (
                "No se encontraron conceptos de vacaciones en nómina para este período. "
                "Los conceptos buscados incluyen: vacacion, bono vacacional, dias disfrutados."
            )

        by_concept_q = text(
            f"SELECT hc.name AS concepto, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto, "
            f"COUNT(*) AS ocurrencias "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"WHERE {where} "
            f"GROUP BY hc.name ORDER BY monto DESC"
        )
        by_concept = [
            {
                "concepto": r[0],
                "empleados": r[1],
                "monto": float(r[2]),
                "ocurrencias": r[3],
            }
            for r in db.execute(by_concept_q, params).fetchall()
        ]

        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto, "
            f"COUNT(*) AS ocurrencias "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"LEFT JOIN adempiere.ad_org o ON hm.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY monto DESC"
        )
        by_org = [
            {
                "organizacion": r[0],
                "empleados": r[1],
                "monto": float(r[2]),
                "ocurrencias": r[3],
            }
            for r in db.execute(by_org_q, params).fetchall()
        ]

        detail_q = text(
            f"SELECT bp.name AS empleado, "
            f"hc.name AS concepto, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"JOIN adempiere.c_bpartner bp ON hm.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name, hc.name ORDER BY monto DESC LIMIT 30"
        )
        detail = [
            {
                "empleado": r[0],
                "concepto": r[1],
                "monto": float(r[2]),
            }
            for r in db.execute(detail_q, params).fetchall()
        ]

        return {
            "totales": totals,
            "por_concepto": by_concept,
            "por_organizacion": by_org,
            "detalle_empleados": detail,
        }
    finally:
        db.close()

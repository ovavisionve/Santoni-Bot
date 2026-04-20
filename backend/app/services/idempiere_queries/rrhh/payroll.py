"""Payroll + attendance queries against hr_process / hr_movement / hr_concept."""

from sqlalchemy import text

from ..common import _add_date_filter, _add_org_filter, _get_session


def build_payroll_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Payroll summary from iDempiere hr_process + hr_movement."""
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "hp.docstatus IN ('CO', 'CL')",
            "hp.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "hp")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "hp.dateacct")
        where = " AND ".join(conditions)

        totals_q = text(
            f"SELECT COUNT(DISTINCT hp.hr_process_id) AS total_procesos, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados_procesados, "
            f"COALESCE(SUM(CASE WHEN hm.amount > 0 THEN hm.amount ELSE 0 END), 0) AS total_devengado, "
            f"COALESCE(SUM(CASE WHEN hm.amount < 0 THEN ABS(hm.amount) ELSE 0 END), 0) AS total_deducciones "
            f"FROM adempiere.hr_process hp "
            f"LEFT JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id "
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_procesos": row[0] if row else 0,
            "empleados_procesados": row[1] if row else 0,
            "total_devengado": float(row[2]) if row else 0.0,
            "total_deducciones": float(row[3]) if row else 0.0,
        }
        totals["neto_a_pagar"] = totals["total_devengado"] - totals["total_deducciones"]

        by_payroll_q = text(
            f"SELECT COALESCE(hpy.name, 'Sin tipo') AS nomina, "
            f"COUNT(DISTINCT hp.hr_process_id) AS procesos, "
            f"COALESCE(SUM(hm.amount), 0) AS total "
            f"FROM adempiere.hr_process hp "
            f"LEFT JOIN adempiere.hr_payroll hpy ON hp.hr_payroll_id = hpy.hr_payroll_id "
            f"LEFT JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id "
            f"WHERE {where} "
            f"GROUP BY hpy.name ORDER BY total DESC"
        )
        by_payroll = [
            {"nomina": r[0], "procesos": r[1], "total": float(r[2])}
            for r in db.execute(by_payroll_q, params).fetchall()
        ]

        by_concept_q = text(
            f"SELECT hc.name AS concepto, "
            f"COALESCE(SUM(hm.amount), 0) AS total, "
            f"COUNT(*) AS movimientos "
            f"FROM adempiere.hr_process hp "
            f"JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"WHERE {where} "
            f"GROUP BY hc.name ORDER BY ABS(SUM(hm.amount)) DESC LIMIT 20"
        )
        by_concept = [
            {"concepto": r[0], "total": float(r[1]), "movimientos": r[2]}
            for r in db.execute(by_concept_q, params).fetchall()
        ]

        return {
            "totales": totals,
            "por_tipo_nomina": by_payroll,
            "conceptos_principales": by_concept,
        }
    finally:
        db.close()


def build_attendance_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Attendance/absence indicators from hr_movement concepts.

    Looks for payroll concepts related to absences (inasistencia, falta,
    permiso, reposo, etc.) and summarises them by type and organisation.
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "hp.docstatus IN ('CO', 'CL')",
            "hp.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "hm")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "hp.dateacct")

        absence_terms = [
            "%ausent%", "%ausencia%", "%inasist%", "%falta%",
            "%permiso%", "%reposo%", "%incapacidad%", "%licencia%",
        ]
        like_clauses = " OR ".join(
            f"LOWER(hc.name) LIKE :abs_{i}" for i in range(len(absence_terms))
        )
        conditions.append(f"({like_clauses})")
        for i, term in enumerate(absence_terms):
            params[f"abs_{i}"] = term

        where = " AND ".join(conditions)

        # NOTE: hm.qty is always 0 for absence concepts in Santoni's iDempiere.
        # We use ABS(hm.amount) for monetary impact and COUNT(*) for occurrences.
        by_concept_q = text(
            f"SELECT hc.name AS concepto, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados_afectados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto_bs, "
            f"COUNT(*) AS registros "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"WHERE {where} "
            f"GROUP BY hc.name ORDER BY registros DESC LIMIT 20"
        )
        by_concept = [
            {
                "concepto": r[0],
                "empleados_afectados": r[1],
                "monto_bs": float(r[2]),
                "ocurrencias": r[3],
            }
            for r in db.execute(by_concept_q, params).fetchall()
        ]

        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados_afectados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto_bs, "
            f"COUNT(*) AS registros "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"LEFT JOIN adempiere.ad_org o ON hm.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY registros DESC"
        )
        by_org = [
            {
                "organizacion": r[0],
                "empleados_afectados": r[1],
                "monto_bs": float(r[2]),
                "ocurrencias": r[3],
            }
            for r in db.execute(by_org_q, params).fetchall()
        ]

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

        total_afectados = sum(c["empleados_afectados"] for c in by_concept)
        tasa = (total_afectados / total_activos * 100) if total_activos else 0

        total_ocurrencias = sum(c["ocurrencias"] for c in by_concept)
        totals = {
            "empleados_activos": total_activos,
            "empleados_con_ausencias": total_afectados,
            "total_ocurrencias": total_ocurrencias,
            "tasa_ausentismo_pct": round(tasa, 2),
            "conceptos_encontrados": len(by_concept),
            "nota_horas": "No se dispone de horas-hombre en el sistema de nómina. Los datos se expresan en ocurrencias y monto (Bs.).",
        }

        if not by_concept:
            totals["nota"] = (
                "No se encontraron conceptos de ausentismo en nómina para este período. "
                "Los conceptos buscados incluyen: inasistencia, falta, permiso, "
                "reposo, incapacidad, licencia."
            )

        return {
            "totales": totals,
            "por_concepto": by_concept,
            "por_organizacion": by_org,
        }
    finally:
        db.close()

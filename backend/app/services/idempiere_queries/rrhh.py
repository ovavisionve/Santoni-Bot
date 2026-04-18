"""HR queries: employees, birthdays, payroll, attendance, turnover, vacations."""

from sqlalchemy import text

from .common import (
    _add_currency_filter,
    _add_date_filter,
    _add_org_filter,
    _add_org_name_filter,
    _convert_value,
    _get_session,
    _rows_to_dicts,
    _ALLOC_JOIN,
    _OPEN_EXPR,
    _IDEMPIERE_DEMO_ORGS,
    _SANTONI_ORG_FILTER,
    execute_idempiere_query,
    logger,
)

# ---------------------------------------------------------------------------
# RRHH (Human Resources)
# ---------------------------------------------------------------------------

def build_employee_summary(org_ids: list[int] | None = None) -> dict:
    """Employee summary from iDempiere using the OFFICIAL view lve_empleadosactivos.

    FIX RRHH-200 (10/Abr/2026): esta función consultaba hr_employee directamente
    lo cual contaba múltiples filas por persona (una por período de nómina) y
    no aplicaba los filtros de negocio que aplica el reporte oficial de Santoni.
    Resultado: el bot reportaba ~2x más empleados de los reales.

    Ejemplo: INPROA SANTONI tenía 457 en el bot vs 258 en el reporte oficial.

    La view lve_empleadosactivos es la fuente oficial — es la misma que usan
    los reportes LVE_EmpleadosActivos que los supervisores de Santoni ven todos
    los días. Incluye 32 columnas con todo pre-calculado:
      ad_org_id, name, cargo, departamento, birthday, sueldo, edad, tservicio, etc.

    La view solo contiene empleados ACTIVOS (no inactivos). Para inactivos hay
    una view separada: lve_empleadosinactivos.
    """
    db = IdempiereSession()
    try:
        conditions = ["1=1"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "v")
        where = " AND ".join(conditions)

        # Totales: la view solo tiene activos, así que "total" = "activos"
        totals_q = text(
            f"SELECT COUNT(*) AS total FROM adempiere.lve_empleadosactivos v "
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        total_activos = row[0] if row else 0
        totals = {
            "total": total_activos,
            "activos": total_activos,
            "inactivos": 0,  # esta view no incluye inactivos
        }

        # Por organización
        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Organización') AS organizacion, "
            f"COUNT(*) AS total, "
            f"COUNT(*) AS activos "
            f"FROM adempiere.lve_empleadosactivos v "
            f"LEFT JOIN adempiere.ad_org o ON v.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY total DESC"
        )
        by_org = [
            {"organizacion": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_org_q, params).fetchall()
        ]

        # Por departamento (la view ya tiene la columna "departamento")
        by_dept_q = text(
            f"SELECT COALESCE(v.departamento, 'Sin Departamento') AS departamento, "
            f"COUNT(*) AS total, "
            f"COUNT(*) AS activos "
            f"FROM adempiere.lve_empleadosactivos v "
            f"WHERE {where} "
            f"GROUP BY v.departamento ORDER BY total DESC LIMIT 20"
        )
        by_dept = [
            {"departamento": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_dept_q, params).fetchall()
        ]

        # Por cargo (la view ya tiene la columna "cargo")
        by_job_q = text(
            f"SELECT COALESCE(v.cargo, 'Sin Cargo') AS cargo, "
            f"COUNT(*) AS total, "
            f"COUNT(*) AS activos "
            f"FROM adempiere.lve_empleadosactivos v "
            f"WHERE {where} "
            f"GROUP BY v.cargo ORDER BY total DESC LIMIT 30"
        )
        by_job = [
            {"cargo": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_job_q, params).fetchall()
        ]

        return {
            "totales": totals,
            "por_organizacion": by_org,
            "por_departamento": by_dept,
            "por_cargo": by_job,
        }
    finally:
        db.close()


def build_employee_list(
    org_ids: list[int] | None = None,
    cargo_search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """List of active employees from iDempiere — official LVE view.

    FIX RRHH-203 (10/Abr/2026): migrado de hr_employee a lve_empleadosactivos.
    La view oficial ya tiene una fila por empleado activo (sin DISTINCT ON),
    ya tiene las columnas cargo/departamento/organizacion/fecha_ingreso
    pre-calculadas, y solo incluye empleados REALMENTE activos según la
    lógica de negocio oficial de Santoni.

    Antes: 457 empleados en INPROA SANTONI (muchos ex-empleados y duplicados)
    Ahora: 258 empleados reales (coincide con el reporte LVE_EmpleadosActivos)
    """
    db = _get_session(date_from=date_from, date_to=date_to)
    try:
        conditions = ["1=1"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "v")

        if cargo_search:
            # Match palabra-por-palabra con ILIKE en v.cargo
            words = cargo_search.strip().split()
            for i, word in enumerate(words):
                stem = word.rstrip("s")
                if stem.endswith("e") and word.endswith("es") and len(stem) > 3:
                    stem = stem[:-1]
                key = f"cargo_w{i}"
                conditions.append(f"v.cargo ILIKE :{key}")
                params[key] = f"%{stem}%"

        if date_from:
            conditions.append("v.startdate >= :date_from")
            params["date_from"] = date_from
        if date_to:
            conditions.append("v.startdate <= :date_to")
            params["date_to"] = date_to

        where = " AND ".join(conditions)

        q = text(
            f"SELECT v.name AS nombre, v.value AS codigo, "
            f"COALESCE(o.name, '') AS organizacion, "
            f"COALESCE(v.departamento, '') AS departamento, "
            f"COALESCE(v.cargo, '') AS cargo, "
            f"v.startdate AS fecha_ingreso "
            f"FROM adempiere.lve_empleadosactivos v "
            f"LEFT JOIN adempiere.ad_org o ON v.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"ORDER BY v.name"
        )
        rows = db.execute(q, params).fetchall()

        results = [
            {
                "nombre": r[0],
                "codigo": r[1],
                "organizacion": r[2],
                "departamento": r[3],
                "cargo": r[4],
                "fecha_ingreso": str(r[5]) if r[5] else "",
            }
            for r in rows
        ]
        # When filtering by cargo, allow more results; otherwise cap at 100
        limit = 200 if cargo_search else 100
        return results[:limit]
    finally:
        db.close()


def build_birthday_list(
    mes: int | None = None,
    org_ids: list[int] | None = None,
) -> list[dict]:
    """List employees whose birthday falls in the given month.

    FIX RRHH-202 (10/Abr/2026): esta función consultaba hr_employee + ad_user
    con JOIN LATERAL para obtener el birthday. Problema: al combinarse con la
    multiplicación de filas de hr_employee (una por período de nómina), algunos
    empleados aparecían duplicados en la respuesta. Ej: GONZALEZ GONZALEZ JOSE
    GREGORIO aparecía 7 veces en los cumpleañeros de mayo.

    Además, usaba hr_employee.isactive='Y' lo que incluía ex-empleados que
    nunca fueron marcados como inactivos → nombres inventados en respuestas.

    La view lve_empleadosactivos:
      - Tiene una sola fila por empleado activo (sin duplicados)
      - Tiene la columna birthday directamente (sin JOIN con ad_user)
      - Solo incluye empleados REALMENTE activos según la lógica de negocio
        oficial de Santoni
    """
    db = _get_session(mes=mes)
    try:
        conditions = ["v.birthday IS NOT NULL"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "v")

        if mes:
            conditions.append("EXTRACT(MONTH FROM v.birthday) = :mes")
            params["mes"] = mes

        where = " AND ".join(conditions)

        q = text(
            f"SELECT v.name AS nombre, "
            f"EXTRACT(DAY FROM v.birthday)::int AS dia, "
            f"EXTRACT(MONTH FROM v.birthday)::int AS mes, "
            f"COALESCE(v.departamento, '') AS departamento, "
            f"COALESCE(o.name, '') AS organizacion, "
            f"COALESCE(v.cargo, '') AS cargo "
            f"FROM adempiere.lve_empleadosactivos v "
            f"LEFT JOIN adempiere.ad_org o ON v.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"ORDER BY EXTRACT(DAY FROM v.birthday), v.name"
        )
        rows = db.execute(q, params).fetchall()

        results = [
            {
                "nombre": r[0],
                "dia": r[1],
                "mes": r[2],
                "departamento": r[3],
                "organizacion": r[4],
                "cargo": r[5],
            }
            for r in rows
        ]
        return results
    finally:
        db.close()


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

        # Process summary
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

        # By payroll type
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

        # Top concepts
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

        # Filter concepts related to absence / attendance
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

        # Summary by concept
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

        # Summary by org
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

        # Total active employees for rate calculation
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


def build_turnover_summary(
    anio: int | None = None,
    org_ids: list[int] | None = None,
) -> dict:
    """Employee turnover (rotation) from hr_employee enddate.

    Counts employees whose enddate falls within the given year as 'bajas'.
    Calculates turnover rate = bajas / total_activos * 100.
    """
    from datetime import datetime

    if not anio:
        anio = datetime.now().year

    db = _get_session(anio=anio)
    try:
        # Bajas (employees with enddate in the given year)
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

        # Bajas by org
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

        # Total active employees for rate
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

        # Filter concepts related to vacations
        vacation_terms = ["%vacacion%", "%bono vacacional%", "%dias disfrut%"]
        like_clauses = " OR ".join(
            f"LOWER(hc.name) LIKE :vac_{i}" for i in range(len(vacation_terms))
        )
        conditions.append(f"({like_clauses})")
        for i, term in enumerate(vacation_terms):
            params[f"vac_{i}"] = term

        where = " AND ".join(conditions)

        # Totals
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

        # By concept
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

        # By organization
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

        # Detail: top 30 employees with vacation amounts
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


# ---------------------------------------------------------------------------

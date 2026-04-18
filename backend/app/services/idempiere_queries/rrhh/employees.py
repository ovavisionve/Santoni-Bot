"""Employee-level queries: summary, list, birthdays.

All three use the OFFICIAL LVE view `lve_empleadosactivos` (see RRHH-200/202/203
fixes, 10/Abr/2026). The view contains ONE row per active employee with
pre-calculated cargo, departamento, birthday, sueldo, edad, tservicio, etc.
"""

from sqlalchemy import text

from app.database import IdempiereSession

from ..common import _add_org_filter, _get_session


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

        totals_q = text(
            f"SELECT COUNT(*) AS total FROM adempiere.lve_empleadosactivos v "
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        total_activos = row[0] if row else 0
        totals = {
            "total": total_activos,
            "activos": total_activos,
            "inactivos": 0,
        }

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

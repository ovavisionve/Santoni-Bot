#!/usr/bin/env python3
"""
Verificación completa de datos RRHH contra iDempiere.

Compara las queries del agente RRHH con los datos reales para identificar
discrepancias en: conteo de empleados, cumpleañeros, vacaciones, ausentismo, nómina.

Uso:
    docker compose exec backend python scripts/verify_rrhh.py
    docker compose exec backend python scripts/verify_rrhh.py --check cumpleaneros
    docker compose exec backend python scripts/verify_rrhh.py --check empleados
    docker compose exec backend python scripts/verify_rrhh.py --check vacaciones
    docker compose exec backend python scripts/verify_rrhh.py --check ausentismo
    docker compose exec backend python scripts/verify_rrhh.py --check nomina
"""

import argparse
from datetime import datetime

from sqlalchemy import text

from app.database import IdempiereSession


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def header(title: str):
    print(f"\n{Colors.BOLD}{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}{Colors.RESET}")


def subheader(title: str):
    print(f"\n  {Colors.CYAN}{title}{Colors.RESET}")
    print(f"  {'-'*60}")


def row(label: str, value, fmt: str = ""):
    if isinstance(value, float):
        formatted = f"{value:,.2f}" if not fmt else fmt.format(value)
    else:
        formatted = str(value)
    print(f"  {label:<45} {Colors.BOLD}{formatted}{Colors.RESET}")


def table(rows: list[dict], max_rows: int = 50):
    if not rows:
        print(f"  {Colors.YELLOW}(sin datos){Colors.RESET}")
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(str(c)), max(len(str(r.get(c, ""))[:40]) for r in rows[:max_rows])) for c in cols}
    widths = {c: min(w, 40) for c, w in widths.items()}
    hdr = "  " + " | ".join(str(c).ljust(widths[c]) for c in cols)
    print(hdr)
    print("  " + "-" * len(hdr))
    for r in rows[:max_rows]:
        vals = " | ".join(str(r.get(c, ""))[:40].ljust(widths[c]) for c in cols)
        print(f"  {vals}")
    if len(rows) > max_rows:
        print(f"  ... y {len(rows) - max_rows} filas más")


# ============================================================
# 1. EMPLEADOS - Conteo real vs lo que reporta el bot
# ============================================================
def check_empleados(db):
    header("EMPLEADOS: CONTEO REAL")

    # --- Método 1: DISTINCT c_bpartner_id en hr_employee (como usa el agente) ---
    subheader("Método 1: hr_employee DISTINCT c_bpartner_id (query del agente)")
    q1 = text("""
        SELECT COUNT(DISTINCT e.c_bpartner_id) AS total
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
    """)
    r = db.execute(q1).fetchone()
    row("Total (hr_employee DISTINCT bp)", r[0])

    # --- Método 2: Sin filtro bp.isactive ---
    q1b = text("""
        SELECT COUNT(DISTINCT e.c_bpartner_id) AS total
        FROM adempiere.hr_employee e
        WHERE e.isactive = 'Y'
    """)
    r = db.execute(q1b).fetchone()
    row("Total (hr_employee sin filtro bp.isactive)", r[0])

    # --- Método 3: Todos los hr_employee sin filtros ---
    q1c = text("""
        SELECT COUNT(DISTINCT e.c_bpartner_id) AS total
        FROM adempiere.hr_employee e
    """)
    r = db.execute(q1c).fetchone()
    row("Total (hr_employee ALL, sin filtros)", r[0])

    # --- Método 4: c_bpartner con isemployee ---
    q2 = text("""
        SELECT COUNT(*) AS total
        FROM adempiere.c_bpartner bp
        WHERE bp.isactive = 'Y' AND bp.isemployee = 'Y'
    """)
    r = db.execute(q2).fetchone()
    row("Total (c_bpartner isemployee='Y' isactive='Y')", r[0])

    # --- Cuántos registros hr_employee por persona ---
    subheader("Registros hr_employee por persona (distribución)")
    q3 = text("""
        SELECT registros_por_persona, COUNT(*) AS personas
        FROM (
            SELECT c_bpartner_id, COUNT(*) AS registros_por_persona
            FROM adempiere.hr_employee
            WHERE isactive = 'Y'
            GROUP BY c_bpartner_id
        ) sub
        GROUP BY registros_por_persona
        ORDER BY registros_por_persona
    """)
    rows_data = [{"registros_por_persona": r[0], "personas": r[1]} for r in db.execute(q3).fetchall()]
    table(rows_data)

    # --- Por organización (como el agente) ---
    subheader("Por organización (query del agente)")
    q4 = text("""
        SELECT o.name AS organizacion,
               COUNT(DISTINCT e.c_bpartner_id) AS empleados
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id
        WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
        GROUP BY o.name ORDER BY empleados DESC
    """)
    rows_data = [{"organizacion": r[0], "empleados": r[1]} for r in db.execute(q4).fetchall()]
    table(rows_data)
    total = sum(r["empleados"] for r in rows_data)
    row("TOTAL por org", total)

    # --- ¿Hay personas en múltiples organizaciones? ---
    subheader("Personas con registros en MÚLTIPLES organizaciones")
    q5 = text("""
        SELECT bp.name, COUNT(DISTINCT e.ad_org_id) AS num_orgs,
               STRING_AGG(DISTINCT o.name, ', ') AS organizaciones
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id
        WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
        GROUP BY bp.name, bp.c_bpartner_id
        HAVING COUNT(DISTINCT e.ad_org_id) > 1
        ORDER BY num_orgs DESC
        LIMIT 20
    """)
    rows_data = [{"nombre": r[0], "num_orgs": r[1], "organizaciones": r[2]} for r in db.execute(q5).fetchall()]
    row("Personas en múltiples orgs", len(rows_data))
    if rows_data:
        table(rows_data[:10])


# ============================================================
# 2. CUMPLEAÑEROS - Verificar todos los meses
# ============================================================
def check_cumpleaneros(db):
    header("CUMPLEAÑEROS: VERIFICACIÓN POR MES")

    # Total con birthday registrado
    subheader("¿Cuántos empleados tienen birthday en ad_user?")
    q0 = text("""
        SELECT COUNT(DISTINCT bp.c_bpartner_id) AS con_birthday,
               (SELECT COUNT(DISTINCT e.c_bpartner_id) FROM adempiere.hr_employee e
                JOIN adempiere.c_bpartner bp2 ON e.c_bpartner_id = bp2.c_bpartner_id
                WHERE e.isactive = 'Y' AND bp2.isactive = 'Y') AS total_empleados
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        JOIN adempiere.ad_user u ON bp.c_bpartner_id = u.c_bpartner_id
        WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
          AND u.birthday IS NOT NULL
    """)
    r = db.execute(q0).fetchone()
    row("Empleados con birthday registrado", r[0])
    row("Total empleados activos", r[1])
    pct = (r[0] / r[1] * 100) if r[1] else 0
    row("Porcentaje con birthday", f"{pct:.1f}%")

    # Cumpleañeros por mes (todos los meses)
    subheader("Cumpleañeros por mes (usando query del agente)")
    q1 = text("""
        SELECT EXTRACT(MONTH FROM bday.birthday)::int AS mes,
               COUNT(DISTINCT bp.c_bpartner_id) AS empleados
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        JOIN LATERAL (
            SELECT u.birthday FROM adempiere.ad_user u
            WHERE u.c_bpartner_id = bp.c_bpartner_id
            AND u.birthday IS NOT NULL
            ORDER BY u.ad_user_id LIMIT 1
        ) bday ON TRUE
        WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
        GROUP BY EXTRACT(MONTH FROM bday.birthday)
        ORDER BY mes
    """)
    meses_nombres = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                     5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                     9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    rows_data = [{"mes": meses_nombres.get(r[0], r[0]), "empleados": r[1]} for r in db.execute(q1).fetchall()]
    table(rows_data)

    # Verificar meses específicos que fallaron en el chat
    for mes_num, mes_name in [(4, "Abril"), (5, "Mayo"), (8, "Agosto"), (11, "Noviembre")]:
        subheader(f"Cumpleañeros de {mes_name} - TODOS (query del agente)")
        q2 = text(f"""
            SELECT DISTINCT ON (bp.c_bpartner_id)
                   bp.name AS nombre,
                   EXTRACT(DAY FROM bday.birthday)::int AS dia,
                   COALESCE(d.name, '') AS departamento,
                   COALESCE(o.name, '') AS organizacion,
                   COALESCE(j.name, '') AS cargo
            FROM adempiere.hr_employee e
            JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
            JOIN LATERAL (
                SELECT u.birthday FROM adempiere.ad_user u
                WHERE u.c_bpartner_id = bp.c_bpartner_id
                AND u.birthday IS NOT NULL
                ORDER BY u.ad_user_id LIMIT 1
            ) bday ON TRUE
            LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id
            LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id
            LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id
            WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
              AND EXTRACT(MONTH FROM bday.birthday) = :mes
            ORDER BY bp.c_bpartner_id, e.startdate DESC
        """)
        rows_data = [
            {"nombre": r[0], "dia": r[1], "departamento": r[2],
             "organizacion": r[3], "cargo": r[4]}
            for r in db.execute(q2, {"mes": mes_num}).fetchall()
        ]
        rows_data.sort(key=lambda x: x["dia"])
        row(f"Total cumpleañeros {mes_name}", len(rows_data))
        table(rows_data)

        # Solo de INPROA SANTONI
        subheader(f"Cumpleañeros de {mes_name} - solo INPROA SANTONI")
        q3 = text(f"""
            SELECT DISTINCT ON (bp.c_bpartner_id)
                   bp.name AS nombre,
                   EXTRACT(DAY FROM bday.birthday)::int AS dia,
                   COALESCE(d.name, '') AS departamento,
                   COALESCE(j.name, '') AS cargo
            FROM adempiere.hr_employee e
            JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
            JOIN LATERAL (
                SELECT u.birthday FROM adempiere.ad_user u
                WHERE u.c_bpartner_id = bp.c_bpartner_id
                AND u.birthday IS NOT NULL
                ORDER BY u.ad_user_id LIMIT 1
            ) bday ON TRUE
            LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id
            LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id
            LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id
            WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
              AND EXTRACT(MONTH FROM bday.birthday) = :mes
              AND UPPER(o.name) LIKE '%INPROA SANTONI%'
            ORDER BY bp.c_bpartner_id, e.startdate DESC
        """)
        rows_data = [
            {"nombre": r[0], "dia": r[1], "departamento": r[2], "cargo": r[3]}
            for r in db.execute(q3, {"mes": mes_num}).fetchall()
        ]
        rows_data.sort(key=lambda x: x["dia"])
        row(f"INPROA SANTONI - cumpleañeros {mes_name}", len(rows_data))
        table(rows_data)


# ============================================================
# 3. VACACIONES - ¿Qué datos realmente hay?
# ============================================================
def check_vacaciones(db):
    header("VACACIONES: DATOS REALES EN HR_MOVEMENT")

    # Todos los conceptos que contienen 'vacacion'
    subheader("Conceptos de nómina con 'vacacion' (primeros 30)")
    q1 = text("""
        SELECT DISTINCT hc.name, hc.value
        FROM adempiere.hr_concept hc
        WHERE LOWER(hc.name) LIKE '%vacacion%'
           OR LOWER(hc.name) LIKE '%bono vacacional%'
           OR LOWER(hc.name) LIKE '%dias disfrut%'
        ORDER BY hc.name
        LIMIT 30
    """)
    rows_data = [{"nombre": r[0], "codigo": r[1]} for r in db.execute(q1).fetchall()]
    row("Conceptos encontrados", len(rows_data))
    table(rows_data)

    # Datos de vacaciones por mes 2026
    subheader("Vacaciones por mes (2026) - hr_movement")
    q2 = text("""
        SELECT EXTRACT(MONTH FROM hp.dateacct)::int AS mes,
               COUNT(DISTINCT hm.c_bpartner_id) AS empleados,
               COALESCE(SUM(ABS(hm.amount)), 0) AS monto_total,
               COUNT(*) AS ocurrencias
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id
        JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
        WHERE hp.docstatus IN ('CO', 'CL')
          AND hp.isactive = 'Y'
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
          AND (LOWER(hc.name) LIKE '%vacacion%'
               OR LOWER(hc.name) LIKE '%bono vacacional%'
               OR LOWER(hc.name) LIKE '%dias disfrut%')
        GROUP BY EXTRACT(MONTH FROM hp.dateacct)
        ORDER BY mes
    """)
    rows_data = [{"mes": r[0], "empleados": r[1], "monto_total": float(r[2]), "ocurrencias": r[3]}
                 for r in db.execute(q2).fetchall()]
    table(rows_data)

    # Vacaciones por organización (todo 2026)
    subheader("Vacaciones por organización (2026)")
    q3 = text("""
        SELECT COALESCE(o.name, 'Sin Org') AS organizacion,
               COUNT(DISTINCT hm.c_bpartner_id) AS empleados,
               COALESCE(SUM(ABS(hm.amount)), 0) AS monto_total,
               COUNT(*) AS ocurrencias
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id
        JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
        LEFT JOIN adempiere.ad_org o ON hm.ad_org_id = o.ad_org_id
        WHERE hp.docstatus IN ('CO', 'CL')
          AND hp.isactive = 'Y'
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
          AND (LOWER(hc.name) LIKE '%vacacion%'
               OR LOWER(hc.name) LIKE '%bono vacacional%'
               OR LOWER(hc.name) LIKE '%dias disfrut%')
        GROUP BY o.name ORDER BY monto_total DESC
    """)
    rows_data = [{"organizacion": r[0], "empleados": r[1], "monto_total": float(r[2]), "ocurrencias": r[3]}
                 for r in db.execute(q3).fetchall()]
    table(rows_data)

    # Top 20 empleados con vacaciones (detalle)
    subheader("Top 20 empleados con vacaciones (2026)")
    q4 = text("""
        SELECT bp.name AS empleado,
               hc.name AS concepto,
               COALESCE(SUM(ABS(hm.amount)), 0) AS monto
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id
        JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
        JOIN adempiere.c_bpartner bp ON hm.c_bpartner_id = bp.c_bpartner_id
        WHERE hp.docstatus IN ('CO', 'CL')
          AND hp.isactive = 'Y'
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
          AND (LOWER(hc.name) LIKE '%vacacion%'
               OR LOWER(hc.name) LIKE '%bono vacacional%'
               OR LOWER(hc.name) LIKE '%dias disfrut%')
        GROUP BY bp.name, hc.name ORDER BY monto DESC LIMIT 20
    """)
    rows_data = [{"empleado": r[0], "concepto": r[1], "monto": float(r[2])} for r in db.execute(q4).fetchall()]
    table(rows_data)


# ============================================================
# 4. AUSENTISMO - ¿Qué datos realmente hay?
# ============================================================
def check_ausentismo(db):
    header("AUSENTISMO: DATOS REALES EN HR_MOVEMENT")

    # Febrero 2026 (el que reportó el bot)
    subheader("Ausentismo febrero 2026 (query del agente)")
    q1 = text("""
        SELECT hc.name AS concepto,
               COUNT(DISTINCT hm.c_bpartner_id) AS empleados_afectados,
               COALESCE(SUM(ABS(hm.amount)), 0) AS monto_bs,
               COUNT(*) AS ocurrencias
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id
        JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
        WHERE hp.docstatus IN ('CO', 'CL')
          AND hp.isactive = 'Y'
          AND EXTRACT(MONTH FROM hp.dateacct) = 2
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
          AND (LOWER(hc.name) LIKE '%ausent%'
               OR LOWER(hc.name) LIKE '%ausencia%'
               OR LOWER(hc.name) LIKE '%inasist%'
               OR LOWER(hc.name) LIKE '%falta%'
               OR LOWER(hc.name) LIKE '%permiso%'
               OR LOWER(hc.name) LIKE '%reposo%'
               OR LOWER(hc.name) LIKE '%incapacidad%'
               OR LOWER(hc.name) LIKE '%licencia%')
        GROUP BY hc.name ORDER BY ocurrencias DESC
    """)
    rows_data = [{"concepto": r[0], "empleados": r[1], "monto_bs": float(r[2]), "ocurrencias": r[3]}
                 for r in db.execute(q1).fetchall()]
    table(rows_data)
    total_occ = sum(r["ocurrencias"] for r in rows_data)
    total_emp = sum(r["empleados"] for r in rows_data)
    total_monto = sum(r["monto_bs"] for r in rows_data)
    row("Total ocurrencias", total_occ)
    row("Total empleados (suma, con duplicados)", total_emp)
    row("Total monto (Bs.)", total_monto)

    # Empleados activos para tasa
    subheader("Total empleados activos (para calcular tasa)")
    q2 = text("""
        SELECT COUNT(DISTINCT e.c_bpartner_id)
        FROM adempiere.hr_employee e
        WHERE e.isactive = 'Y'
    """)
    r = db.execute(q2).fetchone()
    row("Empleados activos (hr_employee)", r[0])

    q2b = text("""
        SELECT COUNT(DISTINCT e.c_bpartner_id)
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
    """)
    r = db.execute(q2b).fetchone()
    row("Empleados activos (hr_employee + bp.isactive)", r[0])

    # Por organización
    subheader("Ausentismo por organización - febrero 2026")
    q3 = text("""
        SELECT COALESCE(o.name, 'Sin Org') AS organizacion,
               COUNT(DISTINCT hm.c_bpartner_id) AS empleados,
               COALESCE(SUM(ABS(hm.amount)), 0) AS monto_bs,
               COUNT(*) AS ocurrencias
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id
        JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
        LEFT JOIN adempiere.ad_org o ON hm.ad_org_id = o.ad_org_id
        WHERE hp.docstatus IN ('CO', 'CL')
          AND hp.isactive = 'Y'
          AND EXTRACT(MONTH FROM hp.dateacct) = 2
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
          AND (LOWER(hc.name) LIKE '%ausent%'
               OR LOWER(hc.name) LIKE '%ausencia%'
               OR LOWER(hc.name) LIKE '%inasist%'
               OR LOWER(hc.name) LIKE '%falta%'
               OR LOWER(hc.name) LIKE '%permiso%'
               OR LOWER(hc.name) LIKE '%reposo%'
               OR LOWER(hc.name) LIKE '%incapacidad%'
               OR LOWER(hc.name) LIKE '%licencia%')
        GROUP BY o.name ORDER BY ocurrencias DESC
    """)
    rows_data = [{"organizacion": r[0], "empleados": r[1], "monto_bs": float(r[2]), "ocurrencias": r[3]}
                 for r in db.execute(q3).fetchall()]
    table(rows_data)


# ============================================================
# 5. NÓMINA - Verificar datos reales
# ============================================================
def check_nomina(db):
    header("NÓMINA: DATOS REALES")

    # Nómina febrero 2026 (lo que reportó el bot)
    subheader("Nómina febrero 2026 (query del agente)")
    q1 = text("""
        SELECT COUNT(DISTINCT hp.hr_process_id) AS procesos,
               COUNT(DISTINCT hm.c_bpartner_id) AS empleados,
               COALESCE(SUM(CASE WHEN hm.amount > 0 THEN hm.amount ELSE 0 END), 0) AS devengado,
               COALESCE(SUM(CASE WHEN hm.amount < 0 THEN ABS(hm.amount) ELSE 0 END), 0) AS deducciones
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id
        WHERE hp.docstatus IN ('CO', 'CL')
          AND hp.isactive = 'Y'
          AND EXTRACT(MONTH FROM hp.dateacct) = 2
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
    """)
    r = db.execute(q1).fetchone()
    row("Procesos de nómina", r[0])
    row("Empleados procesados", r[1])
    row("Total devengado (Bs.)", float(r[2]))
    row("Total deducciones (Bs.)", float(r[3]))
    row("Neto a pagar (Bs.)", float(r[2]) - float(r[3]))

    # Procesos de nómina (detalle)
    subheader("Procesos de nómina febrero 2026 (detalle)")
    q2 = text("""
        SELECT hp.documentno, hp.dateacct::date,
               py.name AS nomina,
               hp.docstatus,
               COUNT(DISTINCT hm.c_bpartner_id) AS empleados,
               COALESCE(SUM(hm.amount), 0) AS monto_neto
        FROM adempiere.hr_process hp
        JOIN adempiere.hr_payroll py ON hp.hr_payroll_id = py.hr_payroll_id
        LEFT JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id
        WHERE hp.docstatus IN ('CO', 'CL')
          AND hp.isactive = 'Y'
          AND EXTRACT(MONTH FROM hp.dateacct) = 2
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
        GROUP BY hp.documentno, hp.dateacct, py.name, hp.docstatus
        ORDER BY hp.dateacct
    """)
    rows_data = [{"documento": r[0], "fecha": str(r[1]), "nomina": r[2],
                  "status": r[3], "empleados": r[4], "monto_neto": float(r[5])}
                 for r in db.execute(q2).fetchall()]
    table(rows_data)

    # ¿Cuántos empleados distintos en nómina (para comparar con 702 vs 1056)?
    subheader("Total empleados DISTINTOS en nómina 2026 (todos los meses)")
    q3 = text("""
        SELECT COUNT(DISTINCT hm.c_bpartner_id) AS empleados_en_nomina
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id
        WHERE hp.docstatus IN ('CO', 'CL')
          AND hp.isactive = 'Y'
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
    """)
    r = db.execute(q3).fetchone()
    row("Empleados distintos en nómina 2026", r[0])

    # Por mes
    subheader("Empleados procesados por mes (2026)")
    q4 = text("""
        SELECT EXTRACT(MONTH FROM hp.dateacct)::int AS mes,
               COUNT(DISTINCT hm.c_bpartner_id) AS empleados,
               COALESCE(SUM(CASE WHEN hm.amount > 0 THEN hm.amount ELSE 0 END), 0) AS devengado
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id
        WHERE hp.docstatus IN ('CO', 'CL')
          AND hp.isactive = 'Y'
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
        GROUP BY EXTRACT(MONTH FROM hp.dateacct)
        ORDER BY mes
    """)
    rows_data = [{"mes": r[0], "empleados": r[1], "devengado": float(r[2])} for r in db.execute(q4).fetchall()]
    table(rows_data)


# ============================================================
# 6. TABLAS HR - Estructura y conteos básicos
# ============================================================
def check_tablas(db):
    header("TABLAS RRHH: ESTRUCTURA Y CONTEOS")

    tables_to_check = [
        ("hr_employee", "Empleados"),
        ("hr_department", "Departamentos"),
        ("hr_job", "Cargos"),
        ("hr_process", "Procesos nómina"),
        ("hr_movement", "Movimientos nómina"),
        ("hr_concept", "Conceptos nómina"),
        ("hr_payroll", "Nóminas definidas"),
    ]

    for tbl, desc in tables_to_check:
        q = text(f"SELECT COUNT(*) FROM adempiere.{tbl}")
        try:
            r = db.execute(q).fetchone()
            row(f"{tbl} ({desc})", f"{r[0]:,} registros")
        except Exception as e:
            row(f"{tbl} ({desc})", f"ERROR: {e}")

    # Columnas de ad_user (verificar que birthday existe)
    subheader("Columnas de ad_user (birthday)")
    q = text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'adempiere'
          AND table_name = 'ad_user'
          AND column_name IN ('birthday', 'c_bpartner_id', 'name', 'ad_user_id')
        ORDER BY column_name
    """)
    rows_data = [{"columna": r[0], "tipo": r[1]} for r in db.execute(q).fetchall()]
    table(rows_data)

    # Verificar ad_user duplicados por c_bpartner_id
    subheader("ad_user: ¿cuántos tienen múltiples registros por bpartner?")
    q = text("""
        SELECT COUNT(*) AS bpartners_con_multiples_users
        FROM (
            SELECT c_bpartner_id, COUNT(*) AS cnt
            FROM adempiere.ad_user
            WHERE c_bpartner_id IS NOT NULL
            GROUP BY c_bpartner_id
            HAVING COUNT(*) > 1
        ) sub
    """)
    r = db.execute(q).fetchone()
    row("BPartners con múltiples ad_user", r[0])


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Verificación RRHH contra iDempiere")
    parser.add_argument(
        "--check", default="all",
        help="Qué verificar: all, empleados, cumpleaneros, vacaciones, ausentismo, nomina, tablas"
    )
    args = parser.parse_args()

    print(f"\n{'#'*70}")
    print(f"  VERIFICACIÓN RRHH - iDempiere")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'#'*70}")

    db = IdempiereSession()
    try:
        checks = {
            "empleados": check_empleados,
            "cumpleaneros": check_cumpleaneros,
            "vacaciones": check_vacaciones,
            "ausentismo": check_ausentismo,
            "nomina": check_nomina,
            "tablas": check_tablas,
        }

        if args.check == "all":
            for fn in checks.values():
                fn(db)
        elif args.check in checks:
            checks[args.check](db)
        else:
            print(f"Check no reconocido: {args.check}")
            print(f"Opciones: {', '.join(checks.keys())}, all")
            return

    finally:
        db.close()

    print(f"\n{'#'*70}")
    print(f"  VERIFICACIÓN COMPLETA")
    print(f"{'#'*70}")


if __name__ == "__main__":
    main()

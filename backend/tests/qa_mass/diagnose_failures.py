#!/usr/bin/env python3
"""
Diagnóstico: ¿Los datos de los 12 casos fallidos EXISTEN en iDempiere?

Para cada caso que el bot dijo "no se encontraron datos", ejecuta una query
SQL directa contra iDempiere y muestra si hay datos o no.

Uso:
    docker compose exec backend python tests/qa_mass/diagnose_failures.py
"""

from sqlalchemy import text
from app.database import IdempiereSession


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


CHECKS = [
    {
        "id": 13,
        "pregunta": "Índices de ausentismo enero 2025",
        "sql": """
            SELECT COUNT(*) AS movimientos,
                   COUNT(DISTINCT hm.c_bpartner_id) AS empleados
            FROM adempiere.hr_movement hm
            JOIN adempiere.hr_process hp ON hm.hr_process_id = hp.hr_process_id
            JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
            WHERE hp.docstatus IN ('CO','CL')
              AND EXTRACT(MONTH FROM hp.dateacct) = 1
              AND EXTRACT(YEAR FROM hp.dateacct) = 2025
              AND (hc.name ILIKE '%ausent%' OR hc.name ILIKE '%inasist%'
                   OR hc.name ILIKE '%falta%' OR hc.name ILIKE '%permiso%'
                   OR hc.name ILIKE '%reposo%')
        """,
        "desc": "hr_movement con conceptos de ausencia en enero 2025",
    },
    {
        "id": 64,
        "pregunta": "Saldo cuenta 1101 febrero 2026",
        "sql": """
            SELECT ev.value, ev.name,
                   COUNT(*) AS movimientos,
                   COALESCE(SUM(fa.amtacctdr), 0) AS debito,
                   COALESCE(SUM(fa.amtacctcr), 0) AS credito
            FROM adempiere.fact_acct fa
            JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id
            WHERE ev.value LIKE '1.1.01%' OR ev.value LIKE '1101%' OR ev.value LIKE '1.01.01%'
            GROUP BY ev.value, ev.name
            ORDER BY movimientos DESC
            LIMIT 10
        """,
        "desc": "fact_acct con cuentas que matcheen '1101' (varios formatos)",
    },
    {
        "id": 142,
        "pregunta": "¿Cuánto se vendió de harinas en febrero 2026?",
        "sql": """
            SELECT p.value AS codigo, p.name AS producto,
                   COUNT(DISTINCT il.c_invoice_id) AS facturas,
                   COALESCE(SUM(il.linenetamt), 0) AS total
            FROM adempiere.c_invoiceline il
            JOIN adempiere.c_invoice i ON il.c_invoice_id = i.c_invoice_id
            JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
            WHERE i.issotrx = 'Y'
              AND i.docstatus IN ('CO','CL')
              AND (p.name ILIKE '%harina%' OR p.name ILIKE '%flour%')
              AND i.dateinvoiced >= '2026-02-01'
              AND i.dateinvoiced < '2026-03-01'
            GROUP BY p.value, p.name
            ORDER BY total DESC
            LIMIT 10
        """,
        "desc": "Productos con 'harina' en nombre, vendidos feb 2026",
    },
    {
        "id": 146,
        "pregunta": "Comparativo de cobranza vs metas enero 2026",
        "sql": """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'adempiere'
              AND (table_name ILIKE '%meta%' OR table_name ILIKE '%goal%'
                   OR table_name ILIKE '%target%' OR table_name ILIKE '%budget%'
                   OR table_name ILIKE '%presupuesto%')
            ORDER BY table_name
        """,
        "desc": "Tablas que puedan contener metas/presupuestos",
    },
    {
        "id": 149,
        "pregunta": "Clientes activos vs inactivos de InproMaiz",
        "sql": """
            SELECT
                CASE WHEN bp.isactive = 'Y' THEN 'Activo' ELSE 'Inactivo' END AS estado,
                COUNT(*) AS clientes
            FROM adempiere.c_bpartner bp
            JOIN adempiere.ad_org o ON bp.ad_org_id = o.ad_org_id
            WHERE bp.iscustomer = 'Y'
              AND o.name ILIKE '%inpromaiz%'
            GROUP BY bp.isactive
        """,
        "desc": "Clientes activos/inactivos de InproMaiz (c_bpartner.iscustomer='Y')",
    },
    {
        "id": 156,
        "pregunta": "Visitas a clientes enero 2026",
        "sql": """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'adempiere'
              AND (table_name ILIKE '%visit%' OR table_name ILIKE '%visita%'
                   OR table_name ILIKE '%activity%' OR table_name ILIKE '%actividad%')
            ORDER BY table_name
        """,
        "desc": "Tablas que puedan contener visitas/actividades",
    },
    {
        "id": 167,
        "pregunta": "Provisiones de pasivos laborales enero 2025",
        "sql": """
            SELECT hc.name AS concepto, COUNT(*) AS movimientos,
                   COALESCE(SUM(hm.amount), 0) AS total
            FROM adempiere.hr_movement hm
            JOIN adempiere.hr_process hp ON hm.hr_process_id = hp.hr_process_id
            JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
            WHERE hp.docstatus IN ('CO','CL')
              AND EXTRACT(MONTH FROM hp.dateacct) = 1
              AND EXTRACT(YEAR FROM hp.dateacct) = 2025
              AND (hc.name ILIKE '%provision%' OR hc.name ILIKE '%pasivo%'
                   OR hc.name ILIKE '%prestacion%' OR hc.name ILIKE '%antigüedad%')
            GROUP BY hc.name
            ORDER BY total DESC
            LIMIT 10
        """,
        "desc": "Conceptos de nómina tipo provisión/pasivo enero 2025",
    },
    {
        "id": 169,
        "pregunta": "Asistencias del día de hoy",
        "sql": """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'adempiere'
              AND (table_name ILIKE '%attend%' OR table_name ILIKE '%asistenc%'
                   OR table_name ILIKE '%marca%' OR table_name ILIKE '%clock%'
                   OR table_name ILIKE '%biometric%')
            ORDER BY table_name
        """,
        "desc": "Tablas de asistencia/marcaje/biométrico",
    },
    {
        "id": 170,
        "pregunta": "Costo total de rotación del 2025",
        "sql": """
            SELECT
                COUNT(*) AS empleados_salidos,
                MIN(e.enddate) AS primera_salida,
                MAX(e.enddate) AS ultima_salida
            FROM adempiere.hr_employee e
            JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
            WHERE e.enddate IS NOT NULL
              AND EXTRACT(YEAR FROM e.enddate) = 2025
        """,
        "desc": "Empleados con enddate en 2025 (rotación = salidas)",
    },
    {
        "id": 171,
        "pregunta": "Calidad de contratación último trimestre",
        "sql": """
            SELECT
                COUNT(*) AS empleados_nuevos,
                MIN(e.startdate) AS primera_contratacion,
                MAX(e.startdate) AS ultima_contratacion
            FROM adempiere.hr_employee e
            WHERE e.startdate >= '2025-10-01'
              AND e.startdate < '2026-01-01'
              AND e.isactive = 'Y'
        """,
        "desc": "Empleados contratados en Q4 2025",
    },
    {
        "id": 373,
        "pregunta": "Ventas del 15/dic/2024 al 15/ene/2025",
        "sql": """
            SELECT
                CASE
                    WHEN i.c_currency_id = 205 THEN 'VES'
                    WHEN i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) THEN 'USD'
                    ELSE 'OTRO'
                END AS moneda,
                COUNT(*) AS facturas,
                COALESCE(SUM(i.grandtotal), 0) AS total
            FROM adempiere.c_invoice i
            JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
            WHERE i.issotrx = 'Y'
              AND i.docstatus IN ('CO','CL')
              AND i.isactive = 'Y'
              AND dt.docbasetype = 'ARI'
              AND i.dateinvoiced >= '2024-12-15'
              AND i.dateinvoiced <= '2025-01-15'
            GROUP BY moneda
        """,
        "desc": "Ventas en rango 15/dic/2024 — 15/ene/2025",
    },
    {
        "id": 395,
        "pregunta": "Nómina INPROA vs InproMaiz enero 2026",
        "sql": """
            SELECT o.name AS organizacion,
                   COUNT(DISTINCT hm.c_bpartner_id) AS empleados,
                   COALESCE(SUM(CASE WHEN hm.amount > 0 THEN hm.amount ELSE 0 END), 0) AS devengado,
                   COALESCE(SUM(CASE WHEN hm.amount < 0 THEN ABS(hm.amount) ELSE 0 END), 0) AS deducciones
            FROM adempiere.hr_movement hm
            JOIN adempiere.hr_process hp ON hm.hr_process_id = hp.hr_process_id
            JOIN adempiere.ad_org o ON hm.ad_org_id = o.ad_org_id
            WHERE hp.docstatus IN ('CO','CL')
              AND EXTRACT(MONTH FROM hp.dateacct) = 1
              AND EXTRACT(YEAR FROM hp.dateacct) = 2026
              AND (o.name ILIKE '%inproa%' OR o.name ILIKE '%inpromaiz%')
            GROUP BY o.name
            ORDER BY devengado DESC
        """,
        "desc": "Nómina enero 2026 para INPROA y InproMaiz por separado",
    },
]


def main():
    print(f"\n{Colors.BOLD}{'=' * 70}")
    print(f"  DIAGNÓSTICO: ¿Los datos existen en iDempiere?")
    print(f"  12 casos que el bot dijo 'no se encontraron datos'")
    print(f"{'=' * 70}{Colors.RESET}\n")

    db = IdempiereSession()
    try:
        for check in CHECKS:
            print(f"{Colors.BOLD}#{check['id']}: {check['pregunta']}{Colors.RESET}")
            print(f"  {Colors.DIM}{check['desc']}{Colors.RESET}")
            try:
                rows = db.execute(text(check["sql"])).fetchall()
                if not rows:
                    print(f"  {Colors.RED}❌ SIN DATOS — la query no devolvió filas{Colors.RESET}")
                else:
                    cols = db.execute(text(check["sql"])).keys()
                    col_names = list(cols) if hasattr(cols, '__iter__') else []

                    # Re-execute to get column names properly
                    result = db.execute(text(check["sql"]))
                    col_names = [c for c in result.keys()]
                    rows = result.fetchall()

                    print(f"  {Colors.GREEN}✅ HAY DATOS — {len(rows)} filas{Colors.RESET}")
                    # Show first 5 rows
                    if col_names:
                        header = " | ".join(str(c)[:20] for c in col_names)
                        print(f"  {header}")
                        print(f"  {'-' * len(header)}")
                    for row in rows[:5]:
                        vals = " | ".join(str(v)[:20] for v in row)
                        print(f"  {vals}")
                    if len(rows) > 5:
                        print(f"  ... ({len(rows)} filas total)")
            except Exception as exc:
                print(f"  {Colors.RED}⚠️  ERROR SQL: {exc}{Colors.RESET}")
            print()
    finally:
        db.close()

    print(f"{Colors.BOLD}{'=' * 70}{Colors.RESET}")


if __name__ == "__main__":
    main()

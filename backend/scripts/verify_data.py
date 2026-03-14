#!/usr/bin/env python3
"""
Verificación directa de datos contra iDempiere.

Ejecuta queries SQL directamente contra la base de datos de iDempiere
y muestra los resultados para comparar con las respuestas del bot.

Uso:
    docker compose exec backend python scripts/verify_data.py
    docker compose exec backend python scripts/verify_data.py --check produccion
    docker compose exec backend python scripts/verify_data.py --check all
"""

import argparse
from datetime import datetime, timedelta

from sqlalchemy import text

# Bootstrap Django-style: import app config
from app.database import IdempiereSession


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    DIM = "\033[2m"


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


def table(rows: list[dict], max_rows: int = 30):
    if not rows:
        print(f"  {Colors.YELLOW}(sin datos){Colors.RESET}")
        return
    cols = list(rows[0].keys())
    # Calculate column widths
    widths = {c: max(len(str(c)), max(len(str(r.get(c, ""))) for r in rows[:max_rows])) for c in cols}
    # Cap widths
    widths = {c: min(w, 40) for c, w in widths.items()}
    # Header
    hdr = " | ".join(str(c).ljust(widths[c])[:widths[c]] for c in cols)
    print(f"  {hdr}")
    print(f"  {'-'*len(hdr)}")
    # Rows
    for i, r in enumerate(rows[:max_rows]):
        line = " | ".join(str(r.get(c, "")).ljust(widths[c])[:widths[c]] for c in cols)
        print(f"  {line}")
    if len(rows) > max_rows:
        print(f"  {Colors.DIM}... y {len(rows) - max_rows} filas más{Colors.RESET}")


# ---------------------------------------------------------------------------
# Verificaciones
# ---------------------------------------------------------------------------

def check_empleados(db):
    """Verificar conteo de empleados activos."""
    header("VERIFICACIÓN: EMPLEADOS")

    subheader("Total empleados activos (DISTINCT c_bpartner_id)")
    q = text("""
        SELECT COUNT(DISTINCT e.c_bpartner_id) AS total_activos
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
    """)
    r = db.execute(q).fetchone()
    row("Total empleados activos", r[0])

    subheader("Por organización")
    q = text("""
        SELECT o.name AS organizacion,
               COUNT(DISTINCT e.c_bpartner_id) AS empleados
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id
        WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
        GROUP BY o.name ORDER BY empleados DESC
    """)
    rows = [{"organizacion": r[0], "empleados": r[1]} for r in db.execute(q).fetchall()]
    table(rows)
    total = sum(r["empleados"] for r in rows)
    row("TOTAL", total)


def check_arroz_paddy(db):
    """Verificar compras de arroz paddy 2026."""
    header("VERIFICACIÓN: COMPRAS ARROZ PADDY 2026")

    subheader("Totales de compras (c_order, arroz paddy, 2026)")
    q = text("""
        SELECT COUNT(DISTINCT o.c_order_id) AS total_guias,
               COALESCE(SUM(ol.qtyordered), 0) AS total_kg,
               COALESCE(SUM(ol.linenetamt), 0) AS total_monto
        FROM adempiere.c_order o
        JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id
        JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id
        WHERE o.issotrx = 'N'
          AND o.docstatus IN ('CO', 'CL')
          AND o.isactive = 'Y'
          AND EXTRACT(YEAR FROM o.dateordered) = 2026
          AND (LOWER(p.name) LIKE '%arroz paddy%' OR LOWER(p.name) LIKE '%arroz%paddy%')
    """)
    r = db.execute(q).fetchone()
    row("Total guías", r[0])
    row("Total kg", r[1])
    row("Total toneladas", float(r[1]) / 1000)
    row("Total monto (Bs.)", r[2])

    subheader("Por producto (nombre exacto en iDempiere)")
    q = text("""
        SELECT p.name AS producto,
               COUNT(DISTINCT o.c_order_id) AS guias,
               COALESCE(SUM(ol.qtyordered), 0) AS kg,
               COALESCE(SUM(ol.linenetamt), 0) AS monto
        FROM adempiere.c_order o
        JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id
        JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id
        WHERE o.issotrx = 'N'
          AND o.docstatus IN ('CO', 'CL')
          AND o.isactive = 'Y'
          AND EXTRACT(YEAR FROM o.dateordered) = 2026
          AND (LOWER(p.name) LIKE '%arroz paddy%' OR LOWER(p.name) LIKE '%arroz%paddy%')
        GROUP BY p.name ORDER BY monto DESC
    """)
    rows = [{"producto": r[0], "guias": r[1], "kg": float(r[2]), "monto": float(r[3])} for r in db.execute(q).fetchall()]
    table(rows)


def check_maiz_inpromaiz(db):
    """Verificar compras de maíz en InproMaiz."""
    header("VERIFICACIÓN: COMPRAS DE MAÍZ - INPROMAIZ 2026")

    subheader("Productos con 'maíz' o 'maiz' en nombre (todos)")
    q = text("""
        SELECT DISTINCT p.name
        FROM adempiere.m_product p
        WHERE LOWER(p.name) LIKE '%ma_z%'
           OR p.name ILIKE '%maiz%'
        ORDER BY p.name
    """)
    rows = [{"producto": r[0]} for r in db.execute(q).fetchall()]
    table(rows)

    subheader("Compras de maíz en InproMaiz (2026)")
    q = text("""
        SELECT p.name AS producto,
               COUNT(DISTINCT o.c_order_id) AS guias,
               COALESCE(SUM(ol.qtyordered), 0) AS kg,
               COALESCE(SUM(ol.linenetamt), 0) AS monto
        FROM adempiere.c_order o
        JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id
        JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id
        JOIN adempiere.ad_org org ON o.ad_org_id = org.ad_org_id
        WHERE o.issotrx = 'N'
          AND o.docstatus IN ('CO', 'CL')
          AND o.isactive = 'Y'
          AND EXTRACT(YEAR FROM o.dateordered) = 2026
          AND (p.name ILIKE '%maiz%' OR p.name ILIKE '%maíz%')
          AND org.name ILIKE '%InproMaiz%'
        GROUP BY p.name ORDER BY monto DESC
    """)
    rows = [{"producto": r[0], "guias": r[1], "kg": float(r[2]), "monto": float(r[3])} for r in db.execute(q).fetchall()]
    table(rows)
    if rows:
        row("TOTAL kg", sum(r["kg"] for r in rows))
        row("TOTAL monto", sum(r["monto"] for r in rows))


def check_cuentas_por_pagar(db):
    """Verificar cuentas por pagar."""
    header("VERIFICACIÓN: CUENTAS POR PAGAR")

    subheader("Facturas de compra pendientes (ispaid='N')")
    q = text("""
        SELECT COALESCE(c.iso_code, 'VES') AS moneda,
               COUNT(*) AS facturas,
               COALESCE(SUM(i.grandtotal), 0) AS total
        FROM adempiere.c_invoice i
        LEFT JOIN adempiere.c_currency c ON i.c_currency_id = c.c_currency_id
        WHERE i.issotrx = 'N'
          AND i.docstatus IN ('CO', 'CL')
          AND i.ispaid = 'N'
          AND i.isactive = 'Y'
        GROUP BY c.iso_code ORDER BY total DESC
    """)
    rows = [{"moneda": r[0], "facturas": r[1], "total": float(r[2])} for r in db.execute(q).fetchall()]
    table(rows)
    row("TOTAL facturas", sum(r["facturas"] for r in rows))


def check_cuentas_por_cobrar(db):
    """Verificar cuentas por cobrar vencidas."""
    header("VERIFICACIÓN: CUENTAS POR COBRAR VENCIDAS")

    subheader("Facturas de venta pendientes vencidas")
    q = text("""
        SELECT COALESCE(c.iso_code, 'VES') AS moneda,
               COUNT(*) AS facturas,
               COALESCE(SUM(i.grandtotal), 0) AS total
        FROM adempiere.c_invoice i
        LEFT JOIN adempiere.c_currency c ON i.c_currency_id = c.c_currency_id
        LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id
        WHERE i.issotrx = 'Y'
          AND i.docstatus IN ('CO', 'CL')
          AND i.ispaid = 'N'
          AND i.isactive = 'Y'
          AND (i.dateinvoiced + CASE WHEN COALESCE(pt.netdays, 0) = 0 THEN 30 ELSE pt.netdays END) < CURRENT_DATE
        GROUP BY c.iso_code
    """)
    rows = [{"moneda": r[0], "facturas": r[1], "total": float(r[2])} for r in db.execute(q).fetchall()]
    if rows:
        table(rows)
    else:
        print(f"  {Colors.YELLOW}No hay facturas de venta vencidas actualmente{Colors.RESET}")

    subheader("Facturas de venta pendientes (NO vencidas)")
    q = text("""
        SELECT COALESCE(c.iso_code, 'VES') AS moneda,
               COUNT(*) AS facturas,
               COALESCE(SUM(i.grandtotal), 0) AS total
        FROM adempiere.c_invoice i
        LEFT JOIN adempiere.c_currency c ON i.c_currency_id = c.c_currency_id
        WHERE i.issotrx = 'Y'
          AND i.docstatus IN ('CO', 'CL')
          AND i.ispaid = 'N'
          AND i.isactive = 'Y'
        GROUP BY c.iso_code
    """)
    rows = [{"moneda": r[0], "facturas": r[1], "total": float(r[2])} for r in db.execute(q).fetchall()]
    table(rows)


def check_produccion(db):
    """Verificar movimientos de inventario (producción).

    Usa la misma lógica que build_production_summary: m_inout con movementtype.
    """
    header("VERIFICACIÓN: PRODUCCIÓN / MOVIMIENTOS DE INVENTARIO")

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Totales de marzo 2026 por tipo de movimiento (misma query que el agente)
    subheader("Marzo 2026 - Totales por tipo de movimiento")
    q = text("""
        SELECT
            SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones_mp,
            SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos_pt,
            SUM(CASE WHEN io.movementtype IN ('M+','M-') THEN 1 ELSE 0 END) AS mov_internos,
            COUNT(*) AS total
        FROM adempiere.m_inout io
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
          AND EXTRACT(MONTH FROM io.movementdate) = 3
          AND EXTRACT(YEAR FROM io.movementdate) = 2026
    """)
    r = db.execute(q).fetchone()
    row("Recepciones MP (V+)", r[0])
    row("Despachos PT (C-)", r[1])
    row("Movimientos internos (M+/M-)", r[2])
    row("TOTAL movimientos", r[3])

    # Hoy
    subheader(f"HOY ({today}) por tipo de movimiento")
    q_today = text("""
        SELECT
            SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones,
            SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos,
            COUNT(*) AS total
        FROM adempiere.m_inout io
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
          AND io.movementdate::date = :today
    """)
    r = db.execute(q_today, {"today": today}).fetchone()
    row("Recepciones hoy", r[0])
    row("Despachos hoy", r[1])
    row("Total hoy", r[2])

    # Ayer
    subheader(f"AYER ({yesterday}) por tipo de movimiento")
    q_ayer = text("""
        SELECT
            SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones,
            SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos,
            COUNT(*) AS total
        FROM adempiere.m_inout io
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
          AND io.movementdate::date = :yesterday
    """)
    r = db.execute(q_ayer, {"yesterday": yesterday}).fetchone()
    row("Recepciones ayer", r[0])
    row("Despachos ayer", r[1])
    row("Total ayer", r[2])

    # Desglose por fecha marzo 2026
    subheader("Fechas con movimientos en marzo 2026")
    q_dates = text("""
        SELECT io.movementdate::date AS fecha,
               SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones,
               SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos,
               COUNT(*) AS total
        FROM adempiere.m_inout io
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
          AND EXTRACT(MONTH FROM io.movementdate) = 3
          AND EXTRACT(YEAR FROM io.movementdate) = 2026
        GROUP BY io.movementdate::date ORDER BY fecha
    """)
    rows = [{"fecha": str(r[0]), "recepciones": r[1], "despachos": r[2], "total": r[3]}
            for r in db.execute(q_dates).fetchall()]
    if rows:
        table(rows)
        row("TOTAL docs marzo", sum(r["total"] for r in rows))
        row("Días con movimientos", len(rows))
    else:
        print(f"  {Colors.YELLOW}Sin movimientos en marzo 2026{Colors.RESET}")

    # Hoy por organización
    subheader(f"HOY ({today}) por organización")
    q_today_org = text("""
        SELECT o.name AS organizacion,
               SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones,
               SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos,
               COUNT(*) AS total
        FROM adempiere.m_inout io
        JOIN adempiere.ad_org o ON io.ad_org_id = o.ad_org_id
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
          AND io.movementdate::date = :today
        GROUP BY o.name ORDER BY total DESC
    """)
    rows = [{"organizacion": r[0], "recepciones": r[1], "despachos": r[2], "total": r[3]}
            for r in db.execute(q_today_org, {"today": today}).fetchall()]
    if rows:
        table(rows)
    else:
        print(f"  {Colors.YELLOW}Sin movimientos hoy{Colors.RESET}")

    # InproMaiz hoy
    subheader(f"InproMaiz HOY ({today})")
    q_inpro_today = text("""
        SELECT SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones,
               SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos,
               COUNT(*) AS total
        FROM adempiere.m_inout io
        JOIN adempiere.ad_org o ON io.ad_org_id = o.ad_org_id
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
          AND io.movementdate::date = :today
          AND o.name ILIKE '%InproMaiz%'
    """)
    r = db.execute(q_inpro_today, {"today": today}).fetchone()
    row("Recepciones InproMaiz hoy", r[0] or 0)
    row("Despachos InproMaiz hoy", r[1] or 0)
    row("Total InproMaiz hoy", r[2] or 0)

    # InproMaiz últimos 7 días
    subheader("InproMaiz últimos 7 días")
    q_inpro_7d = text("""
        SELECT io.movementdate::date AS fecha,
               SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones,
               SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos,
               COUNT(*) AS total
        FROM adempiere.m_inout io
        JOIN adempiere.ad_org o ON io.ad_org_id = o.ad_org_id
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
          AND io.movementdate::date >= (CURRENT_DATE - INTERVAL '7 days')::date
          AND o.name ILIKE '%InproMaiz%'
        GROUP BY io.movementdate::date ORDER BY fecha DESC
    """)
    rows = [{"fecha": str(r[0]), "recepciones": r[1], "despachos": r[2], "total": r[3]}
            for r in db.execute(q_inpro_7d).fetchall()]
    if rows:
        table(rows)
    else:
        print(f"  {Colors.YELLOW}Sin movimientos InproMaiz últimos 7 días{Colors.RESET}")

    # Top productos marzo
    subheader("Top 10 productos movidos en marzo 2026")
    q_prods = text("""
        SELECT p.name AS producto,
               SUM(CASE WHEN io.movementtype = 'V+' THEN iol.movementqty ELSE 0 END) AS recibido_kg,
               SUM(CASE WHEN io.movementtype = 'C-' THEN iol.movementqty ELSE 0 END) AS despachado_kg
        FROM adempiere.m_inout io
        JOIN adempiere.m_inoutline iol ON io.m_inout_id = iol.m_inout_id
        JOIN adempiere.m_product p ON iol.m_product_id = p.m_product_id
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO', 'CL')
          AND EXTRACT(MONTH FROM io.movementdate) = 3
          AND EXTRACT(YEAR FROM io.movementdate) = 2026
        GROUP BY p.name ORDER BY (SUM(ABS(iol.movementqty))) DESC LIMIT 10
    """)
    rows = [{"producto": r[0], "recibido_kg": float(r[1]), "despachado_kg": float(r[2])}
            for r in db.execute(q_prods).fetchall()]
    table(rows)

    # PP_ORDER check
    subheader("PP_ORDER (Órdenes de producción) - ¿existe la tabla?")
    try:
        q5 = text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'adempiere' AND table_name = 'pp_order'
        """)
        exists = db.execute(q5).fetchone()[0]
        if exists:
            q6 = text("SELECT COUNT(*) FROM adempiere.pp_order WHERE docstatus IN ('CO', 'CL')")
            r = db.execute(q6).fetchone()
            row("Total órdenes de producción completadas", r[0])
        else:
            print(f"  {Colors.YELLOW}La tabla pp_order NO existe en iDempiere{Colors.RESET}")
    except Exception:
        db.rollback()
        print(f"  {Colors.YELLOW}Error consultando pp_order{Colors.RESET}")

    # Check m_production as alternative
    subheader("M_PRODUCTION (Producción alternativa) - ¿existe?")
    q8 = text("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'adempiere' AND table_name = 'm_production'
    """)
    exists2 = db.execute(q8).fetchone()[0]
    if exists2:
        q9 = text("""
            SELECT COUNT(*) AS total,
                   MIN(movementdate::date) AS primera,
                   MAX(movementdate::date) AS ultima
            FROM adempiere.m_production
        """)
        r = db.execute(q9).fetchone()
        row("Total registros m_production", r[0])
        row("Primer registro", r[1])
        row("Último registro", r[2])
    else:
        print(f"  {Colors.YELLOW}La tabla m_production NO existe en iDempiere{Colors.RESET}")


def check_vacaciones(db):
    """Verificar datos de vacaciones enero 2026."""
    header("VERIFICACIÓN: VACACIONES ENERO 2026")

    subheader("Conceptos de nómina con 'vacacion' en nombre")
    q = text("""
        SELECT hc.hr_concept_id, hc.value, hc.name
        FROM adempiere.hr_concept hc
        WHERE LOWER(hc.name) LIKE '%vacacion%'
           OR LOWER(hc.name) LIKE '%bono vacacional%'
           OR LOWER(hc.name) LIKE '%dias disfrut%'
        ORDER BY hc.name
    """)
    rows = [{"id": r[0], "codigo": r[1], "nombre": r[2]} for r in db.execute(q).fetchall()]
    table(rows)

    subheader("Movimientos de vacaciones enero 2026")
    q2 = text("""
        SELECT COUNT(DISTINCT hm.c_bpartner_id) AS empleados,
               COALESCE(SUM(ABS(hm.amount)), 0) AS monto_total,
               COUNT(*) AS ocurrencias
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id
        JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
        WHERE hp.docstatus IN ('CO', 'CL')
          AND hp.isactive = 'Y'
          AND EXTRACT(MONTH FROM hp.dateacct) = 1
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
          AND (LOWER(hc.name) LIKE '%vacacion%'
               OR LOWER(hc.name) LIKE '%bono vacacional%'
               OR LOWER(hc.name) LIKE '%dias disfrut%')
    """)
    r = db.execute(q2).fetchone()
    row("Empleados con vacaciones", r[0])
    row("Monto total (Bs.)", r[1])
    row("Total ocurrencias", r[2])


def check_cumpleaneros(db):
    """Verificar cumpleañeros de marzo."""
    header("VERIFICACIÓN: CUMPLEAÑEROS DE MARZO")

    q = text("""
        SELECT COUNT(*) AS total
        FROM (
            SELECT DISTINCT ON (e.c_bpartner_id) e.c_bpartner_id
            FROM adempiere.hr_employee e
            JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
            JOIN adempiere.ad_user u ON bp.c_bpartner_id = u.c_bpartner_id
            WHERE e.isactive = 'Y'
              AND bp.isactive = 'Y'
              AND u.birthday IS NOT NULL
              AND EXTRACT(MONTH FROM u.birthday) = 3
        ) sub
    """)
    r = db.execute(q).fetchone()
    row("Cumpleañeros de marzo", r[0])

    subheader("Primeros 10 cumpleañeros de marzo (DISTINCT)")
    q2 = text("""
        SELECT DISTINCT ON (e.c_bpartner_id)
               bp.name AS nombre,
               EXTRACT(DAY FROM u.birthday)::int AS dia,
               EXTRACT(MONTH FROM u.birthday)::int AS mes
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        JOIN adempiere.ad_user u ON bp.c_bpartner_id = u.c_bpartner_id
        WHERE e.isactive = 'Y'
          AND bp.isactive = 'Y'
          AND u.birthday IS NOT NULL
          AND EXTRACT(MONTH FROM u.birthday) = 3
        ORDER BY e.c_bpartner_id, EXTRACT(DAY FROM u.birthday)
        LIMIT 10
    """)
    rows = [{"nombre": r[0], "dia": r[1], "mes": r[2]} for r in db.execute(q2).fetchall()]
    table(rows)


def check_nomina(db):
    """Verificar nómina febrero 2026."""
    header("VERIFICACIÓN: NÓMINA FEBRERO 2026")

    # Usa la misma lógica que build_payroll_summary: amount > 0 = devengado, amount < 0 = deducción
    q = text("""
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
    r = db.execute(q).fetchone()
    row("Procesos de nómina", r[0])
    row("Empleados procesados", r[1])
    row("Total devengado (Bs.)", r[2])
    row("Total deducciones (Bs.)", r[3])
    row("Neto a pagar (Bs.)", float(r[2]) - float(r[3]))


def check_m_production(db):
    """Verificar producciones reales desde m_production + m_productionline."""
    header("VERIFICACIÓN: M_PRODUCTION (PRODUCCIONES REALES)")

    # Estructura de la tabla
    subheader("Estructura m_productionline (columnas clave)")
    try:
        q = text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'adempiere' AND table_name = 'm_productionline'
              AND column_name IN ('isendproduct', 'movementqty', 'm_product_id',
                                  'm_production_id', 'm_locator_id', 'line')
            ORDER BY column_name
        """)
        rows = [{"columna": r[0], "tipo": r[1]} for r in db.execute(q).fetchall()]
        table(rows)
        has_isendproduct = any(r["columna"] == "isendproduct" for r in rows)
        if not has_isendproduct:
            print(f"  {Colors.RED}¡ALERTA! Columna 'isendproduct' NO encontrada en m_productionline{Colors.RESET}")
    except Exception as exc:
        db.rollback()
        print(f"  {Colors.RED}Error: {exc}{Colors.RESET}")

    # Totales generales
    subheader("Totales generales m_production")
    q = text("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN docstatus IN ('CO', 'CL') THEN 1 ELSE 0 END) AS completadas,
               MIN(movementdate::date) AS primera,
               MAX(movementdate::date) AS ultima,
               COALESCE(SUM(CASE WHEN docstatus IN ('CO', 'CL') THEN productionqty ELSE 0 END), 0) AS qty_total
        FROM adempiere.m_production
    """)
    r = db.execute(q).fetchone()
    row("Total registros", r[0])
    row("Completadas (CO/CL)", r[1])
    row("Primer registro", r[2])
    row("Último registro", r[3])
    row("Qty total (completadas)", r[4])

    # Marzo 2026
    subheader("Marzo 2026 - Producciones")
    q = text("""
        SELECT COUNT(*) AS producciones,
               COALESCE(SUM(productionqty), 0) AS qty
        FROM adempiere.m_production
        WHERE docstatus IN ('CO', 'CL') AND isactive = 'Y'
          AND EXTRACT(MONTH FROM movementdate) = 3
          AND EXTRACT(YEAR FROM movementdate) = 2026
    """)
    r = db.execute(q).fetchone()
    row("Producciones marzo 2026", r[0])
    row("Cantidad producida", r[1])

    # Top productos terminados (isendproduct = 'Y')
    subheader("Top 10 productos terminados (isendproduct='Y') - 2026")
    try:
        q = text("""
            SELECT p.name AS producto,
                   COUNT(DISTINCT pr.m_production_id) AS producciones,
                   COALESCE(SUM(prl.movementqty), 0) AS qty
            FROM adempiere.m_production pr
            JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id
            JOIN adempiere.m_product p ON prl.m_product_id = p.m_product_id
            WHERE pr.docstatus IN ('CO', 'CL') AND pr.isactive = 'Y'
              AND EXTRACT(YEAR FROM pr.movementdate) = 2026
              AND prl.isendproduct = 'Y' AND prl.movementqty > 0
            GROUP BY p.name ORDER BY qty DESC LIMIT 10
        """)
        rows = [{"producto": r[0], "producciones": r[1], "qty": float(r[2])} for r in db.execute(q).fetchall()]
        table(rows)
    except Exception as exc:
        db.rollback()
        print(f"  {Colors.RED}Error con isendproduct: {exc}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Intentando con movementqty > 0...{Colors.RESET}")
        q = text("""
            SELECT p.name AS producto,
                   COUNT(DISTINCT pr.m_production_id) AS producciones,
                   COALESCE(SUM(prl.movementqty), 0) AS qty
            FROM adempiere.m_production pr
            JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id
            JOIN adempiere.m_product p ON prl.m_product_id = p.m_product_id
            WHERE pr.docstatus IN ('CO', 'CL') AND pr.isactive = 'Y'
              AND EXTRACT(YEAR FROM pr.movementdate) = 2026
              AND prl.movementqty > 0
            GROUP BY p.name ORDER BY qty DESC LIMIT 10
        """)
        rows = [{"producto": r[0], "producciones": r[1], "qty": float(r[2])} for r in db.execute(q).fetchall()]
        table(rows)

    # Top insumos consumidos (isendproduct = 'N' o qty < 0)
    subheader("Top 10 insumos consumidos (isendproduct='N') - 2026")
    try:
        q = text("""
            SELECT p.name AS insumo,
                   COALESCE(SUM(ABS(prl.movementqty)), 0) AS qty_consumida
            FROM adempiere.m_production pr
            JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id
            JOIN adempiere.m_product p ON prl.m_product_id = p.m_product_id
            WHERE pr.docstatus IN ('CO', 'CL') AND pr.isactive = 'Y'
              AND EXTRACT(YEAR FROM pr.movementdate) = 2026
              AND (prl.isendproduct = 'N' OR prl.movementqty < 0)
            GROUP BY p.name ORDER BY qty_consumida DESC LIMIT 10
        """)
        rows = [{"insumo": r[0], "qty_consumida": float(r[1])} for r in db.execute(q).fetchall()]
        table(rows)
    except Exception as exc:
        db.rollback()
        print(f"  {Colors.RED}Error: {exc}{Colors.RESET}")

    # Por organización
    subheader("Por organización - 2026")
    q = text("""
        SELECT org.name AS organizacion,
               COUNT(*) AS producciones,
               COALESCE(SUM(pr.productionqty), 0) AS qty
        FROM adempiere.m_production pr
        JOIN adempiere.ad_org org ON pr.ad_org_id = org.ad_org_id
        WHERE pr.docstatus IN ('CO', 'CL') AND pr.isactive = 'Y'
          AND EXTRACT(YEAR FROM pr.movementdate) = 2026
        GROUP BY org.name ORDER BY producciones DESC
    """)
    rows = [{"organizacion": r[0], "producciones": r[1], "qty": float(r[2])} for r in db.execute(q).fetchall()]
    table(rows)


def check_bom(db):
    """Verificar BOMs / recetas desde pp_product_bom."""
    header("VERIFICACIÓN: PP_PRODUCT_BOM (RECETAS / BILL OF MATERIALS)")

    # Check table exists
    subheader("¿Existen las tablas?")
    q = text("""
        SELECT table_name, (SELECT COUNT(*) FROM information_schema.columns c
                            WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) AS columnas
        FROM information_schema.tables t
        WHERE table_schema = 'adempiere'
          AND table_name IN ('pp_product_bom', 'pp_product_bomline')
        ORDER BY table_name
    """)
    rows = [{"tabla": r[0], "columnas": r[1]} for r in db.execute(q).fetchall()]
    table(rows)
    if len(rows) < 2:
        print(f"  {Colors.RED}¡Tablas BOM no encontradas! No se puede continuar.{Colors.RESET}")
        return

    # Totals
    subheader("Totales BOMs")
    q = text("""
        SELECT COUNT(*) AS total_boms,
               SUM(CASE WHEN isactive = 'Y' THEN 1 ELSE 0 END) AS activas
        FROM adempiere.pp_product_bom
    """)
    r = db.execute(q).fetchone()
    row("Total BOMs", r[0])
    row("BOMs activas", r[1])

    # Total bomlines
    q = text("SELECT COUNT(*) FROM adempiere.pp_product_bomline WHERE isactive = 'Y'")
    r = db.execute(q).fetchone()
    row("Total componentes (activos)", r[0])

    # Sample BOMs with component count
    subheader("Top 15 BOMs por número de componentes")
    q = text("""
        SELECT b.name AS bom_nombre, p.name AS producto, org.name AS organizacion,
               (SELECT COUNT(*) FROM adempiere.pp_product_bomline bl
                WHERE bl.pp_product_bom_id = b.pp_product_bom_id AND bl.isactive = 'Y') AS componentes
        FROM adempiere.pp_product_bom b
        JOIN adempiere.m_product p ON b.m_product_id = p.m_product_id
        JOIN adempiere.ad_org org ON b.ad_org_id = org.ad_org_id
        WHERE b.isactive = 'Y'
        ORDER BY componentes DESC LIMIT 15
    """)
    rows = [{"bom": r[0], "producto": r[1], "org": r[2], "componentes": r[3]}
            for r in db.execute(q).fetchall()]
    table(rows)

    # Sample BOM detail: first BOM with most components
    if rows:
        subheader(f"Ejemplo detalle BOM: {rows[0]['bom']}")
        q = text("""
            SELECT p.name AS componente, bl.qtybom AS cantidad,
                   COALESCE(u.name, '-') AS unidad, bl.componenttype AS tipo
            FROM adempiere.pp_product_bomline bl
            JOIN adempiere.m_product p ON bl.m_product_id = p.m_product_id
            LEFT JOIN adempiere.c_uom u ON bl.c_uom_id = u.c_uom_id
            JOIN adempiere.pp_product_bom b ON bl.pp_product_bom_id = b.pp_product_bom_id
            WHERE b.name = :bom_name AND bl.isactive = 'Y'
            ORDER BY bl.line
        """)
        comps = [{"componente": r[0], "cantidad": float(r[1]) if r[1] else 0,
                  "unidad": r[2], "tipo": r[3]}
                 for r in db.execute(q, {"bom_name": rows[0]["bom"]}).fetchall()]
        table(comps)

    # BOMs por organización
    subheader("BOMs por organización")
    q = text("""
        SELECT org.name AS organizacion, COUNT(*) AS boms
        FROM adempiere.pp_product_bom b
        JOIN adempiere.ad_org org ON b.ad_org_id = org.ad_org_id
        WHERE b.isactive = 'Y'
        GROUP BY org.name ORDER BY boms DESC
    """)
    rows = [{"organizacion": r[0], "boms": r[1]} for r in db.execute(q).fetchall()]
    table(rows)


def check_m_movement(db):
    """Verificar movimientos entre almacenes desde m_movement."""
    header("VERIFICACIÓN: M_MOVEMENT (MOVIMIENTOS ENTRE ALMACENES)")

    # Check table exists
    subheader("Totales m_movement")
    q = text("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN docstatus IN ('CO', 'CL') THEN 1 ELSE 0 END) AS completados,
               MIN(movementdate::date) AS primera,
               MAX(movementdate::date) AS ultima
        FROM adempiere.m_movement
    """)
    r = db.execute(q).fetchone()
    row("Total registros", r[0])
    row("Completados (CO/CL)", r[1])
    row("Primer registro", r[2])
    row("Último registro", r[3])

    # 2026
    subheader("Año 2026 - Movimientos entre almacenes")
    q = text("""
        SELECT COUNT(*) AS movimientos
        FROM adempiere.m_movement
        WHERE docstatus IN ('CO', 'CL') AND isactive = 'Y'
          AND EXTRACT(YEAR FROM movementdate) = 2026
    """)
    r = db.execute(q).fetchone()
    row("Movimientos 2026", r[0])

    # Marzo 2026
    q = text("""
        SELECT COUNT(*) AS movimientos
        FROM adempiere.m_movement
        WHERE docstatus IN ('CO', 'CL') AND isactive = 'Y'
          AND EXTRACT(MONTH FROM movementdate) = 3
          AND EXTRACT(YEAR FROM movementdate) = 2026
    """)
    r = db.execute(q).fetchone()
    row("Movimientos marzo 2026", r[0])

    # Top productos movidos 2026
    subheader("Top 10 productos movidos entre almacenes - 2026")
    q = text("""
        SELECT p.name AS producto,
               SUM(ABS(ml.movementqty)) AS qty_movida,
               COUNT(DISTINCT mv.m_movement_id) AS movimientos
        FROM adempiere.m_movement mv
        JOIN adempiere.m_movementline ml ON mv.m_movement_id = ml.m_movement_id
        JOIN adempiere.m_product p ON ml.m_product_id = p.m_product_id
        WHERE mv.docstatus IN ('CO', 'CL') AND mv.isactive = 'Y'
          AND EXTRACT(YEAR FROM mv.movementdate) = 2026
        GROUP BY p.name ORDER BY qty_movida DESC LIMIT 10
    """)
    rows = [{"producto": r[0], "qty_movida": float(r[1]), "movimientos": r[2]}
            for r in db.execute(q).fetchall()]
    table(rows)

    # Flujo almacén origen → destino
    subheader("Flujo almacén origen → destino (top 10) - 2026")
    q = text("""
        SELECT w_from.name AS origen, w_to.name AS destino,
               COUNT(DISTINCT mv.m_movement_id) AS movimientos,
               SUM(ABS(ml.movementqty)) AS qty
        FROM adempiere.m_movement mv
        JOIN adempiere.m_movementline ml ON mv.m_movement_id = ml.m_movement_id
        JOIN adempiere.m_locator l_from ON ml.m_locator_id = l_from.m_locator_id
        JOIN adempiere.m_warehouse w_from ON l_from.m_warehouse_id = w_from.m_warehouse_id
        JOIN adempiere.m_locator l_to ON ml.m_locatorto_id = l_to.m_locator_id
        JOIN adempiere.m_warehouse w_to ON l_to.m_warehouse_id = w_to.m_warehouse_id
        WHERE mv.docstatus IN ('CO', 'CL') AND mv.isactive = 'Y'
          AND EXTRACT(YEAR FROM mv.movementdate) = 2026
        GROUP BY w_from.name, w_to.name ORDER BY qty DESC LIMIT 10
    """)
    rows = [{"origen": r[0], "destino": r[1], "movimientos": r[2], "qty": float(r[3])}
            for r in db.execute(q).fetchall()]
    table(rows)

    # Por organización
    subheader("Por organización - 2026")
    q = text("""
        SELECT org.name AS organizacion, COUNT(*) AS movimientos
        FROM adempiere.m_movement mv
        JOIN adempiere.ad_org org ON mv.ad_org_id = org.ad_org_id
        WHERE mv.docstatus IN ('CO', 'CL') AND mv.isactive = 'Y'
          AND EXTRACT(YEAR FROM mv.movementdate) = 2026
        GROUP BY org.name ORDER BY movimientos DESC
    """)
    rows = [{"organizacion": r[0], "movimientos": r[1]} for r in db.execute(q).fetchall()]
    table(rows)


def check_stock_arroz_paddy(db):
    """Verificar stock actual de arroz paddy y producto '01-0' - comparar con respuesta del bot."""
    header("VERIFICACIÓN: STOCK ARROZ PADDY + PRODUCTO '01-0'")

    # El bot reportó: 40,750,455.69 kg de Arroz Paddy Acondicionado
    subheader("Stock actual: productos con 'arroz' y 'paddy' en nombre")
    q = text("""
        SELECT p.name AS producto, p.value AS codigo,
               w.name AS almacen, org.name AS organizacion,
               COALESCE(SUM(s.qtyonhand), 0) AS stock_kg
        FROM adempiere.m_storageonhand s
        JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id
        JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id
        JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id
        JOIN adempiere.ad_org org ON l.ad_org_id = org.ad_org_id
        WHERE LOWER(p.name) LIKE '%arroz%paddy%'
          AND s.qtyonhand <> 0
        GROUP BY p.name, p.value, w.name, org.name
        ORDER BY stock_kg DESC
    """)
    rows = [{"producto": r[0], "codigo": r[1], "almacen": r[2], "org": r[3], "stock_kg": float(r[4])}
            for r in db.execute(q).fetchall()]
    table(rows)
    if rows:
        total_paddy = sum(r["stock_kg"] for r in rows)
        row("TOTAL stock arroz paddy (kg)", total_paddy)
        row("TOTAL stock arroz paddy (ton)", total_paddy / 1000)
        print(f"\n  {Colors.CYAN}Bot reportó: 40,750,455.69 kg{Colors.RESET}")

    # Producto "01-0": búsqueda exacta y flexible
    subheader("Producto '01-0': búsqueda en m_product")
    q = text("""
        SELECT p.m_product_id, p.value AS codigo, p.name AS nombre, p.isactive
        FROM adempiere.m_product p
        WHERE p.value LIKE '%01-0%' OR p.name LIKE '%01-0%'
        ORDER BY p.value LIMIT 20
    """)
    rows = [{"id": r[0], "codigo": r[1], "nombre": r[2], "activo": r[3]}
            for r in db.execute(q).fetchall()]
    if rows:
        table(rows)
    else:
        print(f"  {Colors.YELLOW}No se encontró ningún producto con código/nombre '01-0'{Colors.RESET}")

    # Búsqueda más amplia: productos que empiecen con "01"
    subheader("Productos con código que empiece con '01' (primeros 20)")
    q = text("""
        SELECT p.value AS codigo, p.name AS nombre,
               COALESCE((SELECT SUM(s.qtyonhand) FROM adempiere.m_storageonhand s
                         WHERE s.m_product_id = p.m_product_id), 0) AS stock
        FROM adempiere.m_product p
        WHERE p.value LIKE '01%' AND p.isactive = 'Y'
        ORDER BY p.value LIMIT 20
    """)
    rows = [{"codigo": r[0], "nombre": r[1], "stock": float(r[2])} for r in db.execute(q).fetchall()]
    table(rows)

    # Stock total por categoría (arroz-related products with stock)
    subheader("Stock actual: todos los productos con 'arroz' (resumen)")
    q = text("""
        SELECT p.name AS producto, p.value AS codigo,
               COALESCE(SUM(s.qtyonhand), 0) AS stock_kg
        FROM adempiere.m_storageonhand s
        JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id
        WHERE LOWER(p.name) LIKE '%arroz%'
          AND s.qtyonhand <> 0
        GROUP BY p.name, p.value
        ORDER BY stock_kg DESC LIMIT 20
    """)
    rows = [{"producto": r[0], "codigo": r[1], "stock_kg": float(r[2])}
            for r in db.execute(q).fetchall()]
    table(rows)


def check_ventas(db):
    """Verificar datos de ventas (facturación) 2024-hoy."""
    header("VERIFICACIÓN: VENTAS (FACTURACIÓN)")

    cur_label = (
        "CASE WHEN i.c_currency_id = 205 THEN 'Bs.' "
        "WHEN i.c_currency_id IN "
        "(100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) "
        "THEN 'USD' ELSE 'Otro' END"
    )

    # --- Totales por año ---
    subheader("Totales por año (2024-2026)")
    q = text("""
        SELECT EXTRACT(YEAR FROM i.dateinvoiced)::int AS anio,
               SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
               SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS monto_nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                            WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
        FROM adempiere.c_invoice i
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
          AND EXTRACT(YEAR FROM i.dateinvoiced) >= 2024
        GROUP BY EXTRACT(YEAR FROM i.dateinvoiced)
        ORDER BY anio
    """)
    rows = [{"anio": r[0], "facturas": r[1], "nc": r[2],
             "total_facturado": float(r[3]), "monto_nc": float(r[4]),
             "venta_neta": float(r[5])} for r in db.execute(q).fetchall()]
    table(rows)

    # --- Ventas por mes 2026 ---
    subheader("Ventas por mes 2026")
    q = text("""
        SELECT EXTRACT(MONTH FROM i.dateinvoiced)::int AS mes,
               SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
               SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS monto_nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                            WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
        FROM adempiere.c_invoice i
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
        GROUP BY EXTRACT(MONTH FROM i.dateinvoiced)
        ORDER BY mes
    """)
    rows = [{"mes": r[0], "facturas": r[1], "nc": r[2],
             "total_facturado": float(r[3]), "monto_nc": float(r[4]),
             "venta_neta": float(r[5])} for r in db.execute(q).fetchall()]
    table(rows)

    # --- Ventas por moneda 2026 ---
    subheader("Ventas por moneda 2026 (agrupado USD)")
    q = text(f"""
        SELECT {cur_label} AS moneda,
               SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
               SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS monto_nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                            WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
        FROM adempiere.c_invoice i
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
        GROUP BY {cur_label}
        ORDER BY venta_neta DESC
    """)
    rows = [{"moneda": r[0], "facturas": r[1], "nc": r[2],
             "total_facturado": float(r[3]), "monto_nc": float(r[4]),
             "venta_neta": float(r[5])} for r in db.execute(q).fetchall()]
    table(rows)

    # --- Ventas marzo 2026 por moneda ---
    subheader("Marzo 2026 por moneda (para comparar con bot)")
    q = text(f"""
        SELECT {cur_label} AS moneda,
               SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
               SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS monto_nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                            WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
        FROM adempiere.c_invoice i
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 3
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
        GROUP BY {cur_label}
        ORDER BY venta_neta DESC
    """)
    rows = [{"moneda": r[0], "facturas": r[1], "nc": r[2],
             "total_facturado": float(r[3]), "monto_nc": float(r[4]),
             "venta_neta": float(r[5])} for r in db.execute(q).fetchall()]
    table(rows)
    if rows:
        total_fact = sum(r["total_facturado"] for r in rows)
        total_nc = sum(r["monto_nc"] for r in rows)
        total_neta = sum(r["venta_neta"] for r in rows)
        row("TOTAL facturado bruto (todas monedas)", total_fact)
        row("TOTAL notas de crédito", total_nc)
        row("TOTAL venta neta", total_neta)

    # --- Febrero 2026 por moneda ---
    subheader("Febrero 2026 por moneda (para comparar con bot)")
    q = text(f"""
        SELECT {cur_label} AS moneda,
               SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
               SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS monto_nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                            WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
        FROM adempiere.c_invoice i
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
        GROUP BY {cur_label}
        ORDER BY venta_neta DESC
    """)
    rows = [{"moneda": r[0], "facturas": r[1], "nc": r[2],
             "total_facturado": float(r[3]), "monto_nc": float(r[4]),
             "venta_neta": float(r[5])} for r in db.execute(q).fetchall()]
    table(rows)
    if rows:
        total_fact = sum(r["total_facturado"] for r in rows)
        total_nc = sum(r["monto_nc"] for r in rows)
        total_neta = sum(r["venta_neta"] for r in rows)
        row("TOTAL facturado bruto", total_fact)
        row("TOTAL notas de crédito", total_nc)
        row("TOTAL venta neta", total_neta)

    # --- Top 10 clientes marzo 2026 (Bs.) - campos completos ---
    subheader("Top 10 clientes marzo 2026 (Bs.) - campos completos")
    zone_cte = """
        WITH client_zone AS (
            SELECT DISTINCT ON (bpl.c_bpartner_id)
                   bpl.c_bpartner_id, sreg.name AS zona_name
            FROM adempiere.c_bpartner_location bpl
            LEFT JOIN adempiere.c_salesregion sreg
            ON bpl.c_salesregion_id = sreg.c_salesregion_id
            WHERE bpl.isactive = 'Y'
            ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
        )
    """
    q = text(f"""
        {zone_cte}
        SELECT bp.value AS codigo, bp.name AS nombre,
               MIN(COALESCE(cz.zona_name, 'Sin Zona')) AS zona,
               SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
               SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS total_nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                            WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
        FROM adempiere.c_invoice i
        JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
        LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 3
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
          AND i.c_currency_id = 205
        GROUP BY bp.value, bp.name
        ORDER BY venta_neta DESC LIMIT 10
    """)
    rows = [{"codigo": r[0], "nombre": r[1], "zona": r[2], "facturas": r[3], "nc": r[4],
             "facturado": float(r[5]), "total_nc": float(r[6]),
             "venta_neta": float(r[7])} for r in db.execute(q).fetchall()]
    table(rows)

    # --- Top 10 clientes marzo 2026 (USD) - campos completos ---
    usd_ids = "100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017"
    subheader("Top 10 clientes marzo 2026 (USD) - campos completos")
    q = text(f"""
        {zone_cte}
        SELECT bp.value AS codigo, bp.name AS nombre,
               MIN(COALESCE(cz.zona_name, 'Sin Zona')) AS zona,
               SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
               SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS total_nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                            WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
        FROM adempiere.c_invoice i
        JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
        LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 3
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
          AND i.c_currency_id IN ({usd_ids})
        GROUP BY bp.value, bp.name
        ORDER BY venta_neta DESC LIMIT 10
    """)
    rows = [{"codigo": r[0], "nombre": r[1], "zona": r[2], "facturas": r[3], "nc": r[4],
             "facturado": float(r[5]), "total_nc": float(r[6]),
             "venta_neta": float(r[7])} for r in db.execute(q).fetchall()]
    table(rows)

    # --- Top 10 clientes febrero 2026 (Bs.) - campos completos ---
    subheader("Top 10 clientes febrero 2026 (Bs.) - campos completos")
    q = text(f"""
        {zone_cte}
        SELECT bp.value AS codigo, bp.name AS nombre,
               MIN(COALESCE(cz.zona_name, 'Sin Zona')) AS zona,
               SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
               SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS total_nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                            WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
        FROM adempiere.c_invoice i
        JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
        LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
          AND i.c_currency_id = 205
        GROUP BY bp.value, bp.name
        ORDER BY venta_neta DESC LIMIT 10
    """)
    rows = [{"codigo": r[0], "nombre": r[1], "zona": r[2], "facturas": r[3], "nc": r[4],
             "facturado": float(r[5]), "total_nc": float(r[6]),
             "venta_neta": float(r[7])} for r in db.execute(q).fetchall()]
    table(rows)

    # --- Top 10 clientes febrero 2026 (USD) - campos completos ---
    subheader("Top 10 clientes febrero 2026 (USD) - campos completos")
    q = text(f"""
        {zone_cte}
        SELECT bp.value AS codigo, bp.name AS nombre,
               MIN(COALESCE(cz.zona_name, 'Sin Zona')) AS zona,
               SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
               SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS total_nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                            WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
        FROM adempiere.c_invoice i
        JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
        LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 2
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
          AND i.c_currency_id IN ({usd_ids})
        GROUP BY bp.value, bp.name
        ORDER BY venta_neta DESC LIMIT 10
    """)
    rows = [{"codigo": r[0], "nombre": r[1], "zona": r[2], "facturas": r[3], "nc": r[4],
             "facturado": float(r[5]), "total_nc": float(r[6]),
             "venta_neta": float(r[7])} for r in db.execute(q).fetchall()]
    table(rows)

    # --- Ventas por zona marzo 2026 ---
    subheader("Ventas por zona marzo 2026 (Bs., top 15)")
    q = text("""
        WITH client_zone AS (
            SELECT DISTINCT ON (bpl.c_bpartner_id)
                   bpl.c_bpartner_id, sreg.name AS zona_name
            FROM adempiere.c_bpartner_location bpl
            LEFT JOIN adempiere.c_salesregion sreg
            ON bpl.c_salesregion_id = sreg.c_salesregion_id
            WHERE bpl.isactive = 'Y'
            ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC
        )
        SELECT COALESCE(cz.zona_name, 'Sin Zona') AS zona,
               SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas,
               SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS nc,
               COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal
                            WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta
        FROM adempiere.c_invoice i
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        LEFT JOIN client_zone cz ON i.c_bpartner_id = cz.c_bpartner_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.isactive = 'Y'
          AND EXTRACT(MONTH FROM i.dateinvoiced) = 3
          AND EXTRACT(YEAR FROM i.dateinvoiced) = 2026
          AND i.c_currency_id = 205
        GROUP BY cz.zona_name
        ORDER BY venta_neta DESC LIMIT 15
    """)
    rows = [{"zona": r[0], "facturas": r[1], "nc": r[2],
             "venta_neta": float(r[3])} for r in db.execute(q).fetchall()]
    table(rows)


def check_cobranza(db):
    """Verificar datos de cobranza (c_payment) 2024-hoy."""
    header("VERIFICACIÓN: COBRANZA (c_payment)")

    # --- Cobranza por año ---
    subheader("Cobranza por año (2024-2026)")
    q = text("""
        SELECT EXTRACT(YEAR FROM p.datetrx)::int AS anio,
               COUNT(*) AS recibos,
               COALESCE(SUM(p.payamt), 0) AS total_cobrado
        FROM adempiere.c_payment p
        WHERE p.isreceipt = 'Y' AND p.docstatus IN ('CO', 'CL') AND p.isactive = 'Y'
          AND EXTRACT(YEAR FROM p.datetrx) >= 2024
        GROUP BY EXTRACT(YEAR FROM p.datetrx)
        ORDER BY anio
    """)
    rows = [{"anio": r[0], "recibos": r[1], "total_cobrado": float(r[2])}
            for r in db.execute(q).fetchall()]
    table(rows)

    # --- Cobranza por mes 2026 ---
    subheader("Cobranza por mes 2026")
    q = text("""
        SELECT EXTRACT(MONTH FROM p.datetrx)::int AS mes,
               COUNT(*) AS recibos,
               COALESCE(SUM(p.payamt), 0) AS total_cobrado
        FROM adempiere.c_payment p
        WHERE p.isreceipt = 'Y' AND p.docstatus IN ('CO', 'CL') AND p.isactive = 'Y'
          AND EXTRACT(YEAR FROM p.datetrx) = 2026
        GROUP BY EXTRACT(MONTH FROM p.datetrx)
        ORDER BY mes
    """)
    rows = [{"mes": r[0], "recibos": r[1], "total_cobrado": float(r[2])}
            for r in db.execute(q).fetchall()]
    table(rows)

    cur_label = (
        "CASE WHEN p.c_currency_id = 205 THEN 'Bs.' "
        "WHEN p.c_currency_id IN "
        "(100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) "
        "THEN 'USD' ELSE 'Otro' END"
    )

    # --- Cobranza marzo 2026 por moneda ---
    subheader("Cobranza marzo 2026 por moneda (comparar con bot)")
    q = text(f"""
        SELECT {cur_label} AS moneda,
               COUNT(*) AS recibos,
               COALESCE(SUM(p.payamt), 0) AS total_cobrado
        FROM adempiere.c_payment p
        WHERE p.isreceipt = 'Y' AND p.docstatus IN ('CO', 'CL') AND p.isactive = 'Y'
          AND EXTRACT(MONTH FROM p.datetrx) = 3
          AND EXTRACT(YEAR FROM p.datetrx) = 2026
        GROUP BY {cur_label}
        ORDER BY total_cobrado DESC
    """)
    rows = [{"moneda": r[0], "recibos": r[1], "total_cobrado": float(r[2])}
            for r in db.execute(q).fetchall()]
    table(rows)
    if rows:
        total = sum(r["total_cobrado"] for r in rows)
        row("TOTAL cobrado marzo 2026 (todas monedas)", total)

    # --- Cobranza febrero 2026 por moneda ---
    subheader("Cobranza febrero 2026 por moneda")
    q = text(f"""
        SELECT {cur_label} AS moneda,
               COUNT(*) AS recibos,
               COALESCE(SUM(p.payamt), 0) AS total_cobrado
        FROM adempiere.c_payment p
        WHERE p.isreceipt = 'Y' AND p.docstatus IN ('CO', 'CL') AND p.isactive = 'Y'
          AND EXTRACT(MONTH FROM p.datetrx) = 2
          AND EXTRACT(YEAR FROM p.datetrx) = 2026
        GROUP BY {cur_label}
        ORDER BY total_cobrado DESC
    """)
    rows = [{"moneda": r[0], "recibos": r[1], "total_cobrado": float(r[2])}
            for r in db.execute(q).fetchall()]
    table(rows)
    if rows:
        total = sum(r["total_cobrado"] for r in rows)
        row("TOTAL cobrado febrero 2026 (todas monedas)", total)

    # --- Cobranza marzo 2026 por método de pago ---
    subheader("Cobranza marzo 2026 por método de pago")
    q = text("""
        SELECT CASE p.tendertype
            WHEN 'A' THEN 'Depósito Directo'
            WHEN 'B' THEN 'Tarjeta de Débito'
            WHEN 'C' THEN 'Tarjeta de Crédito'
            WHEN 'D' THEN 'Débito Directo'
            WHEN 'E' THEN 'Euro Efectivo'
            WHEN 'G' THEN 'Depósito Bancario'
            WHEN 'K' THEN 'Cheque'
            WHEN 'S' THEN 'Transferencia Empresas'
            WHEN 'T' THEN 'Cuenta'
            WHEN 'W' THEN 'Transferencia'
            WHEN 'X' THEN 'Efectivo'
            WHEN 'Y' THEN 'Dólar Efectivo'
            WHEN 'Z' THEN 'Dólar Transferencia'
            WHEN 'R' THEN 'Dólar IGTF'
            WHEN 'U' THEN 'Euro Transferencia'
            ELSE p.tendertype END AS metodo,
               COUNT(*) AS recibos,
               COALESCE(SUM(p.payamt), 0) AS total
        FROM adempiere.c_payment p
        WHERE p.isreceipt = 'Y' AND p.docstatus IN ('CO', 'CL') AND p.isactive = 'Y'
          AND EXTRACT(MONTH FROM p.datetrx) = 3
          AND EXTRACT(YEAR FROM p.datetrx) = 2026
        GROUP BY p.tendertype ORDER BY total DESC
    """)
    rows = [{"metodo": r[0], "recibos": r[1], "total": float(r[2])}
            for r in db.execute(q).fetchall()]
    table(rows)

    # --- Top 10 clientes cobranza marzo 2026 ---
    subheader("Top 10 clientes cobranza marzo 2026")
    q = text("""
        SELECT bp.name AS cliente,
               COUNT(*) AS recibos,
               COALESCE(SUM(p.payamt), 0) AS total
        FROM adempiere.c_payment p
        JOIN adempiere.c_bpartner bp ON p.c_bpartner_id = bp.c_bpartner_id
        WHERE p.isreceipt = 'Y' AND p.docstatus IN ('CO', 'CL') AND p.isactive = 'Y'
          AND EXTRACT(MONTH FROM p.datetrx) = 3
          AND EXTRACT(YEAR FROM p.datetrx) = 2026
        GROUP BY bp.name ORDER BY total DESC LIMIT 10
    """)
    rows = [{"cliente": r[0], "recibos": r[1], "total": float(r[2])}
            for r in db.execute(q).fetchall()]
    table(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_CHECKS = {
    "empleados": check_empleados,
    "arroz": check_arroz_paddy,
    "maiz": check_maiz_inpromaiz,
    "cxp": check_cuentas_por_pagar,
    "cxc": check_cuentas_por_cobrar,
    "produccion": check_produccion,
    "produccion_real": check_m_production,
    "bom": check_bom,
    "movimientos_almacen": check_m_movement,
    "stock_paddy": check_stock_arroz_paddy,
    "vacaciones": check_vacaciones,
    "cumpleaneros": check_cumpleaneros,
    "nomina": check_nomina,
    "ventas": check_ventas,
    "cobranza": check_cobranza,
}


def main():
    parser = argparse.ArgumentParser(description="Verificar datos directamente contra iDempiere")
    parser.add_argument(
        "--check", default="all",
        help=f"Verificación a ejecutar: {', '.join(ALL_CHECKS.keys())}, all (default: all)",
    )
    args = parser.parse_args()

    print(f"\n{Colors.BOLD}{'#'*70}")
    print(f"  VERIFICACIÓN DIRECTA DE DATOS - iDempiere")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'#'*70}{Colors.RESET}")

    db = IdempiereSession()
    try:
        if args.check == "all":
            for name, fn in ALL_CHECKS.items():
                try:
                    fn(db)
                except Exception as exc:
                    db.rollback()
                    print(f"\n  {Colors.RED}ERROR en {name}: {exc}{Colors.RESET}")
        elif args.check in ALL_CHECKS:
            ALL_CHECKS[args.check](db)
        else:
            print(f"  {Colors.RED}Verificación desconocida: {args.check}{Colors.RESET}")
            print(f"  Opciones: {', '.join(ALL_CHECKS.keys())}, all")
    finally:
        db.close()

    print(f"\n{Colors.BOLD}{'#'*70}")
    print(f"  VERIFICACIÓN COMPLETA")
    print(f"{'#'*70}{Colors.RESET}\n")


if __name__ == "__main__":
    main()

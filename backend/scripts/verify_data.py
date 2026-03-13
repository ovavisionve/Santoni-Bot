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
    "vacaciones": check_vacaciones,
    "cumpleaneros": check_cumpleaneros,
    "nomina": check_nomina,
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

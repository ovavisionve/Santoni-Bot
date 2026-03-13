#!/usr/bin/env python3
"""
Verificación directa de datos en iDempiere.
Ejecuta queries SQL directas (sin pasar por el bot ni el LLM)
para comparar con lo que responde el bot.

Uso:
    docker compose exec backend python scripts/verify_data.py
    docker compose exec backend python scripts/verify_data.py --check empleados
    docker compose exec backend python scripts/verify_data.py --check produccion
"""

import argparse
import sys
import os

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text


def get_idempiere_session():
    """Get a direct session to iDempiere DB."""
    from app.database import IdempiereSession
    return IdempiereSession()


def _print_header(title: str):
    print(f"\n{'=' * 60}")
    print(f"  VERIFICACIÓN: {title}")
    print(f"{'=' * 60}")


def _print_table(rows, headers=None):
    if not rows:
        print("  (sin datos)")
        return
    if headers:
        print("  " + " | ".join(str(h) for h in headers))
        print("  " + "-" * 60)
    for r in rows:
        print("  " + " | ".join(str(v) for v in r))


def check_empleados(db):
    _print_header("EMPLEADOS")

    print("\n  Total empleados activos (DISTINCT c_bpartner_id)")
    q = text("""
        SELECT COUNT(DISTINCT e.c_bpartner_id) AS total
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
    """)
    row = db.execute(q).fetchone()
    print(f"  Total empleados activos  {row[0]}")

    print("\n  Por organización")
    q2 = text("""
        SELECT org.name AS organizacion, COUNT(DISTINCT e.c_bpartner_id) AS empleados
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        JOIN adempiere.ad_org org ON e.ad_org_id = org.ad_org_id
        WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
        GROUP BY org.name ORDER BY empleados DESC
    """)
    rows = db.execute(q2).fetchall()
    _print_table(rows, ["organizacion", "empleados"])
    total = sum(r[1] for r in rows)
    print(f"  TOTAL  {total}")


def check_arroz(db):
    _print_header("COMPRAS ARROZ PADDY 2026")

    print("\n  Totales de compras (c_order, arroz paddy, 2026)")
    q = text("""
        SELECT COUNT(DISTINCT o.c_order_id) AS total_guias,
               COALESCE(SUM(ol.qtyordered), 0) AS total_kg,
               COALESCE(SUM(ol.linenetamt), 0) AS total_monto
        FROM adempiere.c_order o
        JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id
        JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id
        WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') AND o.isactive = 'Y'
          AND EXTRACT(YEAR FROM o.dateordered) = 2026
          AND LOWER(p.name) LIKE '%arroz paddy%'
    """)
    row = db.execute(q).fetchone()
    print(f"  Total guías  {row[0]}")
    print(f"  Total kg     {row[1]:,.3f}")
    print(f"  Total toneladas  {float(row[1]) / 1000:,.2f}")
    print(f"  Total monto (Bs.)  {row[2]}")

    print("\n  Por producto (nombre exacto en iDempiere)")
    q2 = text("""
        SELECT p.name AS producto,
               COUNT(DISTINCT o.c_order_id) AS guias,
               COALESCE(SUM(ol.qtyordered), 0) AS kg,
               COALESCE(SUM(ol.linenetamt), 0) AS monto
        FROM adempiere.c_order o
        JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id
        JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id
        WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') AND o.isactive = 'Y'
          AND EXTRACT(YEAR FROM o.dateordered) = 2026
          AND LOWER(p.name) LIKE '%arroz paddy%'
        GROUP BY p.name ORDER BY monto DESC
    """)
    rows = db.execute(q2).fetchall()
    _print_table(rows, ["producto", "guias", "kg", "monto"])


def check_maiz(db):
    _print_header("COMPRAS DE MAÍZ - INPROMAIZ 2026")

    print("\n  Compras de maíz en InproMaiz (2026)")
    q = text("""
        SELECT p.name AS producto,
               COUNT(DISTINCT o.c_order_id) AS guias,
               COALESCE(SUM(ol.qtyordered), 0) AS kg,
               COALESCE(SUM(ol.linenetamt), 0) AS monto
        FROM adempiere.c_order o
        JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id
        JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id
        JOIN adempiere.ad_org org ON o.ad_org_id = org.ad_org_id
        WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') AND o.isactive = 'Y'
          AND EXTRACT(YEAR FROM o.dateordered) = 2026
          AND LOWER(org.name) LIKE '%inpromaiz%'
          AND (LOWER(p.name) LIKE '%maiz%' OR LOWER(p.name) LIKE '%maíz%')
        GROUP BY p.name ORDER BY monto DESC
    """)
    rows = db.execute(q).fetchall()
    _print_table(rows, ["producto", "guias", "kg", "monto"])
    if rows:
        total_kg = sum(float(r[2]) for r in rows)
        total_monto = sum(float(r[3]) for r in rows)
        print(f"  TOTAL kg  {total_kg:,.2f}")
        print(f"  TOTAL monto  {total_monto:,.2f}")


def check_cxp(db):
    _print_header("CUENTAS POR PAGAR")

    print("\n  Facturas de compra pendientes (ispaid='N')")
    q = text("""
        SELECT cur.iso_code AS moneda,
               COUNT(*) AS facturas,
               SUM(i.grandtotal) AS total
        FROM adempiere.c_invoice i
        JOIN adempiere.c_currency cur ON i.c_currency_id = cur.c_currency_id
        WHERE i.issotrx = 'N' AND i.docstatus IN ('CO','CL')
          AND i.ispaid = 'N' AND i.isactive = 'Y'
        GROUP BY cur.iso_code ORDER BY total DESC
    """)
    rows = db.execute(q).fetchall()
    _print_table(rows, ["moneda", "facturas", "total"])
    total_facturas = sum(r[1] for r in rows)
    print(f"  TOTAL facturas  {total_facturas}")


def check_cxc(db):
    _print_header("CUENTAS POR COBRAR VENCIDAS")

    print("\n  Facturas de venta pendientes vencidas")
    q = text("""
        SELECT cur.iso_code AS moneda,
               COUNT(*) AS facturas,
               SUM(i.grandtotal) AS total
        FROM adempiere.c_invoice i
        JOIN adempiere.c_currency cur ON i.c_currency_id = cur.c_currency_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO','CL')
          AND i.ispaid = 'N' AND i.isactive = 'Y'
          AND i.dateinvoiced + (
              CASE WHEN i.c_paymentterm_id IS NOT NULL
                   THEN (SELECT COALESCE(pt.netdays, 30)
                         FROM adempiere.c_paymentterm pt
                         WHERE pt.c_paymentterm_id = i.c_paymentterm_id)
                   ELSE 30 END
          ) < CURRENT_DATE
        GROUP BY cur.iso_code ORDER BY total DESC
    """)
    try:
        rows = db.execute(q).fetchall()
        _print_table(rows, ["moneda", "facturas", "total"])
    except Exception as e:
        print(f"  ERROR: {e}")
        db.rollback()

    print("\n  Facturas de venta pendientes (NO vencidas)")
    q2 = text("""
        SELECT cur.iso_code AS moneda,
               COUNT(*) AS facturas,
               SUM(i.grandtotal) AS total
        FROM adempiere.c_invoice i
        JOIN adempiere.c_currency cur ON i.c_currency_id = cur.c_currency_id
        WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO','CL')
          AND i.ispaid = 'N' AND i.isactive = 'Y'
          AND i.dateinvoiced + (
              CASE WHEN i.c_paymentterm_id IS NOT NULL
                   THEN (SELECT COALESCE(pt.netdays, 30)
                         FROM adempiere.c_paymentterm pt
                         WHERE pt.c_paymentterm_id = i.c_paymentterm_id)
                   ELSE 30 END
          ) >= CURRENT_DATE
        GROUP BY cur.iso_code ORDER BY total DESC
    """)
    try:
        rows = db.execute(q2).fetchall()
        _print_table(rows, ["moneda", "facturas", "total"])
    except Exception as e:
        print(f"  ERROR: {e}")
        db.rollback()


def check_produccion(db):
    _print_header("PRODUCCIÓN / MOVIMIENTOS DE INVENTARIO")

    today = "2026-03-13"

    print(f"\n  Marzo 2026 - Totales por tipo de movimiento")
    q = text("""
        SELECT
            SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones,
            SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos,
            SUM(CASE WHEN io.movementtype IN ('M+','M-') THEN 1 ELSE 0 END) AS internos,
            COUNT(*) AS total
        FROM adempiere.m_inout io
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO','CL')
          AND EXTRACT(MONTH FROM io.movementdate) = 3
          AND EXTRACT(YEAR FROM io.movementdate) = 2026
    """)
    row = db.execute(q).fetchone()
    if row:
        print(f"  Recepciones MP (V+)       {row[0]}")
        print(f"  Despachos PT (C-)         {row[1]}")
        print(f"  Movimientos internos      {row[2]}")
        print(f"  TOTAL movimientos         {row[3]}")

    print(f"\n  HOY ({today}) por tipo de movimiento")
    q2 = text("""
        SELECT
            SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones,
            SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos,
            COUNT(*) AS total
        FROM adempiere.m_inout io
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO','CL')
          AND io.movementdate::date = :today
    """)
    row2 = db.execute(q2, {"today": today}).fetchone()
    if row2:
        print(f"  Recepciones hoy  {row2[0]}")
        print(f"  Despachos hoy    {row2[1]}")
        print(f"  Total hoy        {row2[2]}")

    print(f"\n  AYER por tipo de movimiento")
    q3 = text("""
        SELECT
            SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones,
            SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos,
            COUNT(*) AS total
        FROM adempiere.m_inout io
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO','CL')
          AND io.movementdate::date = (:today::date - INTERVAL '1 day')::date
    """)
    row3 = db.execute(q3, {"today": today}).fetchone()
    if row3:
        print(f"  Recepciones ayer  {row3[0]}")
        print(f"  Despachos ayer    {row3[1]}")
        print(f"  Total ayer        {row3[2]}")

    print(f"\n  Fechas con movimientos en marzo 2026")
    q4 = text("""
        SELECT io.movementdate::date AS fecha,
               SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones,
               SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos,
               COUNT(*) AS total
        FROM adempiere.m_inout io
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO','CL')
          AND EXTRACT(MONTH FROM io.movementdate) = 3
          AND EXTRACT(YEAR FROM io.movementdate) = 2026
        GROUP BY io.movementdate::date ORDER BY fecha
    """)
    rows = db.execute(q4).fetchall()
    _print_table(rows, ["fecha", "recepciones", "despachos", "total"])
    if rows:
        total_docs = sum(r[3] for r in rows)
        print(f"  TOTAL docs marzo  {total_docs}")
        print(f"  Días con movimientos  {len(rows)}")

    print(f"\n  Top 10 productos movidos en marzo 2026")
    q5 = text("""
        SELECT p.name AS producto,
               SUM(CASE WHEN io.movementtype = 'V+' THEN iol.movementqty ELSE 0 END) AS recibido_kg,
               SUM(CASE WHEN io.movementtype = 'C-' THEN iol.movementqty ELSE 0 END) AS despachado_kg
        FROM adempiere.m_inout io
        JOIN adempiere.m_inoutline iol ON io.m_inout_id = iol.m_inout_id
        JOIN adempiere.m_product p ON iol.m_product_id = p.m_product_id
        WHERE io.isactive = 'Y' AND io.docstatus IN ('CO','CL')
          AND EXTRACT(MONTH FROM io.movementdate) = 3
          AND EXTRACT(YEAR FROM io.movementdate) = 2026
        GROUP BY p.name ORDER BY SUM(ABS(iol.movementqty)) DESC LIMIT 10
    """)
    rows = db.execute(q5).fetchall()
    _print_table(rows, ["producto", "recibido_kg", "despachado_kg"])

    print(f"\n  PP_ORDER (Órdenes de producción) - ¿existe la tabla?")
    try:
        q6 = text("""
            SELECT COUNT(*) FROM adempiere.pp_order WHERE docstatus IN ('CO','CL')
        """)
        row = db.execute(q6).fetchone()
        print(f"  Total órdenes de producción completadas  {row[0]}")
    except Exception as e:
        print(f"  pp_order: {e}")
        db.rollback()

    print(f"\n  M_PRODUCTION (Producción alternativa) - ¿existe?")
    try:
        q7 = text("""
            SELECT COUNT(*), MIN(movementdate), MAX(movementdate)
            FROM adempiere.m_production
        """)
        row = db.execute(q7).fetchone()
        print(f"  Total registros m_production  {row[0]}")
        print(f"  Primer registro  {row[1]}")
        print(f"  Último registro  {row[2]}")
    except Exception as e:
        print(f"  m_production: {e}")
        db.rollback()


def check_vacaciones(db):
    _print_header("VACACIONES ENERO 2026")

    print("\n  Conceptos de nómina con 'vacacion' en nombre")
    q = text("""
        SELECT hc.hr_concept_id, hc.value, hc.name
        FROM adempiere.hr_concept hc
        WHERE LOWER(hc.name) LIKE '%vacacion%'
           OR LOWER(hc.name) LIKE '%bono vacacional%'
           OR LOWER(hc.name) LIKE '%dias disfrut%'
        ORDER BY hc.name
    """)
    try:
        rows = db.execute(q).fetchall()
        _print_table(rows[:30], ["id", "codigo", "nombre"])
        if len(rows) > 30:
            print(f"  ... y {len(rows) - 30} filas más")
    except Exception as e:
        print(f"  ERROR en vacaciones: {e}")
        db.rollback()
        return

    print("\n  Movimientos de vacaciones enero 2026")
    q2 = text("""
        SELECT COUNT(DISTINCT hm.c_bpartner_id) AS empleados,
               SUM(ABS(hm.amount)) AS monto_total,
               COUNT(*) AS total_ocurrencias
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id
        JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id
        WHERE hp.docstatus IN ('CO','CL') AND hp.isactive = 'Y'
          AND EXTRACT(MONTH FROM hp.dateacct) = 1
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
          AND (LOWER(hc.name) LIKE '%vacacion%' OR LOWER(hc.name) LIKE '%bono vacacional%')
    """)
    try:
        row = db.execute(q2).fetchone()
        print(f"  Empleados con vacaciones  {row[0]}")
        print(f"  Monto total (Bs.)  {row[1]}")
        print(f"  Total ocurrencias  {row[2]}")
    except Exception as e:
        print(f"  ERROR: {e}")
        db.rollback()


def check_cumpleaneros(db):
    _print_header("CUMPLEAÑEROS DE MARZO")

    q = text("""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT ON (bp.c_bpartner_id) bp.name, EXTRACT(DAY FROM u.birthday)
            FROM adempiere.hr_employee e
            JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
            JOIN adempiere.ad_user u ON bp.c_bpartner_id = u.c_bpartner_id
            WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
              AND u.birthday IS NOT NULL
              AND EXTRACT(MONTH FROM u.birthday) = 3
        ) sub
    """)
    try:
        row = db.execute(q).fetchone()
        print(f"  Cumpleañeros de marzo (DISTINCT)  {row[0]}")
    except Exception as e:
        print(f"  ERROR en cumpleaneros: {e}")
        db.rollback()
        return

    print("\n  Primeros 10 cumpleañeros de marzo (DISTINCT)")
    q2 = text("""
        SELECT DISTINCT ON (bp.c_bpartner_id) bp.name,
               EXTRACT(DAY FROM u.birthday)::int AS dia,
               EXTRACT(MONTH FROM u.birthday)::int AS mes
        FROM adempiere.hr_employee e
        JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id
        JOIN adempiere.ad_user u ON bp.c_bpartner_id = u.c_bpartner_id
        WHERE e.isactive = 'Y' AND bp.isactive = 'Y'
          AND u.birthday IS NOT NULL AND EXTRACT(MONTH FROM u.birthday) = 3
        ORDER BY bp.c_bpartner_id, u.ad_user_id
        LIMIT 10
    """)
    try:
        rows = db.execute(q2).fetchall()
        _print_table(rows, ["nombre", "dia", "mes"])
    except Exception as e:
        print(f"  ERROR: {e}")
        db.rollback()


def check_nomina(db):
    _print_header("NÓMINA FEBRERO 2026")

    q = text("""
        SELECT COUNT(DISTINCT hp.hr_process_id) AS procesos,
               COUNT(DISTINCT hm.c_bpartner_id) AS empleados,
               COALESCE(SUM(CASE WHEN hm.amount > 0 THEN hm.amount ELSE 0 END), 0) AS devengado,
               COALESCE(SUM(CASE WHEN hm.amount < 0 THEN ABS(hm.amount) ELSE 0 END), 0) AS deducciones
        FROM adempiere.hr_movement hm
        JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id
        WHERE hp.docstatus IN ('CO','CL') AND hp.isactive = 'Y'
          AND EXTRACT(MONTH FROM hp.dateacct) = 2
          AND EXTRACT(YEAR FROM hp.dateacct) = 2026
    """)
    try:
        row = db.execute(q).fetchone()
        print(f"  Procesos de nómina  {row[0]}")
        print(f"  Empleados procesados  {row[1]}")
        print(f"  Total devengado (Bs.)  {row[2]}")
        print(f"  Total deducciones (Bs.)  {row[3]}")
        devengado = float(row[2]) if row[2] else 0
        deducciones = float(row[3]) if row[3] else 0
        print(f"  Neto a pagar (Bs.)  {devengado - deducciones:,.2f}")
    except Exception as e:
        print(f"  ERROR en nomina: {e}")
        db.rollback()


CHECKS = {
    "empleados": check_empleados,
    "arroz": check_arroz,
    "maiz": check_maiz,
    "cxp": check_cxp,
    "cxc": check_cxc,
    "produccion": check_produccion,
    "vacaciones": check_vacaciones,
    "cumpleaneros": check_cumpleaneros,
    "nomina": check_nomina,
}


def main():
    parser = argparse.ArgumentParser(description="Verificar datos directamente en iDempiere")
    parser.add_argument("--check", default="all", help="Verificación específica o 'all'")
    args = parser.parse_args()

    print("#" * 70)
    print("  VERIFICACIÓN DIRECTA DE DATOS - iDempiere")
    from datetime import datetime
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("#" * 70)

    db = get_idempiere_session()
    try:
        if args.check == "all":
            for name, fn in CHECKS.items():
                try:
                    fn(db)
                except Exception as e:
                    print(f"\n  ERROR en {name}: {e}")
                    db.rollback()
        elif args.check in CHECKS:
            CHECKS[args.check](db)
        else:
            print(f"Check desconocido: {args.check}")
            print(f"Disponibles: {', '.join(CHECKS.keys())}, all")
            sys.exit(1)
    finally:
        db.close()

    print("\n" + "#" * 70)
    print("  VERIFICACIÓN COMPLETA")
    print("#" * 70)


if __name__ == "__main__":
    main()

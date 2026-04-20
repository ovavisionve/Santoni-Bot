"""Diagnóstico: por qué build_producer_purchases devuelve 27 guías vs 356 en verificación.

Ejecuta queries incrementales contra iDempiere en vivo para identificar
exactamente qué filtro excluye más registros.

Uso: docker compose exec backend python scripts/diagnose_producer_gap.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.services.idempiere_queries import IdempiereSession

def main():
    db = IdempiereSession()
    try:
        base = (
            "FROM adempiere.c_order o "
            "JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id "
            "JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id "
            "JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
        )

        queries = [
            (
                "1. TODAS las compras arroz paddy 2026 (sin filtros extra)",
                f"SELECT COUNT(DISTINCT o.c_order_id) AS guias, "
                f"COALESCE(SUM(ol.qtyordered),0) AS kg, "
                f"COALESCE(SUM(ol.linenetamt),0) AS monto "
                f"{base}"
                f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
                f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
                f"AND (p.name ILIKE '%arroz%' AND p.name ILIKE '%paddy%')"
            ),
            (
                "2. + isactive = 'Y'",
                f"SELECT COUNT(DISTINCT o.c_order_id) AS guias, "
                f"COALESCE(SUM(ol.qtyordered),0) AS kg, "
                f"COALESCE(SUM(ol.linenetamt),0) AS monto "
                f"{base}"
                f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
                f"AND o.isactive = 'Y' "
                f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
                f"AND (p.name ILIKE '%arroz%' AND p.name ILIKE '%paddy%')"
            ),
            (
                "3. + priceactual < 10000",
                f"SELECT COUNT(DISTINCT o.c_order_id) AS guias, "
                f"COALESCE(SUM(ol.qtyordered),0) AS kg, "
                f"COALESCE(SUM(ol.linenetamt),0) AS monto "
                f"{base}"
                f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
                f"AND o.isactive = 'Y' "
                f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
                f"AND (p.name ILIKE '%arroz%' AND p.name ILIKE '%paddy%') "
                f"AND ol.priceactual < 10000"
            ),
            (
                "4. + exclusión empresas internas (el filtro completo)",
                f"SELECT COUNT(DISTINCT o.c_order_id) AS guias, "
                f"COALESCE(SUM(ol.qtyordered),0) AS kg, "
                f"COALESCE(SUM(ol.linenetamt),0) AS monto "
                f"{base}"
                f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
                f"AND o.isactive = 'Y' "
                f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
                f"AND (p.name ILIKE '%arroz%' AND p.name ILIKE '%paddy%') "
                f"AND ol.priceactual < 10000 "
                f"AND LOWER(bp.name) NOT LIKE '%inproa santoni%' "
                f"AND LOWER(bp.name) NOT LIKE '%inpromaiz%' "
                f"AND LOWER(bp.name) NOT LIKE '%santoni service%' "
                f"AND LOWER(bp.name) NOT LIKE '%agropecuaria r.r%' "
                f"AND LOWER(bp.name) NOT LIKE '%aga agricola%' "
                f"AND LOWER(bp.name) NOT LIKE '%agroinproa%' "
                f"AND LOWER(bp.name) NOT LIKE '%inversiones aga%' "
                f"AND LOWER(bp.name) NOT LIKE '%agro import%'"
            ),
        ]

        print("=" * 80)
        print("DIAGNÓSTICO: Compras Arroz Paddy 2026 - Filtros incrementales")
        print("Verificación iDempiere: 356 guías, 7,657,696.79 kg, 1,397,225,883.67 Bs")
        print("=" * 80)

        for label, sql in queries:
            row = db.execute(text(sql)).fetchone()
            guias = row[0] if row else 0
            kg = float(row[1]) if row else 0
            monto = float(row[2]) if row else 0
            precio = monto / kg if kg > 0 else 0
            print(f"\n{label}")
            print(f"  Guías: {guias:,}")
            print(f"  Kg: {kg:,.2f}")
            print(f"  Monto: Bs. {monto:,.2f}")
            print(f"  Precio promedio: {precio:,.2f} Bs/kg")

        # 5. Desglose: qué empresas internas están como proveedores de arroz paddy
        print("\n" + "=" * 80)
        print("DESGLOSE: Empresas del grupo Santoni como 'proveedores' de arroz paddy 2026")
        print("=" * 80)
        desglose_sql = text(
            f"SELECT bp.name, "
            f"COUNT(DISTINCT o.c_order_id) AS guias, "
            f"COALESCE(SUM(ol.qtyordered),0) AS kg, "
            f"COALESCE(SUM(ol.linenetamt),0) AS monto "
            f"{base}"
            f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
            f"AND o.isactive = 'Y' "
            f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
            f"AND (p.name ILIKE '%arroz%' AND p.name ILIKE '%paddy%') "
            f"AND ("
            f"  LOWER(bp.name) LIKE '%inproa santoni%' "
            f"  OR LOWER(bp.name) LIKE '%inpromaiz%' "
            f"  OR LOWER(bp.name) LIKE '%santoni service%' "
            f"  OR LOWER(bp.name) LIKE '%agropecuaria r.r%' "
            f"  OR LOWER(bp.name) LIKE '%aga agricola%' "
            f"  OR LOWER(bp.name) LIKE '%agroinproa%' "
            f"  OR LOWER(bp.name) LIKE '%inversiones aga%' "
            f"  OR LOWER(bp.name) LIKE '%agro import%'"
            f") "
            f"GROUP BY bp.name ORDER BY kg DESC"
        )
        rows = db.execute(desglose_sql).fetchall()
        if rows:
            for r in rows:
                print(f"  {r[0]}: {r[1]} guías, {float(r[2]):,.2f} kg, Bs. {float(r[3]):,.2f}")
        else:
            print("  (Ninguna empresa interna aparece como proveedor de arroz paddy)")

        # 6. Registros excluidos por priceactual >= 10000
        print("\n" + "=" * 80)
        print("REGISTROS CON priceactual >= 10000 (excluidos por filtro de outliers)")
        print("=" * 80)
        outlier_sql = text(
            f"SELECT bp.name, ol.priceactual, ol.qtyordered, ol.linenetamt, o.documentno "
            f"{base}"
            f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
            f"AND o.isactive = 'Y' "
            f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
            f"AND (p.name ILIKE '%arroz%' AND p.name ILIKE '%paddy%') "
            f"AND ol.priceactual >= 10000 "
            f"ORDER BY ol.priceactual DESC LIMIT 20"
        )
        rows = db.execute(outlier_sql).fetchall()
        if rows:
            for r in rows:
                print(f"  {r[0]}: precio={float(r[1]):,.2f}, qty={float(r[2]):,.2f}, "
                      f"monto={float(r[3]):,.2f}, doc={r[4]}")
        else:
            print("  (Ningún registro con priceactual >= 10000)")

        # 7. Verificación: query EXACTA de la verificación (sin filtros extra)
        print("\n" + "=" * 80)
        print("VERIFICACIÓN EXACTA: p.name = 'ARROZ PADDY ACONDICIONADO' (match exacto)")
        print("=" * 80)
        exact_sql = text(
            f"SELECT COUNT(DISTINCT o.c_order_id) AS guias, "
            f"COALESCE(SUM(ol.qtyordered),0) AS kg, "
            f"COALESCE(SUM(ol.linenetamt),0) AS monto "
            f"{base}"
            f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
            f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
            f"AND p.name = 'ARROZ PADDY ACONDICIONADO'"
        )
        row = db.execute(exact_sql).fetchone()
        if row:
            guias = row[0]
            kg = float(row[1])
            monto = float(row[2])
            precio = monto / kg if kg > 0 else 0
            print(f"  Guías: {guias:,}")
            print(f"  Kg: {kg:,.2f}")
            print(f"  Monto: Bs. {monto:,.2f}")
            print(f"  Precio promedio: {precio:,.2f} Bs/kg")

        # 8. Top 10 proveedores de arroz paddy 2026 (sin exclusiones)
        print("\n" + "=" * 80)
        print("TOP 10 PROVEEDORES de arroz paddy 2026 (SIN exclusiones)")
        print("=" * 80)
        top_sql = text(
            f"SELECT bp.name, "
            f"COUNT(DISTINCT o.c_order_id) AS guias, "
            f"COALESCE(SUM(ol.qtyordered),0) AS kg, "
            f"COALESCE(SUM(ol.linenetamt),0) AS monto "
            f"{base}"
            f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
            f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
            f"AND p.name = 'ARROZ PADDY ACONDICIONADO' "
            f"GROUP BY bp.name ORDER BY kg DESC LIMIT 10"
        )
        rows = db.execute(top_sql).fetchall()
        for r in rows:
            print(f"  {r[0]}: {r[1]} guías, {float(r[2]):,.2f} kg, Bs. {float(r[3]):,.2f}")

    finally:
        db.close()


if __name__ == "__main__":
    main()

"""Diagnóstico: por qué MAIZ BLANCO DE CONSUMO no aparece en compras productores.

Verificación dice: 274 guías, 7,003,571.05 kg, 824,284,245.86 Bs
Bot dice: 0 guías de MAIZ BLANCO

Uso: docker compose exec backend python scripts/diagnose_maiz_gap.py
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

        print("=" * 80)
        print("DIAGNÓSTICO: Compras Maíz 2026 - Filtros incrementales")
        print("Verificación: MAIZ BLANCO DE CONSUMO = 274 guías, 7,003,571.05 kg")
        print("=" * 80)

        queries = [
            (
                "1. TODAS las compras de maíz 2026 (sin filtros extra)",
                f"SELECT COUNT(DISTINCT o.c_order_id), "
                f"COALESCE(SUM(ol.qtyordered),0), "
                f"COALESCE(SUM(ol.linenetamt),0) "
                f"{base}"
                f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
                f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
                f"AND p.name ILIKE '%maiz%'"
            ),
            (
                "2. + isactive='Y' + qtyordered > 1",
                f"SELECT COUNT(DISTINCT o.c_order_id), "
                f"COALESCE(SUM(ol.qtyordered),0), "
                f"COALESCE(SUM(ol.linenetamt),0) "
                f"{base}"
                f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
                f"AND o.isactive = 'Y' AND ol.qtyordered > 1 "
                f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
                f"AND p.name ILIKE '%maiz%'"
            ),
            (
                "3. + exclusión empresas internas",
                f"SELECT COUNT(DISTINCT o.c_order_id), "
                f"COALESCE(SUM(ol.qtyordered),0), "
                f"COALESCE(SUM(ol.linenetamt),0) "
                f"{base}"
                f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
                f"AND o.isactive = 'Y' AND ol.qtyordered > 1 "
                f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
                f"AND p.name ILIKE '%maiz%' "
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
            print(f"  Precio prom: {precio:,.2f} Bs/kg")

        # Desglose: quién es el proveedor de MAIZ BLANCO DE CONSUMO
        print("\n" + "=" * 80)
        print("TOP PROVEEDORES de MAIZ BLANCO DE CONSUMO 2026")
        print("=" * 80)
        top_sql = text(
            f"SELECT bp.name, "
            f"COUNT(DISTINCT o.c_order_id) AS guias, "
            f"COALESCE(SUM(ol.qtyordered),0) AS kg, "
            f"COALESCE(SUM(ol.linenetamt),0) AS monto "
            f"{base}"
            f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
            f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
            f"AND p.name = 'MAIZ BLANCO DE CONSUMO' "
            f"GROUP BY bp.name ORDER BY kg DESC LIMIT 15"
        )
        rows = db.execute(top_sql).fetchall()
        for r in rows:
            excluded = ""
            name_lower = r[0].lower()
            for org in ["inproa santoni", "inpromaiz", "santoni service",
                        "agropecuaria r.r", "aga agricola", "agroinproa",
                        "inversiones aga", "agro import"]:
                if org in name_lower:
                    excluded = " *** EXCLUIDO por filtro interno ***"
                    break
            print(f"  {r[0]}: {r[1]} guías, {float(r[2]):,.2f} kg, Bs. {float(r[3]):,.2f}{excluded}")

        # Solo MAIZ BLANCO con filtro interno
        print("\n" + "=" * 80)
        print("MAIZ BLANCO DE CONSUMO 2026 - SOLO PRODUCTORES EXTERNOS")
        print("=" * 80)
        ext_sql = text(
            f"SELECT COUNT(DISTINCT o.c_order_id), "
            f"COALESCE(SUM(ol.qtyordered),0), "
            f"COALESCE(SUM(ol.linenetamt),0) "
            f"{base}"
            f"WHERE o.issotrx = 'N' AND o.docstatus IN ('CO','CL') "
            f"AND EXTRACT(YEAR FROM o.dateordered) = 2026 "
            f"AND p.name = 'MAIZ BLANCO DE CONSUMO' "
            f"AND LOWER(bp.name) NOT LIKE '%inproa santoni%' "
            f"AND LOWER(bp.name) NOT LIKE '%inpromaiz%' "
            f"AND LOWER(bp.name) NOT LIKE '%santoni service%' "
            f"AND LOWER(bp.name) NOT LIKE '%agropecuaria r.r%' "
            f"AND LOWER(bp.name) NOT LIKE '%aga agricola%' "
            f"AND LOWER(bp.name) NOT LIKE '%agroinproa%' "
            f"AND LOWER(bp.name) NOT LIKE '%inversiones aga%' "
            f"AND LOWER(bp.name) NOT LIKE '%agro import%'"
        )
        row = db.execute(ext_sql).fetchone()
        if row:
            print(f"  Guías: {row[0]:,}")
            print(f"  Kg: {float(row[1]):,.2f}")
            print(f"  Monto: Bs. {float(row[2]):,.2f}")
        else:
            print("  (Sin resultados)")

    finally:
        db.close()


if __name__ == "__main__":
    main()

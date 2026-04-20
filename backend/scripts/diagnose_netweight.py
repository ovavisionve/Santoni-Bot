"""Verificar campos de peso en c_order para compras agrícolas.

Uso: docker compose exec backend python scripts/diagnose_netweight.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.services.idempiere_queries import IdempiereSession

def main():
    db = IdempiereSession()
    try:
        # 1. Verificar que netweight existe y tiene datos
        print("=" * 80)
        print("CAMPOS DE PESO EN c_order - Compras MAIZ BLANCO 2026")
        print("=" * 80)

        sql = text("""
            SELECT bp.name,
                   o.documentno,
                   o.netweight,
                   o.grossweight,
                   o.tareweight,
                   ol.qtyordered,
                   ol.linenetamt,
                   ol.priceactual
            FROM adempiere.c_order o
            JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id
            JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id
            JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id
            WHERE o.issotrx = 'N'
              AND o.docstatus IN ('CO','CL')
              AND EXTRACT(YEAR FROM o.dateordered) = 2026
              AND p.name = 'MAIZ BLANCO DE CONSUMO'
              AND LOWER(bp.name) NOT LIKE '%inproa santoni%'
              AND LOWER(bp.name) NOT LIKE '%inpromaiz%'
              AND LOWER(bp.name) NOT LIKE '%santoni service%'
              AND LOWER(bp.name) NOT LIKE '%agropecuaria r.r%'
              AND LOWER(bp.name) NOT LIKE '%aga agricola%'
              AND LOWER(bp.name) NOT LIKE '%agroinproa%'
              AND LOWER(bp.name) NOT LIKE '%inversiones aga%'
              AND LOWER(bp.name) NOT LIKE '%agro import%'
            ORDER BY o.dateordered
            LIMIT 20
        """)
        rows = db.execute(sql).fetchall()
        print(f"\n{'Proveedor':<45} {'Doc':<12} {'netweight':>12} {'grossweight':>12} {'tareweight':>12} {'qtyordered':>12} {'linenetamt':>14} {'priceactual':>12}")
        print("-" * 145)
        for r in rows:
            print(f"{str(r[0]):<45} {str(r[1]):<12} {r[2] or 0:>12,.2f} {r[3] or 0:>12,.2f} {r[4] or 0:>12,.2f} {r[5] or 0:>12,.2f} {r[6] or 0:>14,.2f} {r[7] or 0:>12,.2f}")

        # 2. Ahora ARROZ - misma verificación
        print("\n" + "=" * 80)
        print("CAMPOS DE PESO EN c_order - Compras ARROZ 2026 (primeras 10 externas)")
        print("=" * 80)

        sql2 = text("""
            SELECT bp.name,
                   o.documentno,
                   o.netweight,
                   o.grossweight,
                   o.tareweight,
                   ol.qtyordered,
                   ol.linenetamt,
                   ol.priceactual
            FROM adempiere.c_order o
            JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id
            JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id
            JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id
            WHERE o.issotrx = 'N'
              AND o.docstatus IN ('CO','CL')
              AND EXTRACT(YEAR FROM o.dateordered) = 2026
              AND p.name ILIKE '%arroz%'
              AND LOWER(bp.name) NOT LIKE '%inproa santoni%'
              AND LOWER(bp.name) NOT LIKE '%inpromaiz%'
              AND LOWER(bp.name) NOT LIKE '%santoni service%'
              AND LOWER(bp.name) NOT LIKE '%agropecuaria r.r%'
              AND LOWER(bp.name) NOT LIKE '%aga agricola%'
              AND LOWER(bp.name) NOT LIKE '%agroinproa%'
              AND LOWER(bp.name) NOT LIKE '%inversiones aga%'
              AND LOWER(bp.name) NOT LIKE '%agro import%'
            ORDER BY o.dateordered
            LIMIT 10
        """)
        rows2 = db.execute(sql2).fetchall()
        print(f"\n{'Proveedor':<45} {'Doc':<12} {'netweight':>12} {'grossweight':>12} {'tareweight':>12} {'qtyordered':>12} {'linenetamt':>14} {'priceactual':>12}")
        print("-" * 145)
        for r in rows2:
            print(f"{str(r[0]):<45} {str(r[1]):<12} {r[2] or 0:>12,.2f} {r[3] or 0:>12,.2f} {r[4] or 0:>12,.2f} {r[5] or 0:>12,.2f} {r[6] or 0:>14,.2f} {r[7] or 0:>12,.2f}")

        # 3. Totales usando netweight vs qtyordered para MAIZ externo
        print("\n" + "=" * 80)
        print("COMPARACIÓN: SUM(netweight) vs SUM(qtyordered) - MAIZ externo 2026")
        print("=" * 80)

        sql3 = text("""
            SELECT COUNT(DISTINCT o.c_order_id) AS guias,
                   COALESCE(SUM(o.netweight), 0) AS sum_netweight,
                   COALESCE(SUM(ol.qtyordered), 0) AS sum_qtyordered,
                   COALESCE(SUM(ol.linenetamt), 0) AS sum_linenetamt
            FROM adempiere.c_order o
            JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id
            JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id
            JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id
            WHERE o.issotrx = 'N'
              AND o.docstatus IN ('CO','CL')
              AND o.isactive = 'Y'
              AND EXTRACT(YEAR FROM o.dateordered) = 2026
              AND p.name ILIKE '%maiz%'
              AND LOWER(bp.name) NOT LIKE '%inproa santoni%'
              AND LOWER(bp.name) NOT LIKE '%inpromaiz%'
              AND LOWER(bp.name) NOT LIKE '%santoni service%'
              AND LOWER(bp.name) NOT LIKE '%agropecuaria r.r%'
              AND LOWER(bp.name) NOT LIKE '%aga agricola%'
              AND LOWER(bp.name) NOT LIKE '%agroinproa%'
              AND LOWER(bp.name) NOT LIKE '%inversiones aga%'
              AND LOWER(bp.name) NOT LIKE '%agro import%'
        """)
        row = db.execute(sql3).fetchone()
        if row:
            print(f"  Guías: {row[0]}")
            print(f"  SUM(netweight):  {float(row[1]):>15,.2f} kg")
            print(f"  SUM(qtyordered): {float(row[2]):>15,.2f} kg")
            print(f"  SUM(linenetamt): Bs. {float(row[3]):>15,.2f}")

        # 4. Totales usando netweight vs qtyordered para ARROZ externo
        print("\n" + "=" * 80)
        print("COMPARACIÓN: SUM(netweight) vs SUM(qtyordered) - ARROZ externo 2026")
        print("=" * 80)

        sql4 = text("""
            SELECT COUNT(DISTINCT o.c_order_id) AS guias,
                   COALESCE(SUM(o.netweight), 0) AS sum_netweight,
                   COALESCE(SUM(ol.qtyordered), 0) AS sum_qtyordered,
                   COALESCE(SUM(ol.linenetamt), 0) AS sum_linenetamt
            FROM adempiere.c_order o
            JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id
            JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id
            JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id
            WHERE o.issotrx = 'N'
              AND o.docstatus IN ('CO','CL')
              AND o.isactive = 'Y'
              AND EXTRACT(YEAR FROM o.dateordered) = 2026
              AND p.name ILIKE '%arroz%'
              AND LOWER(bp.name) NOT LIKE '%inproa santoni%'
              AND LOWER(bp.name) NOT LIKE '%inpromaiz%'
              AND LOWER(bp.name) NOT LIKE '%santoni service%'
              AND LOWER(bp.name) NOT LIKE '%agropecuaria r.r%'
              AND LOWER(bp.name) NOT LIKE '%aga agricola%'
              AND LOWER(bp.name) NOT LIKE '%agroinproa%'
              AND LOWER(bp.name) NOT LIKE '%inversiones aga%'
              AND LOWER(bp.name) NOT LIKE '%agro import%'
        """)
        row = db.execute(sql4).fetchone()
        if row:
            print(f"  Guías: {row[0]}")
            print(f"  SUM(netweight):  {float(row[1]):>15,.2f} kg")
            print(f"  SUM(qtyordered): {float(row[2]):>15,.2f} kg")
            print(f"  SUM(linenetamt): Bs. {float(row[3]):>15,.2f}")

        # 5. Verificar si TODAS las compras a productores usan qtyordered=1
        print("\n" + "=" * 80)
        print("DISTRIBUCIÓN de qtyordered en compras externas 2026")
        print("=" * 80)
        sql5 = text("""
            SELECT
              CASE
                WHEN ol.qtyordered = 1 THEN 'qty=1'
                WHEN ol.qtyordered > 1 AND ol.qtyordered <= 100 THEN 'qty 2-100'
                WHEN ol.qtyordered > 100 THEN 'qty > 100'
                ELSE 'qty <= 0'
              END AS rango,
              COUNT(*) AS lineas,
              COUNT(DISTINCT o.c_order_id) AS ordenes
            FROM adempiere.c_order o
            JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id
            JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id
            WHERE o.issotrx = 'N'
              AND o.docstatus IN ('CO','CL')
              AND o.isactive = 'Y'
              AND EXTRACT(YEAR FROM o.dateordered) = 2026
              AND LOWER(bp.name) NOT LIKE '%inproa santoni%'
              AND LOWER(bp.name) NOT LIKE '%inpromaiz%'
              AND LOWER(bp.name) NOT LIKE '%santoni service%'
              AND LOWER(bp.name) NOT LIKE '%agropecuaria r.r%'
              AND LOWER(bp.name) NOT LIKE '%aga agricola%'
              AND LOWER(bp.name) NOT LIKE '%agroinproa%'
              AND LOWER(bp.name) NOT LIKE '%inversiones aga%'
              AND LOWER(bp.name) NOT LIKE '%agro import%'
            GROUP BY 1 ORDER BY 1
        """)
        rows = db.execute(sql5).fetchall()
        for r in rows:
            print(f"  {r[0]}: {r[1]} líneas, {r[2]} órdenes")

    finally:
        db.close()

if __name__ == "__main__":
    main()

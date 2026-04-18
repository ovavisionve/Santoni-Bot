"""Inventory queries: stock levels by product and warehouse."""

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
    _add_product_search_filter,
    execute_idempiere_query,
    logger,
)

# ---------------------------------------------------------------------------
# INVENTARIO (Inventory / Stock)
# ---------------------------------------------------------------------------

def build_inventory_stock(
    org_ids: list[int] | None = None,
    product_search: str | None = None,
    category_search: str | None = None,
    warehouse_search: str | None = None,
    org_name: str | None = None,
) -> dict:
    """Inventory stock from iDempiere m_storageonhand.

    m_storageonhand has multiple rows per product (one per lot/batch via
    m_attributesetinstance_id), so we SUM(qtyonhand) grouped by product.

    JOIN chain:
        m_storageonhand → m_locator → m_warehouse → ad_org
        m_storageonhand → m_product → m_product_category
    """
    db = IdempiereSession()
    try:
        conditions = ["s.isactive = 'Y'", "s.qtyonhand <> 0"]
        params: dict = {}

        # Org filter on warehouse org
        if org_ids:
            placeholders = ", ".join(f":org_{i}" for i in range(len(org_ids)))
            conditions.append(f"w.ad_org_id IN ({placeholders})")
            for i, org_id in enumerate(org_ids):
                params[f"org_{i}"] = org_id

        if product_search:
            _add_product_search_filter(conditions, params, product_search)

        if category_search:
            conditions.append("pc.name ILIKE :cat_search")
            params["cat_search"] = f"%{category_search}%"

        if warehouse_search:
            conditions.append("w.name ILIKE :wh_search")
            params["wh_search"] = f"%{warehouse_search}%"

        if org_name:
            _add_org_name_filter(conditions, params, org_name, "w")

        where = " AND ".join(conditions)

        # ── Summary by organization ──
        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"COUNT(DISTINCT p.m_product_id) AS productos, "
            f"SUM(s.qtyonhand) AS cantidad_total "
            f"FROM adempiere.m_storageonhand s "
            f"JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id "
            f"JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id "
            f"JOIN adempiere.ad_org o ON w.ad_org_id = o.ad_org_id "
            f"JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id "
            f"LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY cantidad_total DESC"
        )
        by_org = [
            {
                "organizacion": r[0],
                "productos": r[1],
                "cantidad_total": float(r[2]) if r[2] else 0.0,
            }
            for r in db.execute(by_org_q, params).fetchall()
        ]

        total_products = sum(r["productos"] for r in by_org)
        total_qty = sum(r["cantidad_total"] for r in by_org)

        # ── Summary by category ──
        by_cat_q = text(
            f"SELECT COALESCE(pc.name, 'Sin Categoría') AS categoria, "
            f"COUNT(DISTINCT p.m_product_id) AS productos, "
            f"SUM(s.qtyonhand) AS cantidad_total "
            f"FROM adempiere.m_storageonhand s "
            f"JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id "
            f"JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id "
            f"JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id "
            f"LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id "
            f"WHERE {where} "
            f"GROUP BY pc.name ORDER BY cantidad_total DESC LIMIT 20"
        )
        by_cat = [
            {
                "categoria": r[0],
                "productos": r[1],
                "cantidad_total": float(r[2]) if r[2] else 0.0,
            }
            for r in db.execute(by_cat_q, params).fetchall()
        ]

        # ── Detail by product (top 50 by quantity) ──
        detail_q = text(
            f"SELECT p.value AS codigo, p.name AS producto, "
            f"COALESCE(pc.name, 'Sin Categoría') AS categoria, "
            f"COALESCE(w.name, 'Sin Almacén') AS almacen, "
            f"COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"SUM(s.qtyonhand) AS cantidad, "
            f"COALESCE(u.name, '-') AS unidad "
            f"FROM adempiere.m_storageonhand s "
            f"JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id "
            f"JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id "
            f"JOIN adempiere.ad_org o ON w.ad_org_id = o.ad_org_id "
            f"JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id "
            f"LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id "
            f"LEFT JOIN adempiere.c_uom u ON p.c_uom_id = u.c_uom_id "
            f"WHERE {where} "
            f"GROUP BY p.value, p.name, pc.name, w.name, o.name, u.name "
            f"ORDER BY cantidad DESC LIMIT 50"
        )
        detail = [
            {
                "codigo": r[0],
                "producto": r[1],
                "categoria": r[2],
                "almacen": r[3],
                "organizacion": r[4],
                "cantidad": float(r[5]) if r[5] else 0.0,
                "unidad": r[6],
            }
            for r in db.execute(detail_q, params).fetchall()
        ]

        return {
            "totales": {
                "productos_con_stock": total_products,
                "cantidad_total": total_qty,
            },
            "filtros": {
                "producto": product_search,
                "categoria": category_search,
                "almacen": warehouse_search,
            },
            "por_organizacion": by_org,
            "por_categoria": by_cat,
            "detalle_productos": detail,
        }
    finally:
        db.close()

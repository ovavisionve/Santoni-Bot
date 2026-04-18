"""Sales by product queries (c_invoiceline breakdown)."""

from sqlalchemy import text

from ..common import (
    _add_currency_filter,
    _add_date_filter,
    _add_org_filter,
    _add_org_name_filter,
    _add_product_search_filter,
    _get_session,
)
from ..ventas_helpers import _currency_label


def build_sales_by_product(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
    product_search: str | None = None,
    category_search: str | None = None,
    only_skus: bool = False,
    limit: int = 30,
) -> dict:
    """Sales breakdown by product from iDempiere c_invoiceline.

    JOIN chain:
        c_invoice → c_invoiceline → m_product → m_product_category
        c_invoice → c_doctype (to separate ARI/ARC)
        m_product → c_uom (unit of measure)

    Parameters:
        only_skus: if True, filters m_product_category.iskpi='Y'
        product_search: ILIKE filter on product name or code
        category_search: ILIKE filter on product category name
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
            "dt.docbasetype = 'ARI'",
        ]
        params: dict = {"limit": limit}
        _add_org_filter(conditions, params, org_ids, "i", exclude_demo=True)
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_currency_filter(conditions, params, currency_ids, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")

        if product_search:
            _add_product_search_filter(conditions, params, product_search)
        if category_search:
            conditions.append("pc.name ILIKE :cat_search")
            params["cat_search"] = f"%{category_search}%"
        if only_skus:
            conditions.append("pc.iskpi = 'Y'")

        where = " AND ".join(conditions)

        cur_label = _currency_label("i")

        top_products_q = text(
            f"SELECT p.value AS codigo, p.name AS producto, "
            f"COALESCE(pc.name, 'Sin Categoría') AS categoria, "
            f"COALESCE(uom.name, '') AS unidad_medida, "
            f"{cur_label} AS moneda, "
            f"SUM(il.qtyinvoiced) AS cantidad, "
            f"COALESCE(SUM(il.linenetamt), 0) AS total_neto "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id "
            f"JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id "
            f"LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id "
            f"LEFT JOIN adempiere.c_uom uom ON p.c_uom_id = uom.c_uom_id "
            f"JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id "
            f"WHERE {where} "
            f"GROUP BY p.value, p.name, pc.name, uom.name, {cur_label} "
            f"ORDER BY total_neto DESC "
            f"LIMIT :limit"
        )
        top_products = [
            {
                "codigo": r[0],
                "producto": r[1],
                "categoria": r[2],
                "unidad_medida": r[3],
                "moneda": r[4],
                "cantidad": float(r[5]) if r[5] else 0,
                "total_neto": float(r[6]),
            }
            for r in db.execute(top_products_q, params).fetchall()
        ]

        by_category_q = text(
            f"SELECT COALESCE(pc.name, 'Sin Categoría') AS categoria, "
            f"COUNT(DISTINCT p.m_product_id) AS productos, "
            f"SUM(il.qtyinvoiced) AS cantidad, "
            f"COALESCE(SUM(il.linenetamt), 0) AS total_neto "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id "
            f"JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id "
            f"LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id "
            f"LEFT JOIN adempiere.c_uom uom ON p.c_uom_id = uom.c_uom_id "
            f"JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id "
            f"WHERE {where} "
            f"GROUP BY pc.name "
            f"ORDER BY total_neto DESC"
        )
        del params["limit"]
        by_category = [
            {
                "categoria": r[0],
                "productos": r[1],
                "cantidad": float(r[2]) if r[2] else 0,
                "total_neto": float(r[3]),
            }
            for r in db.execute(by_category_q, params).fetchall()
        ]

        nc_conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
            "dt.docbasetype = 'ARC'",
        ]
        nc_params: dict = {"nc_limit": limit}
        _add_org_filter(nc_conditions, nc_params, org_ids, "i")
        _add_org_name_filter(nc_conditions, nc_params, org_name, "i")
        _add_currency_filter(nc_conditions, nc_params, currency_ids, "i")
        _add_date_filter(nc_conditions, nc_params, date_from, date_to, mes, anio, "i.dateinvoiced")

        if product_search:
            _add_product_search_filter(nc_conditions, nc_params, product_search)
        if category_search:
            nc_conditions.append("pc.name ILIKE :cat_search")
            nc_params["cat_search"] = f"%{category_search}%"
        if only_skus:
            nc_conditions.append("pc.iskpi = 'Y'")

        nc_where = " AND ".join(nc_conditions)

        nc_q = text(
            f"SELECT p.value AS codigo, p.name AS producto, "
            f"COALESCE(pc.name, 'Sin Categoría') AS categoria, "
            f"COALESCE(uom.name, '') AS unidad_medida, "
            f"{cur_label} AS moneda, "
            f"SUM(il.qtyinvoiced) AS cantidad_nc, "
            f"COALESCE(SUM(il.linenetamt), 0) AS monto_nc, "
            f"COUNT(DISTINCT i.c_invoice_id) AS notas_credito "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id "
            f"JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id "
            f"LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id "
            f"LEFT JOIN adempiere.c_uom uom ON p.c_uom_id = uom.c_uom_id "
            f"JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id "
            f"WHERE {nc_where} "
            f"GROUP BY p.value, p.name, pc.name, uom.name, {cur_label} "
            f"ORDER BY monto_nc DESC "
            f"LIMIT :nc_limit"
        )
        nc_products = [
            {
                "codigo": r[0],
                "producto": r[1],
                "categoria": r[2],
                "unidad_medida": r[3],
                "moneda": r[4],
                "cantidad_nc": float(r[5]) if r[5] else 0,
                "monto_nc": float(r[6]),
                "notas_credito": r[7],
            }
            for r in db.execute(nc_q, nc_params).fetchall()
        ]

        return {
            "anio": anio,
            "top_productos": top_products,
            "por_categoria": by_category,
            "notas_credito_por_producto": nc_products,
        }
    finally:
        db.close()

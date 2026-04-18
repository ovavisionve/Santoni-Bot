"""Supply purchase queries: by product, pending orders, price comparison."""

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
    execute_idempiere_query,
    logger,
)
from .common import _add_product_search_filter

# ---------------------------------------------------------------------------
# COMPRAS INSUMOS (Supply Purchases)
# ---------------------------------------------------------------------------

def build_supply_purchases(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> dict:
    """Supply purchases from iDempiere: purchase invoices (issotrx='N')."""
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")
        _add_currency_filter(conditions, params, currency_ids, "i")

        where = " AND ".join(conditions)

        # Totals
        totals_q = text(
            f"SELECT COUNT(DISTINCT i.c_invoice_id) AS total_ordenes, "
            f"COALESCE(SUM(i.totallines), 0) AS total_monto "
            f"FROM adempiere.c_invoice i WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_ordenes": row[0] if row else 0,
            "total_monto": float(row[1]) if row else 0.0,
        }

        # By supplier (top 20)
        by_supplier_q = text(
            f"SELECT bp.name AS proveedor, "
            f"COUNT(DISTINCT i.c_invoice_id) AS facturas, "
            f"COALESCE(SUM(i.totallines), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name ORDER BY total DESC LIMIT 20"
        )
        by_supplier = [
            {"proveedor": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_supplier_q, params).fetchall()
        ]

        # By month
        by_month_q = text(
            f"SELECT EXTRACT(MONTH FROM i.dateinvoiced)::int AS mes, "
            f"COUNT(DISTINCT i.c_invoice_id) AS facturas, "
            f"COALESCE(SUM(i.totallines), 0) AS total "
            f"FROM adempiere.c_invoice i WHERE {where} "
            f"GROUP BY EXTRACT(MONTH FROM i.dateinvoiced) ORDER BY mes"
        )
        by_month = [
            {"mes": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_month_q, params).fetchall()
        ]

        # By product category (top items purchased)
        by_product_q = text(
            f"SELECT p.value AS codigo, p.name AS producto, "
            f"COALESCE(SUM(il.linenetamt), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id "
            f"JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id "
            f"WHERE {where} "
            f"GROUP BY p.value, p.name ORDER BY total DESC LIMIT 20"
        )
        by_product = [
            {"codigo": r[0], "producto": r[1], "total": float(r[2])}
            for r in db.execute(by_product_q, params).fetchall()
        ]

        # Determine currency label for the agent
        if currency_ids:
            _VES = [205]
            currency_label = "USD" if currency_ids != _VES else "VES"
        else:
            currency_label = "Todas las monedas (mixto)"

        return {
            "anio": anio,
            "mes": mes,
            "moneda": currency_label,
            "totales": totals,
            "por_proveedor": by_supplier,
            "por_mes": by_month,
            "por_producto": by_product,
        }
    finally:
        db.close()


def build_product_purchase_history(
    product_search: str,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_name: str | None = None,
) -> list[dict]:
    """Purchase history for a specific product from iDempiere.

    Searches by product code (value) or name. Returns recent purchase invoices
    for that product with supplier, quantity, unit price, and total.
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")

        # Match by product value (code) or name (word-based for text searches)
        _add_product_search_filter(conditions, params, product_search, prefix="search")

        where = " AND ".join(conditions)

        q = text(
            f"SELECT p.value AS codigo_producto, p.name AS producto, "
            f"bp.name AS proveedor, i.documentno AS factura, "
            f"i.dateinvoiced AS fecha, "
            f"il.qtyinvoiced AS cantidad, "
            f"il.priceactual AS precio_unitario, "
            f"il.linenetamt AS total_linea "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id "
            f"JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"ORDER BY i.dateinvoiced DESC "
            f"LIMIT 50"
        )
        rows = db.execute(q, params).fetchall()
        return [
            {
                "codigo_producto": r[0],
                "producto": r[1],
                "proveedor": r[2],
                "factura": r[3],
                "fecha": r[4].isoformat() if r[4] else None,
                "cantidad": float(r[5]),
                "precio_unitario": float(r[6]),
                "total_linea": float(r[7]),
            }
            for r in rows
        ]
    finally:
        db.close()


def build_pending_purchase_orders(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    product_search: str | None = None,
    org_name: str | None = None,
) -> dict:
    """Pending purchase orders from iDempiere c_order (issotrx='N').

    Includes orders in progress (docstatus IN ('DR','IP','CO') that have
    not been fully invoiced/received).
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "o.issotrx = 'N'",
            "o.isactive = 'Y'",
            "o.docstatus IN ('DR', 'IP', 'CO')",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "o")
        _add_org_name_filter(conditions, params, org_name, "o")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "o.dateordered")
        _add_currency_filter(conditions, params, currency_ids, "o")

        if product_search:
            conditions.append(
                "EXISTS (SELECT 1 FROM adempiere.c_orderline ol2 "
                "JOIN adempiere.m_product p2 ON ol2.m_product_id = p2.m_product_id "
                "WHERE ol2.c_order_id = o.c_order_id "
                "AND (p2.name ILIKE :po_prod OR p2.value ILIKE :po_prod))"
            )
            params["po_prod"] = f"%{product_search}%"

        where = " AND ".join(conditions)

        # Totals
        totals_q = text(
            f"SELECT COUNT(DISTINCT o.c_order_id) AS total_ordenes, "
            f"COALESCE(SUM(o.grandtotal), 0) AS total_monto "
            f"FROM adempiere.c_order o WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_ordenes": row[0] if row else 0,
            "total_monto": float(row[1]) if row else 0.0,
        }

        # By status
        by_status_q = text(
            f"SELECT "
            f"CASE o.docstatus "
            f"  WHEN 'DR' THEN 'Borrador' "
            f"  WHEN 'IP' THEN 'En Proceso' "
            f"  WHEN 'CO' THEN 'Completada' "
            f"  ELSE o.docstatus END AS estado, "
            f"COUNT(DISTINCT o.c_order_id) AS ordenes, "
            f"COALESCE(SUM(o.grandtotal), 0) AS total "
            f"FROM adempiere.c_order o WHERE {where} "
            f"GROUP BY o.docstatus ORDER BY total DESC"
        )
        by_status = [
            {"estado": r[0], "ordenes": r[1], "total": float(r[2])}
            for r in db.execute(by_status_q, params).fetchall()
        ]

        # By supplier (top 20)
        by_supplier_q = text(
            f"SELECT bp.name AS proveedor, "
            f"COUNT(DISTINCT o.c_order_id) AS ordenes, "
            f"COALESCE(SUM(o.grandtotal), 0) AS total "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name ORDER BY total DESC LIMIT 20"
        )
        by_supplier = [
            {"proveedor": r[0], "ordenes": r[1], "total": float(r[2])}
            for r in db.execute(by_supplier_q, params).fetchall()
        ]

        # Recent orders detail (last 30)
        detail_q = text(
            f"SELECT o.documentno, o.dateordered, "
            f"bp.name AS proveedor, "
            f"CASE o.docstatus "
            f"  WHEN 'DR' THEN 'Borrador' "
            f"  WHEN 'IP' THEN 'En Proceso' "
            f"  WHEN 'CO' THEN 'Completada' "
            f"  ELSE o.docstatus END AS estado, "
            f"o.grandtotal, "
            f"COALESCE(org.name, '') AS organizacion "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
            f"LEFT JOIN adempiere.ad_org org ON o.ad_org_id = org.ad_org_id "
            f"WHERE {where} "
            f"ORDER BY o.dateordered DESC LIMIT 30"
        )
        detail = [
            {
                "documento": r[0],
                "fecha": r[1].isoformat() if r[1] else None,
                "proveedor": r[2],
                "estado": r[3],
                "monto": float(r[4]) if r[4] else 0.0,
                "organizacion": r[5],
            }
            for r in db.execute(detail_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "mes": mes,
            "totales": totals,
            "por_estado": by_status,
            "por_proveedor": by_supplier,
            "detalle_ordenes": detail,
        }
    finally:
        db.close()


def build_supplier_price_comparison(
    product_search: str,
    org_ids: list[int] | None = None,
    anio: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
) -> list[dict]:
    """Compare prices from different suppliers for a specific product.

    Returns min, avg, max price per supplier with last purchase date.
    """
    db = _get_session(date_from=date_from, date_to=date_to, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_date_filter(conditions, params, date_from, date_to, None, anio, "i.dateinvoiced")
        _add_product_search_filter(conditions, params, product_search, prefix="cmp")

        where = " AND ".join(conditions)

        q = text(
            f"SELECT bp.name AS proveedor, "
            f"p.name AS producto, "
            f"COUNT(*) AS compras, "
            f"MIN(il.priceactual) AS precio_minimo, "
            f"AVG(il.priceactual) AS precio_promedio, "
            f"MAX(il.priceactual) AS precio_maximo, "
            f"MAX(i.dateinvoiced) AS ultima_compra, "
            f"SUM(il.qtyinvoiced) AS cantidad_total "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id "
            f"JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name, p.name "
            f"ORDER BY precio_promedio ASC "
            f"LIMIT 30"
        )
        rows = db.execute(q, params).fetchall()
        return [
            {
                "proveedor": r[0],
                "producto": r[1],
                "compras": r[2],
                "precio_minimo": float(r[3]) if r[3] else 0.0,
                "precio_promedio": float(r[4]) if r[4] else 0.0,
                "precio_maximo": float(r[5]) if r[5] else 0.0,
                "ultima_compra": r[6].isoformat() if r[6] else None,
                "cantidad_total": float(r[7]) if r[7] else 0.0,
            }
            for r in rows
        ]
    finally:
        db.close()


def build_purchase_payment_status(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
) -> dict:
    """Purchase invoice payment status from iDempiere.

    Shows paid vs unpaid purchase invoices (c_invoice where issotrx='N').
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")

        where = " AND ".join(conditions)

        q = text(
            f"SELECT "
            f"CASE WHEN {_OPEN_EXPR} <= 0 THEN 'Pagada' ELSE 'Pendiente' END AS estado_pago, "
            f"COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.totallines), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"{_ALLOC_JOIN}"
            f"WHERE {where} "
            f"GROUP BY (CASE WHEN {_OPEN_EXPR} <= 0 THEN 'Pagada' ELSE 'Pendiente' END) ORDER BY total DESC"
        )
        rows = db.execute(q, params).fetchall()
        summary = [
            {"estado_pago": r[0], "facturas": r[1], "total": float(r[2])}
            for r in rows
        ]

        # Overdue unpaid invoices
        overdue_conditions = conditions + [
            f"{_OPEN_EXPR} > 0",
            "i.dateinvoiced + COALESCE("
            "  (SELECT pt.netdays FROM adempiere.c_paymentterm pt "
            "   WHERE pt.c_paymentterm_id = i.c_paymentterm_id), 30"
            ") < CURRENT_DATE",
        ]
        overdue_where = " AND ".join(overdue_conditions)

        overdue_q = text(
            f"SELECT bp.name AS proveedor, "
            f"i.documentno, i.dateinvoiced, "
            f"{_OPEN_EXPR} AS monto_pendiente, "
            f"CURRENT_DATE - i.dateinvoiced AS dias "
            f"FROM adempiere.c_invoice i "
            f"{_ALLOC_JOIN}"
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {overdue_where} "
            f"ORDER BY {_OPEN_EXPR} DESC LIMIT 20"
        )
        overdue = [
            {
                "proveedor": r[0],
                "factura": r[1],
                "fecha": r[2].isoformat() if r[2] else None,
                "monto": float(r[3]) if r[3] else 0.0,
                "dias_desde_factura": r[4],
            }
            for r in db.execute(overdue_q, params).fetchall()
        ]

        return {
            "resumen_pago": summary,
            "facturas_vencidas": overdue,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------

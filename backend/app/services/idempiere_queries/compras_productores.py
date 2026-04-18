"""Producer purchase queries: agricultural purchases, registered producers."""

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
from .ventas_helpers import _currency_label

# ---------------------------------------------------------------------------
# COMPRAS PRODUCTORES (Producer Purchases)
# ---------------------------------------------------------------------------

def build_producer_purchases(
    producto: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
) -> dict:
    """Producer purchases from iDempiere."""
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "o.issotrx = 'N'",
            "o.docstatus IN ('CO', 'CL')",
            "o.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "o")
        _add_org_name_filter(conditions, params, org_name, "o")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "o.dateordered")

        if producto:
            conditions.append("LOWER(p.name) LIKE :producto")
            params["producto"] = f"%{producto.lower()}%"

        where = " AND ".join(conditions)

        # Totals
        totals_q = text(
            f"SELECT COUNT(DISTINCT o.c_order_id) AS total_guias, "
            f"COALESCE(SUM(ol.qtyordered), 0) AS total_peso_neto_kg, "
            f"COALESCE(SUM(ol.linenetamt), 0) AS total_monto "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id "
            f"JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id "
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_guias": row[0] if row else 0,
            "total_peso_neto_kg": float(row[1]) if row else 0.0,
            "total_monto": float(row[2]) if row else 0.0,
        }

        # By product (no humedad/impureza — not available in c_order standard fields)
        by_product_q = text(
            f"SELECT p.name AS producto, "
            f"COUNT(DISTINCT o.c_order_id) AS guias, "
            f"COALESCE(SUM(ol.qtyordered), 0) AS peso_neto_kg, "
            f"COALESCE(SUM(ol.linenetamt), 0) AS monto_total "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id "
            f"JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id "
            f"WHERE {where} "
            f"GROUP BY p.name ORDER BY monto_total DESC"
        )
        by_product = [
            {
                "producto": r[0],
                "guias": r[1],
                "peso_neto_kg": float(r[2]),
                "monto_total": float(r[3]),
            }
            for r in db.execute(by_product_q, params).fetchall()
        ]

        # By producer (top 20)
        by_producer_q = text(
            f"SELECT bp.name AS nombre, "
            f"'' AS estado, '' AS municipio, "
            f"COUNT(DISTINCT o.c_order_id) AS guias, "
            f"COALESCE(SUM(ol.qtyordered), 0) AS peso_neto_kg, "
            f"COALESCE(SUM(ol.linenetamt), 0) AS monto_total "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id "
            f"JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id "
            f"JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name "
            f"ORDER BY monto_total DESC LIMIT 20"
        )
        by_producer = [
            {
                "nombre": r[0],
                "estado": r[1],
                "municipio": r[2],
                "guias": r[3],
                "peso_neto_kg": float(r[4]),
                "monto_total": float(r[5]),
            }
            for r in db.execute(by_producer_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "filtro_producto": producto,
            "totales": totals,
            "por_producto": by_product,
            "por_productor": by_producer,
        }
    finally:
        db.close()


def build_registered_producers(org_ids: list[int] | None = None) -> list[dict]:
    """Registered producers (vendors) from iDempiere c_bpartner."""
    db = IdempiereSession()
    try:
        conditions = [
            "bp.isactive = 'Y'",
            "bp.isvendor = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "bp")

        q = text(
            f"SELECT bp.name AS productor, bp.value AS codigo, "
            f"COALESCE(bpl.city, '') AS ciudad "
            f"FROM adempiere.c_bpartner bp "
            f"LEFT JOIN adempiere.c_bpartner_location bpl "
            f"  ON bp.c_bpartner_id = bpl.c_bpartner_id AND bpl.isactive = 'Y' "
            f"WHERE {' AND '.join(conditions)} "
            f"ORDER BY bp.name LIMIT 50"
        )
        return [
            {"productor": r[0], "codigo": r[1], "ciudad": r[2]}
            for r in db.execute(q, params).fetchall()
        ]
    finally:
        db.close()


def build_producer_pending_payments(
    producto: str | None = None,
    org_ids: list[int] | None = None,
    producer_name: str | None = None,
    currency_ids: list[int] | None = None,
) -> list[dict]:
    """Pending purchase invoices (not fully paid) from iDempiere.

    Uses invoiceopen(c_invoice_id, 0) > 0 to find truly unpaid invoices,
    since the ispaid flag may not update reliably when payments are allocated.
    Supports filtering by producer name (ILIKE) for specific producer debt queries.
    """
    db = IdempiereSession()
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
            "i.dateinvoiced >= (CURRENT_DATE - INTERVAL '2 years')",
            f"{_OPEN_EXPR} > 0",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_currency_filter(conditions, params, currency_ids, "i")

        if producto:
            conditions.append("LOWER(p.name) LIKE :producto")
            params["producto"] = f"%{producto.lower()}%"

        if producer_name:
            conditions.append("LOWER(bp.name) LIKE :producer_name")
            params["producer_name"] = f"%{producer_name.lower()}%"

        where = " AND ".join(conditions)

        currency_col = _currency_label("i")
        q = text(
            f"SELECT bp.name AS productor, i.documentno AS documento, "
            f"i.dateinvoiced::date AS fecha, "
            f"{_OPEN_EXPR} AS monto_pendiente, "
            f"i.grandtotal AS monto_original, "
            f"{currency_col} AS moneda "
            f"FROM adempiere.c_invoice i "
            f"{_ALLOC_JOIN}"
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"{'JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id ' if producto else ''}"
            f"{'JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id ' if producto else ''}"
            f"WHERE {where} "
            f"ORDER BY {_OPEN_EXPR} DESC LIMIT 30"
        )
        return [
            {
                "productor": r[0],
                "documento": r[1],
                "fecha": str(r[2]) if r[2] else "",
                "monto_pendiente": float(r[3]) if r[3] else 0.0,
                "monto_original": float(r[4]) if r[4] else 0.0,
                "moneda": r[5] if r[5] else "",
            }
            for r in db.execute(q, params).fetchall()
        ]
    finally:
        db.close()


def build_producer_price_analysis(
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Price analysis per product for producer purchases from iDempiere."""
    db = _get_session(date_from=date_from, date_to=date_to, anio=anio)
    try:
        conditions = [
            "o.issotrx = 'N'",
            "o.docstatus IN ('CO', 'CL')",
            "o.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "o")
        _add_date_filter(conditions, params, date_from, date_to, None, anio, "o.dateordered")

        where = " AND ".join(conditions)

        q = text(
            f"SELECT p.name AS producto, "
            f"MIN(ol.priceactual) AS precio_min, "
            f"AVG(ol.priceactual) AS precio_promedio, "
            f"MAX(ol.priceactual) AS precio_max, "
            f"COUNT(DISTINCT o.c_order_id) AS compras "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id "
            f"JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id "
            f"WHERE {where} "
            f"GROUP BY p.name ORDER BY compras DESC LIMIT 20"
        )
        return [
            {
                "producto": r[0],
                "precio_min": float(r[1]) if r[1] else 0.0,
                "precio_promedio": float(r[2]) if r[2] else 0.0,
                "precio_max": float(r[3]) if r[3] else 0.0,
                "compras": r[4],
            }
            for r in db.execute(q, params).fetchall()
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------

"""Extended ventas queries: receivables, by-product, orders, tax, branch."""

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
from .ventas_helpers import _currency_label, _add_salesrep_filter, _dedupe_salesrep_rows
from .common import _add_product_search_filter

from app.database import IdempiereSession

def build_overdue_receivables(
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
) -> dict:
    """Overdue accounts receivable from iDempiere (unpaid sales invoices).

    Returns summary totals by currency, top 20 clients by amount owed,
    and top 30 individual invoices by amount.

    Uses LEFT JOIN to c_allocationline aggregation to compute the real open
    amount (grandtotal minus allocated payments). Matches iDempiere's own
    invoiceopen() formula but runs ~100x faster (single hash join vs row-by-row
    PL/pgSQL function call).
    """
    db = IdempiereSession()
    try:
        # Build org filter for overdue receivables
        org_clause = ""
        org_params: dict = {}
        if org_ids:
            placeholders = ", ".join(f":org_{i}" for i in range(len(org_ids)))
            org_clause = f"AND i.ad_org_id IN ({placeholders}) "
            for i, org_id in enumerate(org_ids):
                org_params[f"org_{i}"] = org_id
        salesrep_clause = ""
        if salesrep_id:
            salesrep_clause = "AND i.salesrep_id = :salesrep_id "
            org_params["salesrep_id"] = salesrep_id

        base_where = (
            "i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') "
            "AND i.isactive = 'Y' "
            "AND dt.docbasetype = 'ARI' "
            "AND i.dateinvoiced >= (CURRENT_DATE - INTERVAL '3 years') "
            f"{org_clause}"
            f"{salesrep_clause}"
            "AND (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 "
            "THEN 30 ELSE pterm.netdays END) < CURRENT_DATE "
            f"AND {_OPEN_EXPR} > 0 "
        )

        base_joins = (
            "FROM adempiere.c_invoice i "
            f"{_ALLOC_JOIN}"
            "JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            "LEFT JOIN adempiere.ad_user sr ON i.salesrep_id = sr.ad_user_id "
            "LEFT JOIN adempiere.c_paymentterm pterm "
            "ON i.c_paymentterm_id = pterm.c_paymentterm_id "
            "JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id "
        )

        cur_label = _currency_label("i")

        # 1. Totals by currency
        totals_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS facturas, "
            f"COALESCE(SUM({_OPEN_EXPR}), 0) AS total_vencido "
            f"{base_joins}"
            f"WHERE {base_where} "
            f"GROUP BY {cur_label} ORDER BY total_vencido DESC"
        )
        totals_by_currency = [
            {"moneda": r[0], "facturas": r[1], "total_vencido": float(r[2])}
            for r in db.execute(totals_q, org_params).fetchall()
        ]

        # 2. Top 20 clients by total owed
        top_clients_q = text(
            f"SELECT bp.name AS cliente, "
            f"{cur_label} AS moneda, "
            f"COUNT(*) AS facturas, "
            f"COALESCE(SUM({_OPEN_EXPR}), 0) AS total_vencido, "
            f"MAX(CURRENT_DATE - (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 "
            f"THEN 30 ELSE pterm.netdays END)) AS max_dias_vencido "
            f"{base_joins}"
            f"WHERE {base_where} "
            f"GROUP BY bp.name, {cur_label} ORDER BY total_vencido DESC LIMIT 20"
        )
        top_clients = [
            {
                "cliente": r[0], "moneda": r[1], "facturas": r[2],
                "total_vencido": float(r[3]), "max_dias_vencido": r[4],
            }
            for r in db.execute(top_clients_q, org_params).fetchall()
        ]

        # 3. Top 30 individual invoices by open amount
        zone_cte = (
            "WITH client_zone AS ("
            "SELECT DISTINCT ON (bpl.c_bpartner_id) "
            "bpl.c_bpartner_id, sreg.name AS zona_name "
            "FROM adempiere.c_bpartner_location bpl "
            "LEFT JOIN adempiere.c_salesregion sreg "
            "ON bpl.c_salesregion_id = sreg.c_salesregion_id "
            "WHERE bpl.isactive = 'Y' "
            "ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC) "
        )
        detail_q = text(
            f"{zone_cte}"
            f"SELECT i.documentno AS numero_factura, bp.name AS cliente, "
            f"COALESCE(sr.name, '') AS vendedor, "
            f"COALESCE(cz.zona_name, '') AS zona, "
            f"{cur_label} AS moneda, "
            f"{_OPEN_EXPR} AS monto_pendiente, "
            f"i.grandtotal AS monto_original, "
            f"i.dateinvoiced AS fecha, "
            f"(i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 "
            f"THEN 30 ELSE pterm.netdays END)::date AS fecha_vencimiento, "
            f"CURRENT_DATE - (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 "
            f"THEN 30 ELSE pterm.netdays END) AS dias_vencido "
            f"{base_joins}"
            f"LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id "
            f"WHERE {base_where} "
            f"ORDER BY {_OPEN_EXPR} DESC "
            f"LIMIT 30"
        )
        top_invoices = [
            {
                "numero_factura": r[0], "cliente": r[1], "vendedor": r[2],
                "zona": r[3], "moneda": r[4],
                "monto_pendiente": float(r[5]),
                "monto_original": float(r[6]),
                "fecha": r[7].isoformat() if r[7] else None,
                "fecha_vencimiento": r[8].isoformat() if r[8] else None,
                "dias_vencido": r[9],
            }
            for r in db.execute(detail_q, org_params).fetchall()
        ]

        return {
            "totales_por_moneda": totals_by_currency,
            "top_clientes_morosos": top_clients,
            "top_facturas": top_invoices,
        }
    finally:
        db.close()


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

        # Top products by revenue
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

        # By category summary
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
        del params["limit"]  # not needed for category query
        by_category = [
            {
                "categoria": r[0],
                "productos": r[1],
                "cantidad": float(r[2]) if r[2] else 0,
                "total_neto": float(r[3]),
            }
            for r in db.execute(by_category_q, params).fetchall()
        ]

        # --- Notas de crédito (ARC) por producto ---
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


def build_sales_orders(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
    only_pending: bool = False,
) -> dict:
    """Sales orders from iDempiere c_order (issotrx='Y').

    Shows order pipeline: draft, in-progress, completed.
    If only_pending=True, only shows DR/IP (not yet invoiced).

    JOIN chain:
        c_order → c_bpartner (client)
        c_order → ad_user (salesperson via salesrep_id)
        c_order → c_project (branch/sucursal, optional)
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        if only_pending:
            statuses = "('DR', 'IP')"
        else:
            statuses = "('DR', 'IP', 'CO', 'CL')"

        conditions = [
            "o.issotrx = 'Y'",
            f"o.docstatus IN {statuses}",
            "o.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "o")
        _add_org_name_filter(conditions, params, org_name, "o")
        _add_currency_filter(conditions, params, currency_ids, "o")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "o.dateordered")

        where = " AND ".join(conditions)
        cur_label = _currency_label("o")

        # Totals by status
        totals_q = text(
            f"SELECT "
            f"CASE o.docstatus "
            f"  WHEN 'DR' THEN 'Borrador' "
            f"  WHEN 'IP' THEN 'En Proceso' "
            f"  WHEN 'CO' THEN 'Completada' "
            f"  WHEN 'CL' THEN 'Cerrada' "
            f"  ELSE o.docstatus END AS estado, "
            f"COUNT(*) AS ordenes, "
            f"COALESCE(SUM(o.grandtotal), 0) AS total "
            f"FROM adempiere.c_order o "
            f"WHERE {where} "
            f"GROUP BY o.docstatus ORDER BY total DESC"
        )
        by_status = [
            {"estado": r[0], "ordenes": r[1], "total": float(r[2])}
            for r in db.execute(totals_q, params).fetchall()
        ]

        # By salesperson
        by_salesperson_q = text(
            f"SELECT COALESCE(u.name, 'Sin Vendedor') AS vendedor, "
            f"COUNT(*) AS ordenes, "
            f"COALESCE(SUM(o.grandtotal), 0) AS total "
            f"FROM adempiere.c_order o "
            f"LEFT JOIN adempiere.ad_user u ON o.salesrep_id = u.ad_user_id "
            f"WHERE {where} "
            f"GROUP BY u.name ORDER BY total DESC LIMIT 20"
        )
        by_salesperson = [
            {"vendedor": r[0], "ordenes": r[1], "total": float(r[2])}
            for r in db.execute(by_salesperson_q, params).fetchall()
        ]
        by_salesperson = _dedupe_salesrep_rows(
            by_salesperson,
            numeric_keys=["ordenes", "total"],
            sort_key="total",
        )

        # By client (top 20)
        by_client_q = text(
            f"SELECT bp.name AS cliente, "
            f"COUNT(*) AS ordenes, "
            f"COALESCE(SUM(o.grandtotal), 0) AS total "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name ORDER BY total DESC LIMIT 20"
        )
        by_client = [
            {"cliente": r[0], "ordenes": r[1], "total": float(r[2])}
            for r in db.execute(by_client_q, params).fetchall()
        ]

        # By currency
        by_currency_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS ordenes, "
            f"COALESCE(SUM(o.grandtotal), 0) AS total "
            f"FROM adempiere.c_order o "
            f"WHERE {where} "
            f"GROUP BY {cur_label} ORDER BY total DESC"
        )
        by_currency = [
            {"moneda": r[0], "ordenes": r[1], "total": float(r[2])}
            for r in db.execute(by_currency_q, params).fetchall()
        ]

        # By branch (c_project = sucursal)
        by_branch_q = text(
            f"SELECT COALESCE(pj.name, 'Sin Sucursal') AS sucursal, "
            f"COUNT(*) AS ordenes, "
            f"COALESCE(SUM(o.grandtotal), 0) AS total "
            f"FROM adempiere.c_order o "
            f"LEFT JOIN adempiere.c_project pj ON o.c_project_id = pj.c_project_id "
            f"WHERE {where} "
            f"GROUP BY pj.name ORDER BY total DESC"
        )
        by_branch = [
            {"sucursal": r[0], "ordenes": r[1], "total": float(r[2])}
            for r in db.execute(by_branch_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "por_estado": by_status,
            "por_vendedor": by_salesperson,
            "por_cliente": by_client,
            "por_moneda": by_currency,
            "por_sucursal": by_branch,
        }
    finally:
        db.close()


def build_exchange_rates(
    limit: int = 30,
) -> list[dict]:
    """Recent exchange rates from iDempiere c_conversion_rate.

    Shows the most recent VES→USD and USD→VES rates.
    Always queries live iDempiere (no date-based routing).
    """
    db = IdempiereSession()
    try:
        q = text(
            "SELECT "
            "cf.iso_code AS moneda_origen, "
            "ct.iso_code AS moneda_destino, "
            "cr.multiplyrate AS tasa_multiplicar, "
            "cr.dividerate AS tasa_dividir, "
            "cr.validfrom AS vigente_desde, "
            "cr.validto AS vigente_hasta "
            "FROM adempiere.c_conversion_rate cr "
            "JOIN adempiere.c_currency cf ON cr.c_currency_id = cf.c_currency_id "
            "JOIN adempiere.c_currency ct ON cr.c_currency_id_to = ct.c_currency_id "
            "WHERE cr.isactive = 'Y' "
            "ORDER BY cr.validfrom DESC "
            "LIMIT :limit"
        )
        rows = db.execute(q, {"limit": limit}).fetchall()
        return [
            {
                "moneda_origen": r[0],
                "moneda_destino": r[1],
                "tasa_multiplicar": float(r[2]) if r[2] else None,
                "tasa_dividir": float(r[3]) if r[3] else None,
                "vigente_desde": r[4].isoformat() if r[4] else None,
                "vigente_hasta": r[5].isoformat() if r[5] else None,
            }
            for r in rows
        ]
    finally:
        db.close()


def build_sales_tax_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> dict:
    """Tax breakdown on sales invoices from iDempiere.

    JOIN chain:
        c_invoice → c_invoiceline → c_tax (tax applied to each line)
    Shows total base amount and tax amount grouped by tax type.
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
            "dt.docbasetype = 'ARI'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_currency_filter(conditions, params, currency_ids, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")

        where = " AND ".join(conditions)
        cur_label = _currency_label("i")

        q = text(
            f"SELECT COALESCE(t.name, 'Sin Impuesto') AS impuesto, "
            f"COALESCE(t.rate, 0) AS tasa_porcentaje, "
            f"{cur_label} AS moneda, "
            f"COUNT(DISTINCT i.c_invoice_id) AS facturas, "
            f"COALESCE(SUM(il.linenetamt), 0) AS base_imponible, "
            f"COALESCE(SUM(il.linenetamt * t.rate / 100), 0) AS monto_impuesto "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id "
            f"LEFT JOIN adempiere.c_tax t ON il.c_tax_id = t.c_tax_id "
            f"JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id "
            f"WHERE {where} "
            f"GROUP BY t.name, t.rate, {cur_label} "
            f"ORDER BY monto_impuesto DESC"
        )
        rows = db.execute(q, params).fetchall()
        by_tax = [
            {
                "impuesto": r[0],
                "tasa_porcentaje": float(r[1]),
                "moneda": r[2],
                "facturas": r[3],
                "base_imponible": float(r[4]),
                "monto_impuesto": float(r[5]),
            }
            for r in rows
        ]

        # Withholding totals (retenciones IVA)
        wh_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.withholdingamt), 0) AS total_retenciones "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id "
            f"WHERE {where} AND COALESCE(i.withholdingamt, 0) > 0 "
            f"GROUP BY {cur_label}"
        )
        wh_rows = db.execute(wh_q, params).fetchall()
        retenciones = [
            {
                "moneda": r[0],
                "facturas": r[1],
                "total_retenciones": float(r[2]),
            }
            for r in wh_rows
        ]

        return {
            "anio": anio,
            "por_impuesto": by_tax,
            "retenciones": retenciones,
        }
    finally:
        db.close()


def build_sales_by_branch(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> list[dict]:
    """Sales grouped by branch (c_project = sucursal) from iDempiere.

    JOIN chain:
        c_invoice → c_project (branch assigned to the invoice)
        c_invoice → c_doctype (to separate ARI from ARC)
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_currency_filter(conditions, params, currency_ids, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")

        where = " AND ".join(conditions)
        cur_label = _currency_label("i")

        q = text(
            f"SELECT COALESCE(pj.name, 'Sin Sucursal') AS sucursal, "
            f"{cur_label} AS moneda, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END), 0) AS venta_neta "
            f"FROM adempiere.c_invoice i "
            f"LEFT JOIN adempiere.c_project pj ON i.c_project_id = pj.c_project_id "
            f"JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id "
            f"WHERE {where} "
            f"GROUP BY pj.name, {cur_label} "
            f"ORDER BY venta_neta DESC"
        )
        rows = db.execute(q, params).fetchall()
        return [
            {
                "sucursal": r[0],
                "moneda": r[1],
                "facturas": r[2],
                "venta_neta": float(r[3]),
            }
            for r in rows
        ]
    finally:
        db.close()



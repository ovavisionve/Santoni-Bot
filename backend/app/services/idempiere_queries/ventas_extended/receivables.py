"""Overdue accounts receivable queries."""

from sqlalchemy import text

from app.database import IdempiereSession

from ..common import _ALLOC_JOIN, _OPEN_EXPR
from ..ventas_helpers import _currency_label


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

"""
iDempiere query functions for production environment.
All queries target the adempiere schema on PostgreSQL 13 (192.168.1.73).
User 'ova' has SELECT-only permissions.

IMPORTANT: These queries are based on standard iDempiere table structure.
They need validation after connecting to Santoni's actual iDempiere instance
(Phase 4 of deployment). Column names and custom tables may differ.

Convention:
- issotrx = 'Y' → Sales transaction (venta)
- issotrx = 'N' → Purchase transaction (compra)
- docstatus = 'CO' → Completed document
- isactive = 'Y' → Active record
"""

import re
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.database import IdempiereSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _convert_value(val):
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, date):
        return val.isoformat()
    return val


def _rows_to_dicts(rows, columns) -> list[dict]:
    return [
        {col: _convert_value(row[i]) for i, col in enumerate(columns)}
        for row in rows
    ]


def _add_org_filter(
    conditions: list[str],
    params: dict,
    org_ids: list[int] | None,
    table_alias: str,
) -> None:
    """Add ad_org_id IN (...) filter if org_ids is provided.
    Modifies conditions and params in place."""
    if org_ids:
        placeholders = ", ".join(f":org_{i}" for i in range(len(org_ids)))
        conditions.append(f"{table_alias}.ad_org_id IN ({placeholders})")
        for i, org_id in enumerate(org_ids):
            params[f"org_{i}"] = org_id


def _add_org_name_filter(
    conditions: list[str],
    params: dict,
    org_name: str | None,
    table_alias: str,
) -> None:
    """Add org name ILIKE filter via a subquery on ad_org.
    E.g. org_name='inpromaiz' → i.ad_org_id IN (SELECT ad_org_id FROM ad_org WHERE name ILIKE '%inpromaiz%')"""
    if org_name:
        conditions.append(
            f"{table_alias}.ad_org_id IN ("
            f"SELECT o.ad_org_id FROM adempiere.ad_org o "
            f"WHERE o.name ILIKE :org_name_filter)"
        )
        params["org_name_filter"] = f"%{org_name}%"


def _add_currency_filter(
    conditions: list[str],
    params: dict,
    currency_ids: list[int] | None,
    table_alias: str,
) -> None:
    """Add c_currency_id IN (...) filter if currency_ids is provided.
    Supports multiple IDs because Santoni uses several currency entries for dollars.
    Modifies conditions and params in place."""
    if currency_ids:
        placeholders = ", ".join(f":cur_{i}" for i in range(len(currency_ids)))
        conditions.append(f"{table_alias}.c_currency_id IN ({placeholders})")
        for i, cid in enumerate(currency_ids):
            params[f"cur_{i}"] = cid


def _add_date_filter(
    conditions: list[str],
    params: dict,
    date_from: str | None,
    date_to: str | None,
    mes: int | None,
    anio: int | None,
    date_column: str,
) -> None:
    """Add date filters. date_from/date_to override mes/anio when both provided."""
    if date_from and date_to:
        conditions.append(f"{date_column} >= :date_from")
        conditions.append(f"{date_column} <= :date_to")
        params["date_from"] = date_from
        params["date_to"] = date_to
    else:
        if anio:
            conditions.append(f"EXTRACT(YEAR FROM {date_column}) = :anio")
            params["anio"] = anio
        if mes:
            conditions.append(f"EXTRACT(MONTH FROM {date_column}) = :mes")
            params["mes"] = mes


_PRODUCT_STOP_WORDS = {
    'de', 'del', 'las', 'los', 'en', 'el', 'la', 'para', 'por',
    'con', 'sin', 'un', 'una', 'al', 'que', 'se', 'ha', 'y',
}


def _add_product_search_filter(
    conditions: list[str],
    params: dict,
    product_search: str,
    prefix: str = "prod",
) -> None:
    """Add flexible product search conditions on p.name / p.value.

    For product codes (e.g. REP-LAMI-0037), uses exact substring ILIKE.
    For text searches, splits into words and uses AND ILIKE per word
    with basic Spanish de-pluralisation (cajas→caja, laminas→lamina).
    """
    # Product code: exact substring match
    if re.search(r'[A-Za-z]{2,}-[A-Za-z]{2,}-\d+', product_search):
        params[f"{prefix}_search"] = f"%{product_search}%"
        conditions.append(
            f"(p.name ILIKE :{prefix}_search OR p.value ILIKE :{prefix}_search)"
        )
        return

    # Text search: split into meaningful words
    words = [
        w for w in product_search.lower().split()
        if w not in _PRODUCT_STOP_WORDS and len(w) >= 2
    ]

    if not words:
        # Fallback to exact substring
        params[f"{prefix}_search"] = f"%{product_search}%"
        conditions.append(
            f"(p.name ILIKE :{prefix}_search OR p.value ILIKE :{prefix}_search)"
        )
        return

    # De-pluralise: strip trailing 's' for common Spanish plurals
    clean_words = []
    for w in words:
        if len(w) > 3 and w.endswith('s') and w[-2] in 'aeiou':
            clean_words.append(w[:-1])
        else:
            clean_words.append(w)

    word_conds = []
    for i, w in enumerate(clean_words):
        pk = f"{prefix}_w{i}"
        params[pk] = f"%{w}%"
        word_conds.append(f"(p.name ILIKE :{pk} OR p.value ILIKE :{pk})")

    conditions.append(f"({' AND '.join(word_conds)})")


def execute_idempiere_query(query: str, params: dict | None = None) -> list[dict]:
    """Execute a read-only query against iDempiere.
    The connection is enforced read-only at the database level."""
    q = query.strip().rstrip(";")
    if not q.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed on iDempiere.")

    db = IdempiereSession()
    try:
        result = db.execute(text(q), params or {})
        columns = list(result.keys())
        rows = result.fetchall()
        return _rows_to_dicts(rows, columns)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# VENTAS (Sales)
# ---------------------------------------------------------------------------

def _currency_label(alias: str = "i") -> str:
    """SQL CASE expression that groups Santoni's multiple USD currency entries
    into a single 'USD' label and VES into 'Bs.' for display."""
    return (
        f"CASE WHEN {alias}.c_currency_id = 205 THEN 'Bs.' "
        f"WHEN {alias}.c_currency_id IN "
        f"(100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) "
        f"THEN 'USD' ELSE 'Otro' END"
    )


def _add_salesrep_filter(conditions: list, params: dict, salesrep_id: int | None, alias: str = "i"):
    """Add salesrep_id filter to conditions if provided."""
    if salesrep_id:
        conditions.append(f"{alias}.salesrep_id = :salesrep_id")
        params["salesrep_id"] = salesrep_id


def build_sales_summary(
    zona: str | None = None,
    vendedor: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> dict:
    """Sales summary from iDempiere c_invoice (issotrx='Y')."""
    db = IdempiereSession()
    try:
        conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus = 'CO'",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_salesrep_filter(conditions, params, salesrep_id, "i")
        _add_currency_filter(conditions, params, currency_ids, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")

        if vendedor:
            conditions.append("COALESCE(sr.name, '') ILIKE :vendedor")
            params["vendedor"] = f"%{vendedor}%"
        if zona:
            conditions.append("COALESCE(cz.zona_name, '') ILIKE :zona")
            params["zona"] = f"%{zona}%"

        where = " AND ".join(conditions)

        # CTE: one zone per client (avoids JOIN multiplication from
        # c_bpartner_location having multiple rows per client)
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
        joins = (
            "LEFT JOIN adempiere.c_bpartner sr "
            "ON i.salesrep_id = sr.c_bpartner_id "
            "LEFT JOIN client_zone cz "
            "ON i.c_bpartner_id = cz.c_bpartner_id "
        )

        # Totals
        totals_q = text(
            f"{zone_cte}"
            f"SELECT COUNT(*) AS total_facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_facturado, "
            f"COALESCE(SUM(i.totallines), 0) AS total_neto, "
            f"COALESCE(SUM(i.grandtotal - i.totallines), 0) AS total_iva "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_facturas": row[0] if row else 0,
            "total_facturado": float(row[1]) if row else 0.0,
            "total_neto": float(row[2]) if row else 0.0,
            "total_iva": float(row[3]) if row else 0.0,
        }

        # By sales region (zona)
        by_zone_q = text(
            f"{zone_cte}"
            f"SELECT COALESCE(cz.zona_name, 'Sin Zona') AS zona, COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY cz.zona_name ORDER BY total DESC"
        )
        by_zone = [
            {"zona": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_zone_q, params).fetchall()
        ]

        # By distributor (salesrep_id tracks distributors, not internal salespeople)
        by_distributor_q = text(
            f"{zone_cte}"
            f"SELECT COALESCE(sr.name, 'Sin Distribuidor') AS distribuidor, COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY sr.name ORDER BY total DESC"
        )
        by_distributor = [
            {"distribuidor": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_distributor_q, params).fetchall()
        ]

        # By month
        by_month_q = text(
            f"{zone_cte}"
            f"SELECT EXTRACT(MONTH FROM i.dateinvoiced)::int AS mes, COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY EXTRACT(MONTH FROM i.dateinvoiced) ORDER BY mes"
        )
        by_month = [
            {"mes": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_month_q, params).fetchall()
        ]

        # By currency (so user sees totals per currency instead of mixed)
        cur_label = _currency_label("i")
        by_currency_q = text(
            f"{zone_cte}"
            f"SELECT {cur_label} AS moneda, COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_facturado, "
            f"COALESCE(SUM(i.totallines), 0) AS total_neto "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY {cur_label} ORDER BY total_facturado DESC"
        )
        by_currency = [
            {"moneda": r[0], "facturas": r[1], "total_facturado": float(r[2]), "total_neto": float(r[3])}
            for r in db.execute(by_currency_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "filtros": {"zona": zona, "vendedor": vendedor, "mes": mes},
            "totales": totals,
            "por_zona": by_zone,
            "por_distribuidor": by_distributor,
            "por_mes": by_month,
            "por_moneda": by_currency,
        }
    finally:
        db.close()


def build_collection_summary(
    zona: str | None = None,
    vendedor: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> dict:
    """Collection summary from iDempiere c_payment (isreceipt='Y')."""
    db = IdempiereSession()
    try:
        conditions = [
            "p.isreceipt = 'Y'",
            "p.docstatus = 'CO'",
            "p.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "p")
        _add_org_name_filter(conditions, params, org_name, "p")
        _add_currency_filter(conditions, params, currency_ids, "p")
        # Payments don't have salesrep_id directly; filter via linked invoice
        if salesrep_id:
            conditions.append(
                "EXISTS (SELECT 1 FROM adempiere.c_allocationline al "
                "JOIN adempiere.c_invoice inv ON al.c_invoice_id = inv.c_invoice_id "
                "WHERE al.c_payment_id = p.c_payment_id AND inv.salesrep_id = :salesrep_id)"
            )
            params["salesrep_id"] = salesrep_id
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "p.datetrx")

        where = " AND ".join(conditions)

        # Totals
        totals_q = text(
            f"SELECT COUNT(*) AS total_recibos, "
            f"COALESCE(SUM(p.payamt), 0) AS total_cobrado "
            f"FROM adempiere.c_payment p WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_recibos": row[0] if row else 0,
            "total_cobrado": float(row[1]) if row else 0.0,
        }

        # By tender type (payment method)
        by_method_q = text(
            f"SELECT CASE p.tendertype "
            f"  WHEN 'X' THEN 'Transferencia' "
            f"  WHEN 'C' THEN 'Cheque' "
            f"  WHEN 'K' THEN 'Efectivo' "
            f"  WHEN 'D' THEN 'Depósito' "
            f"  WHEN 'T' THEN 'Tarjeta' "
            f"  ELSE p.tendertype END AS metodo_pago, "
            f"COUNT(*) AS recibos, "
            f"COALESCE(SUM(p.payamt), 0) AS total "
            f"FROM adempiere.c_payment p WHERE {where} "
            f"GROUP BY p.tendertype ORDER BY total DESC"
        )
        by_method = [
            {"metodo_pago": r[0], "recibos": r[1], "total": float(r[2])}
            for r in db.execute(by_method_q, params).fetchall()
        ]

        # By client
        by_vendor_q = text(
            f"SELECT bp.name AS vendedor, COUNT(*) AS recibos, "
            f"COALESCE(SUM(p.payamt), 0) AS total "
            f"FROM adempiere.c_payment p "
            f"JOIN adempiere.c_bpartner bp ON p.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name ORDER BY total DESC LIMIT 30"
        )
        by_vendor = [
            {"vendedor": r[0], "recibos": r[1], "total": float(r[2])}
            for r in db.execute(by_vendor_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "filtros": {"zona": zona, "vendedor": vendedor, "mes": mes},
            "totales": totals,
            "por_metodo_pago": by_method,
            "por_vendedor": by_vendor,
        }
    finally:
        db.close()


def build_top_clients(
    limit: int = 20,
    zona: str | None = None,
    vendedor: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> list[dict]:
    """Top clients by invoiced amount from iDempiere.

    Uses client_zone CTE to avoid JOIN multiplication from
    c_bpartner_location having multiple rows per client.
    """
    db = IdempiereSession()
    try:
        conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus = 'CO'",
            "i.isactive = 'Y'",
        ]
        params: dict = {"limit": limit}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_salesrep_filter(conditions, params, salesrep_id, "i")
        _add_currency_filter(conditions, params, currency_ids, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")

        where = " AND ".join(conditions)

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

        cur_label = _currency_label("i")
        q = text(
            f"{zone_cte}"
            f"SELECT bp.value AS codigo, bp.name AS nombre, "
            f"COALESCE(cz.zona_name, 'Sin Zona') AS zona, "
            f"COALESCE(sr.name, 'Sin Distribuidor') AS distribuidor, "
            f"COALESCE(bpg.name, 'Sin Tipología') AS tipologia, "
            f"{cur_label} AS moneda, "
            f"COUNT(i.c_invoice_id) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_facturado "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id "
            f"LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id "
            f"LEFT JOIN adempiere.c_bp_group bpg ON bp.c_bp_group_id = bpg.c_bp_group_id "
            f"WHERE {where} "
            f"GROUP BY bp.value, bp.name, cz.zona_name, sr.name, bpg.name, {cur_label} "
            f"ORDER BY total_facturado DESC "
            f"LIMIT :limit"
        )
        rows = db.execute(q, params).fetchall()
        return [
            {
                "codigo": r[0],
                "nombre": r[1],
                "zona": r[2],
                "distribuidor": r[3],
                "tipologia": r[4],
                "moneda": r[5],
                "facturas": r[6],
                "total_facturado": float(r[7]),
            }
            for r in rows
        ]
    finally:
        db.close()


def build_overdue_receivables(
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
) -> list[dict]:
    """Overdue accounts receivable from iDempiere (unpaid sales invoices).

    Uses client_zone CTE for zone info, and filters to recent invoices
    (last 3 years) with amounts > 100 to exclude old residual balances.
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

        q = text(
            "WITH client_zone AS ("
            "SELECT DISTINCT ON (bpl.c_bpartner_id) "
            "bpl.c_bpartner_id, sreg.name AS zona_name "
            "FROM adempiere.c_bpartner_location bpl "
            "LEFT JOIN adempiere.c_salesregion sreg "
            "ON bpl.c_salesregion_id = sreg.c_salesregion_id "
            "WHERE bpl.isactive = 'Y' "
            "ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC) "
            "SELECT i.documentno AS numero_factura, bp.name AS cliente, "
            "COALESCE(sr.name, '') AS distribuidor, "
            "COALESCE(cz.zona_name, '') AS zona, "
            "i.grandtotal AS monto_total, i.dateinvoiced AS fecha, "
            "(i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END)::date AS fecha_vencimiento, "
            "CURRENT_DATE - (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END) AS dias_vencido "
            "FROM adempiere.c_invoice i "
            "JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            "LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id "
            "LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id "
            "LEFT JOIN adempiere.c_paymentterm pterm ON i.c_paymentterm_id = pterm.c_paymentterm_id "
            "WHERE i.issotrx = 'Y' AND i.docstatus = 'CO' AND i.ispaid = 'N' "
            "AND i.isactive = 'Y' "
            "AND i.dateinvoiced >= (CURRENT_DATE - INTERVAL '3 years') "
            "AND i.grandtotal > 100 "
            f"{org_clause}"
            f"{salesrep_clause}"
            "AND (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END) < CURRENT_DATE "
            "ORDER BY dias_vencido DESC "
            "LIMIT 50"
        )
        rows = db.execute(q, org_params).fetchall()
        return [
            {
                "numero_factura": r[0],
                "cliente": r[1],
                "distribuidor": r[2],
                "zona": r[3],
                "monto_total": float(r[4]),
                "fecha": r[5].isoformat() if r[5] else None,
                "fecha_vencimiento": r[6].isoformat() if r[6] else None,
                "dias_vencido": r[7],
            }
            for r in rows
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# FINANZAS (Finance)
# ---------------------------------------------------------------------------

def build_financial_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Financial summary from iDempiere: bank balances, receivables, payables."""
    # If date_from/date_to provided, nullify mes (range takes priority)
    if date_from and date_to:
        mes = None
    db = IdempiereSession()
    try:
        # Bank balances (filtered by org if applicable)
        bank_conditions = ["ba.isactive = 'Y'"]
        bank_params: dict = {}
        _add_org_filter(bank_conditions, bank_params, org_ids, "ba")
        bank_where = " AND ".join(bank_conditions)
        bank_q = text(
            f"SELECT b.name AS banco, ba.accountno AS numero_cuenta, "
            f"CASE WHEN ba.bankaccounttype = 'C' THEN 'Corriente' "
            f"     WHEN ba.bankaccounttype = 'S' THEN 'Ahorro' "
            f"     WHEN ba.bankaccounttype = 'I' THEN 'Inversión' "
            f"     ELSE ba.bankaccounttype END AS tipo, "
            f"COALESCE(c.iso_code, 'VES') AS moneda, "
            f"ba.currentbalance AS saldo "
            f"FROM adempiere.c_bankaccount ba "
            f"JOIN adempiere.c_bank b ON ba.c_bank_id = b.c_bank_id "
            f"LEFT JOIN adempiere.c_currency c ON ba.c_currency_id = c.c_currency_id "
            f"WHERE {bank_where} "
            f"ORDER BY b.name"
        )
        banks = [
            {
                "banco": r[0],
                "numero_cuenta": r[1],
                "tipo": r[2],
                "moneda": r[3],
                "saldo": float(r[4]) if r[4] else 0.0,
                "fecha_saldo": None,
            }
            for r in db.execute(bank_q, bank_params).fetchall()
        ]
        total_saldo_bancario = sum(b["saldo"] for b in banks)

        # Accounts receivable (unpaid sales invoices)
        ar_conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus = 'CO'",
            "i.ispaid = 'N'",
            "i.isactive = 'Y'",
        ]
        ar_params: dict = {}
        _add_org_filter(ar_conditions, ar_params, org_ids, "i")
        _add_date_filter(ar_conditions, ar_params, date_from, date_to, mes, anio, "i.dateinvoiced")

        ar_where = " AND ".join(ar_conditions)
        ar_q = text(
            f"SELECT COUNT(*) AS facturas_pendientes, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_por_cobrar "
            f"FROM adempiere.c_invoice i WHERE {ar_where}"
        )
        ar_row = db.execute(ar_q, ar_params).fetchone()
        receivables = {
            "facturas_pendientes": ar_row[0] if ar_row else 0,
            "total_por_cobrar": float(ar_row[1]) if ar_row else 0.0,
        }

        # Overdue receivables
        overdue_conds = [
            "i.issotrx = 'Y'",
            "i.docstatus = 'CO'",
            "i.ispaid = 'N'",
            "i.isactive = 'Y'",
            "(i.dateinvoiced + CASE WHEN COALESCE(pt.netdays, 0) = 0 THEN 30 ELSE pt.netdays END) < CURRENT_DATE",
        ]
        overdue_params: dict = {}
        _add_org_filter(overdue_conds, overdue_params, org_ids, "i")
        overdue_where = " AND ".join(overdue_conds)
        overdue_q = text(
            f"SELECT COUNT(*) AS facturas_vencidas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_vencido "
            f"FROM adempiere.c_invoice i "
            f"LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id "
            f"WHERE {overdue_where}"
        )
        overdue_row = db.execute(overdue_q, overdue_params).fetchone()
        receivables["facturas_vencidas"] = overdue_row[0] if overdue_row else 0
        receivables["total_vencido"] = float(overdue_row[1]) if overdue_row else 0.0

        # Accounts payable (unpaid purchase invoices)
        ap_conditions = [
            "i.issotrx = 'N'",
            "i.docstatus = 'CO'",
            "i.ispaid = 'N'",
            "i.isactive = 'Y'",
        ]
        ap_params: dict = {}
        _add_org_filter(ap_conditions, ap_params, org_ids, "i")
        _add_date_filter(ap_conditions, ap_params, date_from, date_to, mes, anio, "i.dateinvoiced")

        ap_where = " AND ".join(ap_conditions)
        ap_q = text(
            f"SELECT COUNT(*) AS facturas_pendientes, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_por_pagar "
            f"FROM adempiere.c_invoice i WHERE {ap_where}"
        )
        ap_row = db.execute(ap_q, ap_params).fetchone()
        payables = {
            "facturas_pendientes": ap_row[0] if ap_row else 0,
            "total_por_pagar": float(ap_row[1]) if ap_row else 0.0,
        }

        # Overdue payables
        overdue_ap_conds = [
            "i.issotrx = 'N'",
            "i.docstatus = 'CO'",
            "i.ispaid = 'N'",
            "i.isactive = 'Y'",
            "(i.dateinvoiced + CASE WHEN COALESCE(pt.netdays, 0) = 0 THEN 30 ELSE pt.netdays END) < CURRENT_DATE",
        ]
        overdue_ap_params: dict = {}
        _add_org_filter(overdue_ap_conds, overdue_ap_params, org_ids, "i")
        overdue_ap_where = " AND ".join(overdue_ap_conds)
        overdue_ap_q = text(
            f"SELECT COUNT(*) AS facturas_vencidas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_vencido "
            f"FROM adempiere.c_invoice i "
            f"LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id "
            f"WHERE {overdue_ap_where}"
        )
        overdue_ap_row = db.execute(overdue_ap_q, overdue_ap_params).fetchone()
        payables["facturas_vencidas"] = overdue_ap_row[0] if overdue_ap_row else 0
        payables["total_vencido"] = float(overdue_ap_row[1]) if overdue_ap_row else 0.0

        return {
            "anio": anio,
            "mes": mes,
            "saldos_bancarios": banks,
            "total_saldo_bancario": total_saldo_bancario,
            "cuentas_por_cobrar": receivables,
            "cuentas_por_pagar": payables,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# RRHH (Human Resources)
# ---------------------------------------------------------------------------

def build_employee_summary(org_ids: list[int] | None = None) -> dict:
    """Employee summary from iDempiere hr_employee (with DISTINCT to avoid duplicates).

    hr_employee has multiple rows per person (one per payroll period), so we use
    COUNT(DISTINCT e.c_bpartner_id) for accurate counts.  Organization is taken
    from hr_employee.ad_org_id (correctly assigned) instead of c_bpartner.ad_org_id
    (which often points to the wildcard '*' org).
    """
    db = IdempiereSession()
    try:
        # Overall counts (unique employees)
        conditions = ["1=1"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "e")
        where = " AND ".join(conditions)

        totals_q = text(
            f"SELECT "
            f"COUNT(DISTINCT e.c_bpartner_id) AS total, "
            f"COUNT(DISTINCT CASE WHEN e.isactive = 'Y' THEN e.c_bpartner_id END) AS activos, "
            f"COUNT(DISTINCT CASE WHEN e.isactive = 'N' THEN e.c_bpartner_id END) AS inactivos "
            f"FROM adempiere.hr_employee e "
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total": row[0] if row else 0,
            "activos": row[1] if row else 0,
            "inactivos": row[2] if row else 0,
        }

        # By organization (unique employees per org)
        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Organización') AS organizacion, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS total, "
            f"COUNT(DISTINCT CASE WHEN e.isactive = 'Y' THEN e.c_bpartner_id END) AS activos "
            f"FROM adempiere.hr_employee e "
            f"LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY total DESC"
        )
        by_org = [
            {"organizacion": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_org_q, params).fetchall()
        ]

        # By department (from hr_department)
        by_dept_q = text(
            f"SELECT COALESCE(d.name, 'Sin Departamento') AS departamento, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS total, "
            f"COUNT(DISTINCT CASE WHEN e.isactive = 'Y' THEN e.c_bpartner_id END) AS activos "
            f"FROM adempiere.hr_employee e "
            f"LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id "
            f"WHERE {where} "
            f"GROUP BY d.name ORDER BY total DESC LIMIT 20"
        )
        by_dept = [
            {"departamento": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_dept_q, params).fetchall()
        ]

        # By job/cargo (from hr_job)
        by_job_q = text(
            f"SELECT COALESCE(j.name, 'Sin Cargo') AS cargo, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS total, "
            f"COUNT(DISTINCT CASE WHEN e.isactive = 'Y' THEN e.c_bpartner_id END) AS activos "
            f"FROM adempiere.hr_employee e "
            f"LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id "
            f"WHERE {where} "
            f"GROUP BY j.name ORDER BY total DESC LIMIT 30"
        )
        by_job = [
            {"cargo": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_job_q, params).fetchall()
        ]

        return {
            "totales": totals,
            "por_organizacion": by_org,
            "por_departamento": by_dept,
            "por_cargo": by_job,
        }
    finally:
        db.close()


def build_employee_list(
    org_ids: list[int] | None = None,
    cargo_search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """List of unique active employees from iDempiere hr_employee + c_bpartner.

    Uses DISTINCT ON (bp.c_bpartner_id) to eliminate duplicate rows caused by
    hr_employee having multiple records per person (one per payroll period).
    Joins hr_department and hr_job for richer employee info.

    If cargo_search is provided, filters by job title using ILIKE.
    If date_from/date_to provided, filters by startdate (fecha de ingreso).
    """
    db = IdempiereSession()
    try:
        conditions = ["e.isactive = 'Y'"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "e")

        if cargo_search:
            # Split into words and require ALL words to appear (handles plural/singular)
            # e.g. "obreros integrales" → j.name ILIKE '%obrero%' AND j.name ILIKE '%integral%'
            words = cargo_search.strip().split()
            for i, word in enumerate(words):
                # Strip trailing 's'/'es' for basic singular matching
                stem = word.rstrip("s")
                if stem.endswith("e") and word.endswith("es") and len(stem) > 3:
                    stem = stem[:-1]  # "integrales" → "integral"
                key = f"cargo_w{i}"
                conditions.append(f"j.name ILIKE :{key}")
                params[key] = f"%{stem}%"

        if date_from:
            conditions.append("e.startdate >= :date_from")
            params["date_from"] = date_from
        if date_to:
            conditions.append("e.startdate <= :date_to")
            params["date_to"] = date_to

        where = " AND ".join(conditions)

        q = text(
            f"SELECT DISTINCT ON (bp.c_bpartner_id) "
            f"bp.name AS nombre, bp.value AS codigo, "
            f"COALESCE(o.name, '') AS organizacion, "
            f"COALESCE(d.name, '') AS departamento, "
            f"COALESCE(j.name, '') AS cargo, "
            f"e.startdate AS fecha_ingreso "
            f"FROM adempiere.hr_employee e "
            f"JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id "
            f"LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id "
            f"LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id "
            f"LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id "
            f"WHERE {where} "
            f"ORDER BY bp.c_bpartner_id, e.startdate DESC"
        )
        rows = db.execute(q, params).fetchall()

        # Sort by name for display after deduplication
        results = [
            {
                "nombre": r[0],
                "codigo": r[1],
                "organizacion": r[2],
                "departamento": r[3],
                "cargo": r[4],
                "fecha_ingreso": str(r[5]) if r[5] else "",
            }
            for r in rows
        ]
        results.sort(key=lambda x: x["nombre"])
        # When filtering by cargo, allow more results; otherwise cap at 100
        limit = 200 if cargo_search else 100
        return results[:limit]
    finally:
        db.close()


def _find_birthday_column(db) -> tuple[str, str] | None:
    """Auto-detect which table/column holds birthday data in iDempiere.

    Searches c_bpartner, lve_c_bpartner, and hr_employee for date columns
    whose name contains 'birth', 'nac', 'cumple', or 'fecha_nac'.
    Returns (table_alias_expr, column_expr) or None if not found.
    Caches the result for the process lifetime.
    """
    if hasattr(_find_birthday_column, "_cached"):
        return _find_birthday_column._cached

    candidates = [
        # (table, join_expr, column_patterns)
        ("c_bpartner", None, ["birthday", "birthdate", "fecha_nacimiento", "fechanacimiento"]),
        (
            "lve_c_bpartner",
            "LEFT JOIN adempiere.lve_c_bpartner lbp ON bp.c_bpartner_id = lbp.c_bpartner_id",
            ["birthday", "birthdate", "fecha_nacimiento", "fechanacimiento",
             "fecha_nac", "fechanac", "nacimiento"],
        ),
    ]

    for tbl, join_expr, patterns in candidates:
        q = text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'adempiere' AND table_name = :tbl "
            "AND data_type IN ('date', 'timestamp without time zone', "
            "'timestamp with time zone') "
            "ORDER BY column_name"
        )
        cols = [r[0] for r in db.execute(q, {"tbl": tbl}).fetchall()]
        for col in cols:
            col_lower = col.lower()
            if any(p in col_lower for p in patterns):
                if tbl == "c_bpartner":
                    result = (None, f"bp.{col}")
                else:
                    alias = "lbp"
                    result = (join_expr, f"{alias}.{col}")
                _find_birthday_column._cached = result
                return result

    _find_birthday_column._cached = None
    return None


def build_birthday_list(
    mes: int | None = None,
    org_ids: list[int] | None = None,
) -> list[dict]:
    """List employees whose birthday falls in the given month.

    Auto-detects the birthday column across c_bpartner and lve_c_bpartner.
    Returns empty list if no birthday column exists in the database.
    """
    db = IdempiereSession()
    try:
        bday_info = _find_birthday_column(db)
        if bday_info is None:
            return []

        extra_join, bday_col = bday_info

        conditions = ["e.isactive = 'Y'", f"{bday_col} IS NOT NULL"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "e")

        if mes:
            conditions.append(f"EXTRACT(MONTH FROM {bday_col}) = :mes")
            params["mes"] = mes

        where = " AND ".join(conditions)

        extra_join_clause = f"\n{extra_join} " if extra_join else ""

        q = text(
            f"SELECT DISTINCT ON (bp.c_bpartner_id) "
            f"bp.name AS nombre, "
            f"EXTRACT(DAY FROM {bday_col})::int AS dia, "
            f"EXTRACT(MONTH FROM {bday_col})::int AS mes, "
            f"COALESCE(d.name, '') AS departamento, "
            f"COALESCE(o.name, '') AS organizacion, "
            f"COALESCE(j.name, '') AS cargo "
            f"FROM adempiere.hr_employee e "
            f"JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id "
            f"{extra_join_clause}"
            f"LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id "
            f"LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id "
            f"LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id "
            f"WHERE {where} "
            f"ORDER BY bp.c_bpartner_id, e.startdate DESC"
        )
        rows = db.execute(q, params).fetchall()

        results = [
            {
                "nombre": r[0],
                "dia": r[1],
                "mes": r[2],
                "departamento": r[3],
                "organizacion": r[4],
                "cargo": r[5],
            }
            for r in rows
        ]
        # Sort by day of month for display
        results.sort(key=lambda x: x["dia"])
        return results
    finally:
        db.close()


def build_payroll_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Payroll summary from iDempiere hr_process + hr_movement."""
    db = IdempiereSession()
    try:
        conditions = [
            "hp.docstatus = 'CO'",
            "hp.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "hp")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "hp.dateacct")
        where = " AND ".join(conditions)

        # Process summary
        totals_q = text(
            f"SELECT COUNT(DISTINCT hp.hr_process_id) AS total_procesos, "
            f"COUNT(DISTINCT hm.hr_employee_id) AS empleados_procesados, "
            f"COALESCE(SUM(CASE WHEN hm.amount > 0 THEN hm.amount ELSE 0 END), 0) AS total_devengado, "
            f"COALESCE(SUM(CASE WHEN hm.amount < 0 THEN ABS(hm.amount) ELSE 0 END), 0) AS total_deducciones "
            f"FROM adempiere.hr_process hp "
            f"LEFT JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id "
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_procesos": row[0] if row else 0,
            "empleados_procesados": row[1] if row else 0,
            "total_devengado": float(row[2]) if row else 0.0,
            "total_deducciones": float(row[3]) if row else 0.0,
        }
        totals["neto_a_pagar"] = totals["total_devengado"] - totals["total_deducciones"]

        # By payroll type
        by_payroll_q = text(
            f"SELECT COALESCE(hpy.name, 'Sin tipo') AS nomina, "
            f"COUNT(DISTINCT hp.hr_process_id) AS procesos, "
            f"COALESCE(SUM(hm.amount), 0) AS total "
            f"FROM adempiere.hr_process hp "
            f"LEFT JOIN adempiere.hr_payroll hpy ON hp.hr_payroll_id = hpy.hr_payroll_id "
            f"LEFT JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id "
            f"WHERE {where} "
            f"GROUP BY hpy.name ORDER BY total DESC"
        )
        by_payroll = [
            {"nomina": r[0], "procesos": r[1], "total": float(r[2])}
            for r in db.execute(by_payroll_q, params).fetchall()
        ]

        # Top concepts
        by_concept_q = text(
            f"SELECT hc.name AS concepto, "
            f"COALESCE(SUM(hm.amount), 0) AS total, "
            f"COUNT(*) AS movimientos "
            f"FROM adempiere.hr_process hp "
            f"JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"WHERE {where} "
            f"GROUP BY hc.name ORDER BY ABS(SUM(hm.amount)) DESC LIMIT 20"
        )
        by_concept = [
            {"concepto": r[0], "total": float(r[1]), "movimientos": r[2]}
            for r in db.execute(by_concept_q, params).fetchall()
        ]

        return {
            "totales": totals,
            "por_tipo_nomina": by_payroll,
            "conceptos_principales": by_concept,
        }
    finally:
        db.close()


def build_attendance_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Attendance/absence indicators from hr_movement concepts.

    Looks for payroll concepts related to absences (inasistencia, falta,
    permiso, reposo, etc.) and summarises them by type and organisation.
    """
    db = IdempiereSession()
    try:
        conditions = [
            "hp.docstatus = 'CO'",
            "hp.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "hp")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "hp.dateacct")

        # Filter concepts related to absence / attendance
        absence_terms = [
            "%ausent%", "%ausencia%", "%inasist%", "%falta%",
            "%permiso%", "%reposo%", "%incapacidad%", "%licencia%",
        ]
        like_clauses = " OR ".join(
            f"LOWER(hc.name) LIKE :abs_{i}" for i in range(len(absence_terms))
        )
        conditions.append(f"({like_clauses})")
        for i, term in enumerate(absence_terms):
            params[f"abs_{i}"] = term

        where = " AND ".join(conditions)

        # Summary by concept
        # NOTE: hm.qty is always 0 for absence concepts in Santoni's iDempiere.
        # We use ABS(hm.amount) for monetary impact and COUNT(*) for occurrences.
        by_concept_q = text(
            f"SELECT hc.name AS concepto, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados_afectados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto_bs, "
            f"COUNT(*) AS registros "
            f"FROM adempiere.hr_process hp "
            f"JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"WHERE {where} "
            f"GROUP BY hc.name ORDER BY registros DESC LIMIT 20"
        )
        by_concept = [
            {
                "concepto": r[0],
                "empleados_afectados": r[1],
                "monto_bs": float(r[2]),
                "ocurrencias": r[3],
            }
            for r in db.execute(by_concept_q, params).fetchall()
        ]

        # Summary by org
        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados_afectados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto_bs, "
            f"COUNT(*) AS registros "
            f"FROM adempiere.hr_process hp "
            f"JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"LEFT JOIN adempiere.ad_org o ON hm.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY registros DESC"
        )
        by_org = [
            {
                "organizacion": r[0],
                "empleados_afectados": r[1],
                "monto_bs": float(r[2]),
                "ocurrencias": r[3],
            }
            for r in db.execute(by_org_q, params).fetchall()
        ]

        # Total active employees for rate calculation
        emp_conditions = ["1=1"]
        emp_params: dict = {}
        _add_org_filter(emp_conditions, emp_params, org_ids, "e")
        emp_where = " AND ".join(emp_conditions)
        emp_q = text(
            f"SELECT COUNT(DISTINCT e.c_bpartner_id) "
            f"FROM adempiere.hr_employee e "
            f"WHERE e.isactive = 'Y' AND {emp_where}"
        )
        emp_row = db.execute(emp_q, emp_params).fetchone()
        total_activos = emp_row[0] if emp_row else 0

        total_afectados = sum(c["empleados_afectados"] for c in by_concept)
        tasa = (total_afectados / total_activos * 100) if total_activos else 0

        total_ocurrencias = sum(c["ocurrencias"] for c in by_concept)
        totals = {
            "empleados_activos": total_activos,
            "empleados_con_ausencias": total_afectados,
            "total_ocurrencias": total_ocurrencias,
            "tasa_ausentismo_pct": round(tasa, 2),
            "conceptos_encontrados": len(by_concept),
            "nota_horas": "No se dispone de horas-hombre en el sistema de nómina. Los datos se expresan en ocurrencias y monto (Bs.).",
        }

        if not by_concept:
            totals["nota"] = (
                "No se encontraron conceptos de ausentismo en nómina para este período. "
                "Los conceptos buscados incluyen: inasistencia, falta, permiso, "
                "reposo, incapacidad, licencia."
            )

        return {
            "totales": totals,
            "por_concepto": by_concept,
            "por_organizacion": by_org,
        }
    finally:
        db.close()


def build_turnover_summary(
    anio: int | None = None,
    org_ids: list[int] | None = None,
) -> dict:
    """Employee turnover (rotation) from hr_employee enddate.

    Counts employees whose enddate falls within the given year as 'bajas'.
    Calculates turnover rate = bajas / total_activos * 100.
    """
    from datetime import datetime

    if not anio:
        anio = datetime.now().year

    db = IdempiereSession()
    try:
        # Bajas (employees with enddate in the given year)
        conditions = [
            "e.isactive = 'N'",
            "e.enddate >= :year_start",
            "e.enddate < :year_end",
        ]
        params: dict = {
            "year_start": f"{anio}-01-01",
            "year_end": f"{anio + 1}-01-01",
        }
        _add_org_filter(conditions, params, org_ids, "e")
        where = " AND ".join(conditions)

        # Bajas by org
        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS bajas "
            f"FROM adempiere.hr_employee e "
            f"LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY bajas DESC"
        )
        by_org = [
            {"organizacion": r[0], "bajas": r[1]}
            for r in db.execute(by_org_q, params).fetchall()
        ]
        total_bajas = sum(r["bajas"] for r in by_org)

        # Total active employees for rate
        emp_conditions = ["1=1"]
        emp_params: dict = {}
        _add_org_filter(emp_conditions, emp_params, org_ids, "e")
        emp_where = " AND ".join(emp_conditions)
        emp_q = text(
            f"SELECT COUNT(DISTINCT e.c_bpartner_id) "
            f"FROM adempiere.hr_employee e "
            f"WHERE e.isactive = 'Y' AND {emp_where}"
        )
        emp_row = db.execute(emp_q, emp_params).fetchone()
        total_activos = emp_row[0] if emp_row else 0

        tasa = (total_bajas / total_activos * 100) if total_activos else 0

        return {
            "anio": anio,
            "totales": {
                "empleados_activos": total_activos,
                "bajas": total_bajas,
                "tasa_rotacion_pct": round(tasa, 2),
            },
            "por_organizacion": by_org,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# PRODUCCION (Production)
# ---------------------------------------------------------------------------

def build_production_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Production/inventory movement summary from iDempiere m_inout.

    Santoni does not use the Manufacturing module (pp_order is empty).
    Instead, production activity is tracked via material movements:
    - V+ = Vendor Receipt (raw material incoming)
    - C- = Customer Shipment (finished product outgoing)
    - M+/M- = Internal inventory movements
    - P+/P- = Production receipts (rare)
    """
    db = IdempiereSession()
    try:
        conditions = ["io.isactive = 'Y'", "io.docstatus = 'CO'"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "io")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "io.movementdate")
        where = " AND ".join(conditions)

        # Totals by movement type
        totals_q = text(
            f"SELECT "
            f"SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones_mp, "
            f"SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos_pt, "
            f"SUM(CASE WHEN io.movementtype IN ('M+','M-') THEN 1 ELSE 0 END) AS movimientos_internos, "
            f"SUM(CASE WHEN io.movementtype IN ('P+','P-') THEN 1 ELSE 0 END) AS movimientos_produccion, "
            f"COUNT(*) AS total_movimientos "
            f"FROM adempiere.m_inout io WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "recepciones_materia_prima": row[0] if row else 0,
            "despachos_producto_terminado": row[1] if row else 0,
            "movimientos_internos": row[2] if row else 0,
            "movimientos_produccion": row[3] if row else 0,
            "total_movimientos": row[4] if row else 0,
        }

        # Top products by quantity moved
        by_product_q = text(
            f"SELECT p.name AS producto, "
            f"SUM(CASE WHEN io.movementtype = 'V+' THEN iol.movementqty ELSE 0 END) AS recibido, "
            f"SUM(CASE WHEN io.movementtype = 'C-' THEN iol.movementqty ELSE 0 END) AS despachado, "
            f"SUM(ABS(iol.movementqty)) AS total_movido "
            f"FROM adempiere.m_inout io "
            f"JOIN adempiere.m_inoutline iol ON io.m_inout_id = iol.m_inout_id "
            f"JOIN adempiere.m_product p ON iol.m_product_id = p.m_product_id "
            f"WHERE {where} "
            f"GROUP BY p.name ORDER BY total_movido DESC LIMIT 20"
        )
        by_product = [
            {
                "producto": r[0],
                "recibido": float(r[1]),
                "despachado": float(r[2]),
                "total_movido": float(r[3]),
            }
            for r in db.execute(by_product_q, params).fetchall()
        ]

        # By month
        by_month_q = text(
            f"SELECT EXTRACT(MONTH FROM io.movementdate)::int AS mes, "
            f"COUNT(*) AS movimientos, "
            f"SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones, "
            f"SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos "
            f"FROM adempiere.m_inout io WHERE {where} "
            f"GROUP BY EXTRACT(MONTH FROM io.movementdate) ORDER BY mes"
        )
        by_month = [
            {"mes": r[0], "movimientos": r[1], "recepciones": r[2], "despachos": r[3]}
            for r in db.execute(by_month_q, params).fetchall()
        ]

        # By organization
        by_org_q = text(
            f"SELECT org.name AS organizacion, "
            f"COUNT(*) AS movimientos, "
            f"SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones, "
            f"SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos "
            f"FROM adempiere.m_inout io "
            f"JOIN adempiere.ad_org org ON io.ad_org_id = org.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY org.name ORDER BY movimientos DESC"
        )
        by_org = [
            {"organizacion": r[0], "movimientos": r[1], "recepciones": r[2], "despachos": r[3]}
            for r in db.execute(by_org_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "mes": mes,
            "totales": totals,
            "por_producto": by_product,
            "por_mes": by_month,
            "por_organizacion": by_org,
        }
    finally:
        db.close()


def build_production_orders(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Recent material movement documents from iDempiere m_inout."""
    db = IdempiereSession()
    try:
        conditions = ["io.isactive = 'Y'", "io.docstatus = 'CO'"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "io")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "io.movementdate")
        where = " AND ".join(conditions)

        q = text(
            f"SELECT io.documentno AS documento, "
            f"io.movementdate::date AS fecha, "
            f"CASE io.movementtype "
            f"  WHEN 'V+' THEN 'Recepción MP' "
            f"  WHEN 'C-' THEN 'Despacho PT' "
            f"  WHEN 'M+' THEN 'Mov. Entrada' "
            f"  WHEN 'M-' THEN 'Mov. Salida' "
            f"  WHEN 'P+' THEN 'Producción +' "
            f"  WHEN 'P-' THEN 'Producción -' "
            f"  ELSE io.movementtype END AS tipo, "
            f"org.name AS organizacion, "
            f"COALESCE(bp.name, '') AS socio_negocio "
            f"FROM adempiere.m_inout io "
            f"JOIN adempiere.ad_org org ON io.ad_org_id = org.ad_org_id "
            f"LEFT JOIN adempiere.c_bpartner bp ON io.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"ORDER BY io.movementdate DESC LIMIT 50"
        )
        return [
            {
                "documento": r[0],
                "fecha": str(r[1]) if r[1] else "",
                "tipo": r[2],
                "organizacion": r[3] or "",
                "socio_negocio": r[4] or "",
            }
            for r in db.execute(q, params).fetchall()
        ]
    finally:
        db.close()


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
) -> dict:
    """Producer purchases from iDempiere."""
    db = IdempiereSession()
    try:
        conditions = [
            "o.issotrx = 'N'",
            "o.docstatus = 'CO'",
            "o.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "o")
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

        # By product
        by_product_q = text(
            f"SELECT p.name AS producto, "
            f"COUNT(DISTINCT o.c_order_id) AS guias, "
            f"COALESCE(SUM(ol.qtyordered), 0) AS peso_neto_kg, "
            f"COALESCE(SUM(ol.linenetamt), 0) AS monto_total, "
            f"0.0 AS humedad_promedio, "
            f"0.0 AS impureza_promedio "
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
                "humedad_promedio": float(r[4]),
                "impureza_promedio": float(r[5]),
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
    producto: str | None = None, org_ids: list[int] | None = None,
) -> list[dict]:
    """Pending purchase invoices (not fully paid) from iDempiere.

    Uses c_invoice (ispaid='N') instead of c_order, since c_order
    does not have a totalpaid column in Santoni's iDempiere.
    """
    db = IdempiereSession()
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus = 'CO'",
            "i.ispaid = 'N'",
            "i.isactive = 'Y'",
            "i.dateinvoiced >= (CURRENT_DATE - INTERVAL '2 years')",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")

        if producto:
            conditions.append("LOWER(p.name) LIKE :producto")
            params["producto"] = f"%{producto.lower()}%"

        where = " AND ".join(conditions)

        q = text(
            f"SELECT bp.name AS productor, i.documentno AS documento, "
            f"i.dateinvoiced::date AS fecha, "
            f"i.grandtotal AS monto_total "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"{'JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id ' if producto else ''}"
            f"{'JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id ' if producto else ''}"
            f"WHERE {where} "
            f"ORDER BY i.grandtotal DESC LIMIT 30"
        )
        return [
            {
                "productor": r[0],
                "documento": r[1],
                "fecha": str(r[2]) if r[2] else "",
                "monto_total": float(r[3]) if r[3] else 0.0,
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
    db = IdempiereSession()
    try:
        conditions = [
            "o.issotrx = 'N'",
            "o.docstatus = 'CO'",
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
# COMPRAS INSUMOS (Supply Purchases)
# ---------------------------------------------------------------------------

def build_supply_purchases(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Supply purchases from iDempiere: purchase invoices (issotrx='N')."""
    db = IdempiereSession()
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus = 'CO'",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")

        where = " AND ".join(conditions)

        # Totals
        totals_q = text(
            f"SELECT COUNT(DISTINCT i.c_invoice_id) AS total_ordenes, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_monto "
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
            f"COALESCE(SUM(i.grandtotal), 0) AS total "
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
            f"COALESCE(SUM(i.grandtotal), 0) AS total "
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

        return {
            "anio": anio,
            "mes": mes,
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
) -> list[dict]:
    """Purchase history for a specific product from iDempiere.

    Searches by product code (value) or name. Returns recent purchase invoices
    for that product with supplier, quantity, unit price, and total.
    """
    db = IdempiereSession()
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus = 'CO'",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
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


# ---------------------------------------------------------------------------
# CONTABILIDAD (Accounting)
# ---------------------------------------------------------------------------

def build_accounting_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Accounting summary from iDempiere fact_acct (posted accounting facts)."""
    db = IdempiereSession()
    try:
        conditions = [
            "fa.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "fa")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "fa.dateacct")

        where = " AND ".join(conditions)

        # Totals
        totals_q = text(
            f"SELECT COUNT(*) AS total_asientos, "
            f"COALESCE(SUM(fa.amtacctdr), 0) AS total_debe, "
            f"COALESCE(SUM(fa.amtacctcr), 0) AS total_haber "
            f"FROM adempiere.fact_acct fa WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_asientos": row[0] if row else 0,
            "total_debe": float(row[1]) if row else 0.0,
            "total_haber": float(row[2]) if row else 0.0,
        }

        # By account type (using element value)
        by_account_q = text(
            f"SELECT CASE "
            f"  WHEN ev.accounttype = 'A' THEN 'Activo' "
            f"  WHEN ev.accounttype = 'L' THEN 'Pasivo' "
            f"  WHEN ev.accounttype = 'O' THEN 'Patrimonio' "
            f"  WHEN ev.accounttype = 'R' THEN 'Ingreso' "
            f"  WHEN ev.accounttype = 'E' THEN 'Gasto' "
            f"  WHEN ev.accounttype = 'M' THEN 'Memorándum' "
            f"  ELSE ev.accounttype END AS tipo_cuenta, "
            f"COALESCE(SUM(fa.amtacctdr), 0) AS debe, "
            f"COALESCE(SUM(fa.amtacctcr), 0) AS haber, "
            f"COALESCE(SUM(fa.amtacctdr), 0) - COALESCE(SUM(fa.amtacctcr), 0) AS saldo "
            f"FROM adempiere.fact_acct fa "
            f"JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id "
            f"WHERE {where} "
            f"GROUP BY ev.accounttype ORDER BY ev.accounttype"
        )
        by_account_type = [
            {"tipo_cuenta": r[0], "debe": float(r[1]), "haber": float(r[2]), "saldo": float(r[3])}
            for r in db.execute(by_account_q, params).fetchall()
        ]

        # Balance: Assets, Liabilities, Equity
        # Use correct sign convention: A=debit-normal, L/O=credit-normal
        balance_conds = [
            "ev.accounttype IN ('A', 'L', 'O')",
            "fa.isactive = 'Y'",
        ]
        balance_params: dict = {}
        _add_org_filter(balance_conds, balance_params, org_ids, "fa")
        if anio:
            balance_conds.append("EXTRACT(YEAR FROM fa.dateacct) <= :anio")
            balance_params["anio"] = anio

        balance_where = " AND ".join(balance_conds)
        balance_q = text(
            f"SELECT CASE "
            f"  WHEN ev.accounttype = 'A' THEN 'Activo' "
            f"  WHEN ev.accounttype = 'L' THEN 'Pasivo' "
            f"  WHEN ev.accounttype = 'O' THEN 'Patrimonio' "
            f"  END AS tipo, "
            f"CASE "
            f"  WHEN ev.accounttype = 'A' THEN COALESCE(SUM(fa.amtacctdr - fa.amtacctcr), 0) "
            f"  ELSE COALESCE(SUM(fa.amtacctcr - fa.amtacctdr), 0) "
            f"END AS saldo "
            f"FROM adempiere.fact_acct fa "
            f"JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id "
            f"WHERE {balance_where} "
            f"GROUP BY ev.accounttype ORDER BY ev.accounttype"
        )
        balance = [
            {"tipo": r[0], "saldo": float(r[1])}
            for r in db.execute(balance_q, balance_params).fetchall()
        ]

        # Top accounts by movement (current period)
        top_accounts_q = text(
            f"SELECT ev.value AS codigo, ev.name AS cuenta, "
            f"COALESCE(SUM(fa.amtacctdr), 0) AS debe, "
            f"COALESCE(SUM(fa.amtacctcr), 0) AS haber "
            f"FROM adempiere.fact_acct fa "
            f"JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id "
            f"WHERE {where} "
            f"GROUP BY ev.value, ev.name "
            f"ORDER BY (COALESCE(SUM(fa.amtacctdr), 0) + COALESCE(SUM(fa.amtacctcr), 0)) DESC "
            f"LIMIT 20"
        )
        top_accounts = [
            {"codigo": r[0], "cuenta": r[1], "debe": float(r[2]), "haber": float(r[3])}
            for r in db.execute(top_accounts_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "mes": mes,
            "totales": totals,
            "por_tipo_cuenta": by_account_type,
            "balance": balance,
            "cuentas_con_mayor_movimiento": top_accounts,
        }
    finally:
        db.close()


def build_account_detail(
    account_code: str,
    date_from: str | None = None,
    date_to: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    currency_ids: list[int] | None = None,
) -> dict:
    """Query detail for a specific account code from fact_acct.

    Parameters:
        account_code: Account code like '2.01.01.10'
        date_from: Start date 'YYYY-MM-DD' (overrides mes/anio if provided)
        date_to: End date 'YYYY-MM-DD' (overrides mes/anio if provided)
        mes: Month number (used if date_from/to not provided)
        anio: Year (used if date_from/to not provided)
        org_ids: List of allowed organization IDs
        currency_ids: List of iDempiere c_currency_id values. Filters fact_acct entries.

    Returns dict with account info, period totals, opening/closing balance.

    IMPORTANT - Balance sign convention:
    - Debit-normal accounts (A=Activo, E=Gasto): saldo = debe - haber
    - Credit-normal accounts (L=Pasivo, O=Patrimonio, R=Ingreso): saldo = haber - debe
    """
    db = IdempiereSession()
    try:
        # 1. Find the account by code
        acct_q = text(
            "SELECT ev.c_elementvalue_id, ev.value, ev.name, ev.accounttype "
            "FROM adempiere.c_elementvalue ev "
            "WHERE ev.value = :code AND ev.isactive = 'Y' "
            "LIMIT 1"
        )
        acct_row = db.execute(acct_q, {"code": account_code}).fetchone()
        if not acct_row:
            return {
                "error": f"Cuenta '{account_code}' no encontrada en el plan de cuentas",
                "cuenta_codigo": account_code,
            }

        acct_id = acct_row[0]
        acct_name = acct_row[2]
        acct_type = acct_row[3]  # A=Activo, L=Pasivo, O=Patrimonio, R=Ingreso, E=Gasto

        # Determine balance sign: credit-normal accounts flip the sign
        # L (Pasivo), O (Patrimonio), R (Ingreso) → saldo = haber - debe
        # A (Activo), E (Gasto) → saldo = debe - haber
        is_credit_normal = acct_type in ("L", "O", "R")

        # 2. Build date conditions
        period_conditions = ["fa.isactive = 'Y'", "fa.account_id = :acct_id"]
        period_params: dict = {"acct_id": acct_id}
        _add_org_filter(period_conditions, period_params, org_ids, "fa")
        _add_currency_filter(period_conditions, period_params, currency_ids, "fa")

        if date_from and date_to:
            period_conditions.append("fa.dateacct >= :date_from")
            period_conditions.append("fa.dateacct <= :date_to")
            period_params["date_from"] = date_from
            period_params["date_to"] = date_to
            period_label = f"{date_from} al {date_to}"
        elif mes and anio:
            period_conditions.append("EXTRACT(YEAR FROM fa.dateacct) = :anio")
            period_conditions.append("EXTRACT(MONTH FROM fa.dateacct) = :mes")
            period_params["anio"] = anio
            period_params["mes"] = mes
            period_label = f"{mes:02d}/{anio}"
        elif anio:
            period_conditions.append("EXTRACT(YEAR FROM fa.dateacct) = :anio")
            period_params["anio"] = anio
            period_label = f"Año {anio}"
        else:
            period_label = "Todos los períodos"

        period_where = " AND ".join(period_conditions)

        # 3. Period totals (debit/credit in the period)
        totals_q = text(
            f"SELECT COUNT(*) AS movimientos, "
            f"COALESCE(SUM(fa.amtacctdr), 0) AS total_debe, "
            f"COALESCE(SUM(fa.amtacctcr), 0) AS total_haber "
            f"FROM adempiere.fact_acct fa WHERE {period_where}"
        )
        row = db.execute(totals_q, period_params).fetchone()
        movimientos = row[0] if row else 0
        total_debe = float(row[1]) if row else 0.0
        total_haber = float(row[2]) if row else 0.0

        # 4. Opening balance (all movements BEFORE the period start)
        # Use the correct sign convention based on account type
        saldo_sql_expr = (
            "COALESCE(SUM(fa.amtacctcr - fa.amtacctdr), 0)"
            if is_credit_normal
            else "COALESCE(SUM(fa.amtacctdr - fa.amtacctcr), 0)"
        )

        saldo_inicial = 0.0
        if date_from:
            opening_conds = [
                "fa.isactive = 'Y'",
                "fa.account_id = :acct_id",
                "fa.dateacct < :date_from",
            ]
            opening_params: dict = {"acct_id": acct_id, "date_from": date_from}
            _add_org_filter(opening_conds, opening_params, org_ids, "fa")
            _add_currency_filter(opening_conds, opening_params, currency_ids, "fa")
            opening_q = text(
                f"SELECT {saldo_sql_expr} "
                f"FROM adempiere.fact_acct fa "
                f"WHERE {' AND '.join(opening_conds)}"
            )
            r = db.execute(opening_q, opening_params).fetchone()
            saldo_inicial = float(r[0]) if r else 0.0
        elif mes and anio:
            opening_conds = [
                "fa.isactive = 'Y'",
                "fa.account_id = :acct_id",
                "fa.dateacct < :opening_date",
            ]
            opening_params2: dict = {"acct_id": acct_id, "opening_date": f"{anio}-{mes:02d}-01"}
            _add_org_filter(opening_conds, opening_params2, org_ids, "fa")
            _add_currency_filter(opening_conds, opening_params2, currency_ids, "fa")
            opening_q = text(
                f"SELECT {saldo_sql_expr} "
                f"FROM adempiere.fact_acct fa "
                f"WHERE {' AND '.join(opening_conds)}"
            )
            r = db.execute(opening_q, opening_params2).fetchone()
            saldo_inicial = float(r[0]) if r else 0.0

        # Closing balance: apply period movements with correct sign
        if is_credit_normal:
            saldo_final = saldo_inicial + total_haber - total_debe
        else:
            saldo_final = saldo_inicial + total_debe - total_haber

        # 5. Daily breakdown with running balance
        daily_q = text(
            f"SELECT fa.dateacct::date AS fecha, "
            f"COALESCE(SUM(fa.amtacctdr), 0) AS debe, "
            f"COALESCE(SUM(fa.amtacctcr), 0) AS haber, "
            f"COUNT(*) AS asientos "
            f"FROM adempiere.fact_acct fa WHERE {period_where} "
            f"GROUP BY fa.dateacct::date ORDER BY fa.dateacct::date "
            f"LIMIT 31"
        )
        daily_rows = db.execute(daily_q, period_params).fetchall()
        daily = []
        running_balance = saldo_inicial
        for r in daily_rows:
            debe_dia = float(r[1])
            haber_dia = float(r[2])
            if is_credit_normal:
                running_balance += haber_dia - debe_dia
            else:
                running_balance += debe_dia - haber_dia
            daily.append({
                "fecha": str(r[0]),
                "debe": debe_dia,
                "haber": haber_dia,
                "asientos": r[3],
                "saldo": round(running_balance, 2),
            })

        # 6. Currency info
        currency_name = "VES"
        if currency_ids:
            # Show label based on the first currency ID
            curr_q = text(
                "SELECT c.iso_code FROM adempiere.c_currency c "
                "WHERE c.c_currency_id = :cid"
            )
            curr_row = db.execute(curr_q, {"cid": currency_ids[0]}).fetchone()
            if curr_row:
                currency_name = curr_row[0]
        else:
            curr_q = text(
                "SELECT DISTINCT c.iso_code FROM adempiere.fact_acct fa "
                "JOIN adempiere.c_currency c ON fa.c_currency_id = c.c_currency_id "
                "WHERE fa.account_id = :acct_id AND fa.isactive = 'Y' LIMIT 3"
            )
            curr_rows = db.execute(curr_q, {"acct_id": acct_id}).fetchall()
            if curr_rows:
                currency_name = ", ".join(r[0] for r in curr_rows)

        acct_type_labels = {
            "A": "Activo", "L": "Pasivo", "O": "Patrimonio",
            "R": "Ingreso", "E": "Gasto", "M": "Memorándum",
        }
        naturaleza = "Crédito" if is_credit_normal else "Débito"

        return {
            "cuenta_codigo": account_code,
            "cuenta_nombre": acct_name,
            "tipo_cuenta": acct_type_labels.get(acct_type, acct_type),
            "naturaleza": naturaleza,
            "periodo": period_label,
            "moneda": currency_name,
            "movimientos": movimientos,
            "total_debe": total_debe,
            "total_haber": total_haber,
            "saldo_inicial": round(saldo_inicial, 2),
            "saldo_final": round(saldo_final, 2),
            "detalle_diario": daily,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# INVENTARIO (Inventory / Stock)
# ---------------------------------------------------------------------------

def build_inventory_stock(
    org_ids: list[int] | None = None,
    product_search: str | None = None,
    category_search: str | None = None,
    warehouse_search: str | None = None,
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

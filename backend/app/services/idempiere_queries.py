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
        _add_salesrep_filter(conditions, params, salesrep_id, "i")

        if anio:
            conditions.append("EXTRACT(YEAR FROM i.dateinvoiced) = :anio")
            params["anio"] = anio

        if mes:
            conditions.append("EXTRACT(MONTH FROM i.dateinvoiced) = :mes")
            params["mes"] = mes

        # TODO: zona and vendedor filters need validation after iDempiere exploration
        # Santoni may use c_salesregion for zones and ad_user/c_bpartner for salesreps
        if vendedor:
            conditions.append("COALESCE(sr.name, '') ILIKE :vendedor")
            params["vendedor"] = f"%{vendedor}%"
        if zona:
            conditions.append("COALESCE(sreg.name, '') ILIKE :zona")
            params["zona"] = f"%{zona}%"

        where = " AND ".join(conditions)

        # Totals
        totals_q = text(
            f"SELECT COUNT(*) AS total_facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_facturado, "
            f"COALESCE(SUM(i.totallines), 0) AS total_neto, "
            f"COALESCE(SUM(i.grandtotal - i.totallines), 0) AS total_iva "
            f"FROM adempiere.c_invoice i "
            f"LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id "
            f"LEFT JOIN adempiere.c_bpartner_location bpl ON i.c_bpartner_id = bpl.c_bpartner_id AND bpl.isactive = 'Y' "
            f"LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id "
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
            f"SELECT COALESCE(sreg.name, 'Sin Zona') AS zona, COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id "
            f"LEFT JOIN adempiere.c_bpartner_location bpl ON i.c_bpartner_id = bpl.c_bpartner_id AND bpl.isactive = 'Y' "
            f"LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id "
            f"WHERE {where} "
            f"GROUP BY sreg.name ORDER BY total DESC"
        )
        by_zone = [
            {"zona": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_zone_q, params).fetchall()
        ]

        # By sales rep (vendedor)
        by_vendor_q = text(
            f"SELECT COALESCE(sr.name, 'Sin Vendedor') AS vendedor, COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY sr.name ORDER BY total DESC"
        )
        by_vendor = [
            {"vendedor": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_vendor_q, params).fetchall()
        ]

        # By month
        by_month_q = text(
            f"SELECT EXTRACT(MONTH FROM i.dateinvoiced)::int AS mes, COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id "
            f"LEFT JOIN adempiere.c_bpartner_location bpl ON i.c_bpartner_id = bpl.c_bpartner_id AND bpl.isactive = 'Y' "
            f"LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id "
            f"WHERE {where} "
            f"GROUP BY EXTRACT(MONTH FROM i.dateinvoiced) ORDER BY mes"
        )
        by_month = [
            {"mes": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_month_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "filtros": {"zona": zona, "vendedor": vendedor, "mes": mes},
            "totales": totals,
            "por_zona": by_zone,
            "por_vendedor": by_vendor,
            "por_mes": by_month,
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
        # Payments don't have salesrep_id directly; filter via linked invoice
        if salesrep_id:
            conditions.append(
                "EXISTS (SELECT 1 FROM adempiere.c_allocationline al "
                "JOIN adempiere.c_invoice inv ON al.c_invoice_id = inv.c_invoice_id "
                "WHERE al.c_payment_id = p.c_payment_id AND inv.salesrep_id = :salesrep_id)"
            )
            params["salesrep_id"] = salesrep_id

        if anio:
            conditions.append("EXTRACT(YEAR FROM p.datetrx) = :anio")
            params["anio"] = anio

        if mes:
            conditions.append("EXTRACT(MONTH FROM p.datetrx) = :mes")
            params["mes"] = mes

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
    anio: int | None = None,
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
) -> list[dict]:
    """Top clients by invoiced amount from iDempiere."""
    db = IdempiereSession()
    try:
        conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus = 'CO'",
            "i.isactive = 'Y'",
        ]
        params: dict = {"limit": limit}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_salesrep_filter(conditions, params, salesrep_id, "i")

        if anio:
            conditions.append("EXTRACT(YEAR FROM i.dateinvoiced) = :anio")
            params["anio"] = anio

        where = " AND ".join(conditions)

        q = text(
            f"SELECT bp.value AS codigo, bp.name AS nombre, "
            f"COALESCE(sreg.name, 'Sin Zona') AS zona, "
            f"COALESCE(sr.name, 'Sin Vendedor') AS vendedor, "
            f"'' AS tipologia, "
            f"COUNT(i.c_invoice_id) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_facturado "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id "
            f"LEFT JOIN adempiere.c_bpartner_location bpl ON bp.c_bpartner_id = bpl.c_bpartner_id AND bpl.isactive = 'Y' "
            f"LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id "
            f"WHERE {where} "
            f"GROUP BY bp.value, bp.name, sreg.name, sr.name "
            f"ORDER BY total_facturado DESC "
            f"LIMIT :limit"
        )
        rows = db.execute(q, params).fetchall()
        return [
            {
                "codigo": r[0],
                "nombre": r[1],
                "zona": r[2],
                "vendedor": r[3],
                "tipologia": r[4],
                "facturas": r[5],
                "total_facturado": float(r[6]),
            }
            for r in rows
        ]
    finally:
        db.close()


def build_overdue_receivables(
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
) -> list[dict]:
    """Overdue accounts receivable from iDempiere (unpaid sales invoices)."""
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
            "SELECT i.documentno AS numero_factura, bp.name AS cliente, "
            "COALESCE(sr.name, '') AS vendedor, "
            "COALESCE(sreg.name, '') AS zona, "
            "i.grandtotal AS monto_total, i.dateinvoiced AS fecha, "
            "COALESCE(pterm.netdays, 30) AS dias_credito, "
            "CURRENT_DATE - (i.dateinvoiced + COALESCE(pterm.netdays, 30)) AS dias_vencido "
            "FROM adempiere.c_invoice i "
            "JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            "LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id "
            "LEFT JOIN adempiere.c_bpartner_location bpl ON bp.c_bpartner_id = bpl.c_bpartner_id AND bpl.isactive = 'Y' "
            "LEFT JOIN adempiere.c_salesregion sreg ON bpl.c_salesregion_id = sreg.c_salesregion_id "
            "LEFT JOIN adempiere.c_paymentterm pterm ON i.c_paymentterm_id = pterm.c_paymentterm_id "
            "WHERE i.issotrx = 'Y' AND i.docstatus = 'CO' AND i.ispaid = 'N' "
            "AND i.isactive = 'Y' "
            f"{org_clause}"
            f"{salesrep_clause}"
            "AND (i.dateinvoiced + COALESCE(pterm.netdays, 30)) < CURRENT_DATE "
            "ORDER BY dias_vencido DESC "
            "LIMIT 50"
        )
        rows = db.execute(q, org_params).fetchall()
        return [
            {
                "numero_factura": r[0],
                "cliente": r[1],
                "vendedor": r[2],
                "zona": r[3],
                "monto_total": float(r[4]),
                "fecha": r[5].isoformat() if r[5] else None,
                "fecha_vencimiento": None,  # Calculated from dateinvoiced + netdays
                "dias_vencido": r[7],
            }
            for r in rows
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# FINANZAS (Finance)
# ---------------------------------------------------------------------------

def build_financial_summary(mes: int | None = None, anio: int | None = None, org_ids: list[int] | None = None) -> dict:
    """Financial summary from iDempiere: bank balances, receivables, payables."""
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
        if anio:
            ar_conditions.append("EXTRACT(YEAR FROM i.dateinvoiced) = :anio")
            ar_params["anio"] = anio
        if mes:
            ar_conditions.append("EXTRACT(MONTH FROM i.dateinvoiced) = :mes")
            ar_params["mes"] = mes

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
            "(i.dateinvoiced + COALESCE(pt.netdays, 30)) < CURRENT_DATE",
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
        if mes:
            ap_conditions.append("EXTRACT(MONTH FROM i.dateinvoiced) = :mes")
            ap_params["mes"] = mes

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
            "(i.dateinvoiced + COALESCE(pt.netdays, 30)) < CURRENT_DATE",
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
    """Employee summary from iDempiere c_bpartner (isemployee='Y').
    NOTE: Full HR module (hr_*) availability needs to be verified."""
    db = IdempiereSession()
    try:
        # Overall counts
        emp_conditions = ["bp.isemployee = 'Y'"]
        emp_params: dict = {}
        _add_org_filter(emp_conditions, emp_params, org_ids, "bp")
        emp_where = " AND ".join(emp_conditions)
        totals_q = text(
            f"SELECT COUNT(*) AS total, "
            f"SUM(CASE WHEN bp.isactive = 'Y' THEN 1 ELSE 0 END) AS activos, "
            f"SUM(CASE WHEN bp.isactive = 'N' THEN 1 ELSE 0 END) AS inactivos "
            f"FROM adempiere.c_bpartner bp WHERE {emp_where}"
        )
        row = db.execute(totals_q, emp_params).fetchone()
        totals = {
            "total": row[0] if row else 0,
            "activos": row[1] if row else 0,
            "inactivos": row[2] if row else 0,
        }

        # By department (using c_bpartner groups or org)
        by_dept_q = text(
            f"SELECT COALESCE(o.name, 'Sin Departamento') AS departamento, "
            f"COUNT(*) AS total, "
            f"SUM(CASE WHEN bp.isactive = 'Y' THEN 1 ELSE 0 END) AS activos "
            f"FROM adempiere.c_bpartner bp "
            f"LEFT JOIN adempiere.ad_org o ON bp.ad_org_id = o.ad_org_id "
            f"WHERE {emp_where} "
            f"GROUP BY o.name ORDER BY total DESC"
        )
        by_dept = [
            {"departamento": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_dept_q, emp_params).fetchall()
        ]

        return {
            "totales": totals,
            "por_departamento": by_dept,
            "por_ubicacion": [],  # TODO: Map after iDempiere exploration
            "por_turno": [],  # TODO: Map after iDempiere exploration
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# PRODUCCION (Production)
# ---------------------------------------------------------------------------

def build_production_summary(mes: int | None = None, anio: int | None = None, org_ids: list[int] | None = None) -> dict:
    """Production summary from iDempiere m_production / pp_order."""
    db = IdempiereSession()
    try:
        conditions = ["mp.isactive = 'Y'"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "mp")

        if anio:
            conditions.append("EXTRACT(YEAR FROM mp.movementdate) = :anio")
            params["anio"] = anio

        if mes:
            conditions.append("EXTRACT(MONTH FROM mp.movementdate) = :mes")
            params["mes"] = mes

        where = " AND ".join(conditions)

        # Check if m_production table has data
        # TODO: Verify if Santoni uses m_production or pp_order for production tracking
        totals_q = text(
            f"SELECT COALESCE(SUM(ABS(pl.movementqty)), 0) AS total_producido, "
            f"COUNT(DISTINCT mp.m_production_id) AS total_ordenes "
            f"FROM adempiere.m_production mp "
            f"JOIN adempiere.m_productionline pl ON mp.m_production_id = pl.m_production_id "
            f"WHERE {where} AND mp.isactive = 'Y'"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_producido_kg": float(row[0]) if row else 0.0,
            "total_desperdicio_kg": 0.0,  # TODO: Map waste tracking after exploration
            "porcentaje_desperdicio": 0.0,
            "total_horas_operacion": 0.0,
            "total_horas_parada": 0.0,
        }

        # By product
        by_product_q = text(
            f"SELECT p.name AS producto, "
            f"COALESCE(SUM(ABS(pl.movementqty)), 0) AS producido "
            f"FROM adempiere.m_production mp "
            f"JOIN adempiere.m_productionline pl ON mp.m_production_id = pl.m_production_id "
            f"JOIN adempiere.m_product p ON pl.m_product_id = p.m_product_id "
            f"WHERE {where} AND mp.isactive = 'Y' AND pl.movementqty > 0 "
            f"GROUP BY p.name ORDER BY producido DESC"
        )
        by_product = [
            {"producto": r[0], "producido_kg": float(r[1])}
            for r in db.execute(by_product_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "mes": mes,
            "totales": totals,
            "por_planta": [],  # TODO: Map plant info after iDempiere exploration
            "por_producto": by_product,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# COMPRAS PRODUCTORES (Producer Purchases)
# ---------------------------------------------------------------------------

def build_producer_purchases(
    producto: str | None = None, mes: int | None = None, anio: int | None = None, org_ids: list[int] | None = None,
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

        if anio:
            conditions.append("EXTRACT(YEAR FROM o.dateordered) = :anio")
            params["anio"] = anio

        if mes:
            conditions.append("EXTRACT(MONTH FROM o.dateordered) = :mes")
            params["mes"] = mes

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
    """Pending purchase orders (not fully paid) from iDempiere."""
    db = IdempiereSession()
    try:
        conditions = [
            "o.issotrx = 'N'",
            "o.docstatus = 'CO'",
            "o.isactive = 'Y'",
            "o.grandtotal > o.totalpaid",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "o")

        if producto:
            conditions.append("LOWER(p.name) LIKE :producto")
            params["producto"] = f"%{producto.lower()}%"

        where = " AND ".join(conditions)

        q = text(
            f"SELECT bp.name AS productor, o.documentno AS documento, "
            f"o.dateordered::date AS fecha, "
            f"o.grandtotal AS monto_total, "
            f"COALESCE(o.totalpaid, 0) AS pagado, "
            f"(o.grandtotal - COALESCE(o.totalpaid, 0)) AS monto_pendiente "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
            f"{'JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id ' if producto else ''}"
            f"{'JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id ' if producto else ''}"
            f"WHERE {where} "
            f"ORDER BY monto_pendiente DESC LIMIT 30"
        )
        return [
            {
                "productor": r[0],
                "documento": r[1],
                "fecha": str(r[2]) if r[2] else "",
                "monto_total": float(r[3]) if r[3] else 0.0,
                "pagado": float(r[4]) if r[4] else 0.0,
                "monto_pendiente": float(r[5]) if r[5] else 0.0,
            }
            for r in db.execute(q, params).fetchall()
        ]
    finally:
        db.close()


def build_producer_price_analysis(
    anio: int | None = None, org_ids: list[int] | None = None,
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

        if anio:
            conditions.append("EXTRACT(YEAR FROM o.dateordered) = :anio")
            params["anio"] = anio

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

def build_supply_purchases(mes: int | None = None, anio: int | None = None, org_ids: list[int] | None = None) -> dict:
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

        if anio:
            conditions.append("EXTRACT(YEAR FROM i.dateinvoiced) = :anio")
            params["anio"] = anio

        if mes:
            conditions.append("EXTRACT(MONTH FROM i.dateinvoiced) = :mes")
            params["mes"] = mes

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
            f"SELECT p.name AS producto, "
            f"COALESCE(SUM(il.linenetamt), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id "
            f"JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id "
            f"WHERE {where} "
            f"GROUP BY p.name ORDER BY total DESC LIMIT 20"
        )
        by_product = [
            {"producto": r[0], "total": float(r[1])}
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


# ---------------------------------------------------------------------------
# CONTABILIDAD (Accounting)
# ---------------------------------------------------------------------------

def build_accounting_summary(mes: int | None = None, anio: int | None = None, org_ids: list[int] | None = None) -> dict:
    """Accounting summary from iDempiere fact_acct (posted accounting facts)."""
    db = IdempiereSession()
    try:
        conditions = [
            "fa.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "fa")

        if anio:
            conditions.append("EXTRACT(YEAR FROM fa.dateacct) = :anio")
            params["anio"] = anio

        if mes:
            conditions.append("EXTRACT(MONTH FROM fa.dateacct) = :mes")
            params["mes"] = mes

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
            f"COALESCE(SUM(fa.amtacctdr - fa.amtacctcr), 0) AS saldo "
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
) -> dict:
    """Query detail for a specific account code from fact_acct.

    Parameters:
        account_code: Account code like '2.01.01.10'
        date_from: Start date 'YYYY-MM-DD' (overrides mes/anio if provided)
        date_to: End date 'YYYY-MM-DD' (overrides mes/anio if provided)
        mes: Month number (used if date_from/to not provided)
        anio: Year (used if date_from/to not provided)
        org_ids: List of allowed organization IDs

    Returns dict with account info, period totals, opening/closing balance.
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
        acct_type = acct_row[3]

        # 2. Build date conditions
        period_conditions = ["fa.isactive = 'Y'", "fa.account_id = :acct_id"]
        period_params: dict = {"acct_id": acct_id}
        _add_org_filter(period_conditions, period_params, org_ids, "fa")

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
        saldo_inicial = 0.0
        if date_from:
            opening_conds = [
                "fa.isactive = 'Y'",
                "fa.account_id = :acct_id",
                "fa.dateacct < :date_from",
            ]
            opening_params: dict = {"acct_id": acct_id, "date_from": date_from}
            _add_org_filter(opening_conds, opening_params, org_ids, "fa")
            opening_q = text(
                f"SELECT COALESCE(SUM(fa.amtacctdr - fa.amtacctcr), 0) "
                f"FROM adempiere.fact_acct fa "
                f"WHERE {' AND '.join(opening_conds)}"
            )
            r = db.execute(opening_q, opening_params).fetchone()
            saldo_inicial = float(r[0]) if r else 0.0
        elif mes and anio:
            opening_conds = [
                "fa.isactive = 'Y'",
                "fa.account_id = :acct_id",
                f"fa.dateacct < '{anio}-{mes:02d}-01'",
            ]
            opening_params2: dict = {"acct_id": acct_id}
            _add_org_filter(opening_conds, opening_params2, org_ids, "fa")
            opening_q = text(
                f"SELECT COALESCE(SUM(fa.amtacctdr - fa.amtacctcr), 0) "
                f"FROM adempiere.fact_acct fa "
                f"WHERE {' AND '.join(opening_conds)}"
            )
            r = db.execute(opening_q, opening_params2).fetchone()
            saldo_inicial = float(r[0]) if r else 0.0

        saldo_final = saldo_inicial + total_debe - total_haber

        # 5. Daily breakdown (top 30 dates by movement)
        daily_q = text(
            f"SELECT fa.dateacct::date AS fecha, "
            f"COALESCE(SUM(fa.amtacctdr), 0) AS debe, "
            f"COALESCE(SUM(fa.amtacctcr), 0) AS haber, "
            f"COUNT(*) AS asientos "
            f"FROM adempiere.fact_acct fa WHERE {period_where} "
            f"GROUP BY fa.dateacct::date ORDER BY fa.dateacct::date "
            f"LIMIT 30"
        )
        daily = [
            {"fecha": str(r[0]), "debe": float(r[1]), "haber": float(r[2]), "asientos": r[3]}
            for r in db.execute(daily_q, period_params).fetchall()
        ]

        # 6. Currency info (get from first movement)
        currency_name = "VES"
        curr_q = text(
            f"SELECT DISTINCT c.iso_code FROM adempiere.fact_acct fa "
            f"JOIN adempiere.c_currency c ON fa.c_currency_id = c.c_currency_id "
            f"WHERE fa.account_id = :acct_id AND fa.isactive = 'Y' LIMIT 3"
        )
        curr_rows = db.execute(curr_q, {"acct_id": acct_id}).fetchall()
        if curr_rows:
            currency_name = ", ".join(r[0] for r in curr_rows)

        return {
            "cuenta_codigo": account_code,
            "cuenta_nombre": acct_name,
            "tipo_cuenta": {
                "A": "Activo", "L": "Pasivo", "O": "Patrimonio",
                "R": "Ingreso", "E": "Gasto",
            }.get(acct_type, acct_type),
            "periodo": period_label,
            "moneda": currency_name,
            "movimientos": movimientos,
            "total_debe": total_debe,
            "total_haber": total_haber,
            "saldo_inicial": saldo_inicial,
            "saldo_final": saldo_final,
            "detalle_diario": daily,
        }
    finally:
        db.close()

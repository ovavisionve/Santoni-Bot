"""Financial queries: bank balances, AR/AP summaries."""

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

from app.database import IdempiereSession

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
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
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
            f"ba.currentbalance AS saldo, "
            f"o.name AS organizacion "
            f"FROM adempiere.c_bankaccount ba "
            f"JOIN adempiere.c_bank b ON ba.c_bank_id = b.c_bank_id "
            f"LEFT JOIN adempiere.c_currency c ON ba.c_currency_id = c.c_currency_id "
            f"LEFT JOIN adempiere.ad_org o ON ba.ad_org_id = o.ad_org_id "
            f"WHERE {bank_where} "
            f"ORDER BY c.iso_code, b.name"
        )
        banks = [
            {
                "banco": r[0],
                "numero_cuenta": r[1],
                "tipo": r[2],
                "moneda": r[3],
                "saldo": float(r[4]) if r[4] else 0.0,
                "organizacion": r[5] or "Sin asignar",
            }
            for r in db.execute(bank_q, bank_params).fetchall()
        ]

        # Separate totals by currency
        totals_by_currency: dict[str, float] = {}
        for b in banks:
            cur = b["moneda"]
            totals_by_currency[cur] = totals_by_currency.get(cur, 0.0) + b["saldo"]

        # Group banks by currency for clearer presentation
        banks_ves = [b for b in banks if b["moneda"] == "VES"]
        banks_usd = [b for b in banks if b["moneda"] == "USD"]
        banks_other = [b for b in banks if b["moneda"] not in ("VES", "USD")]

        total_saldo_bancario = sum(b["saldo"] for b in banks)

        # Accounts receivable (unpaid sales invoices) - separated by currency
        # Uses LEFT JOIN to c_allocationline aggregation (_OPEN_EXPR) instead of
        # invoiceopen() PL/pgSQL function for ~100x speedup.
        cur_label = _currency_label("i")
        ar_conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
            f"{_OPEN_EXPR} > 0",
        ]
        ar_params: dict = {}
        _add_org_filter(ar_conditions, ar_params, org_ids, "i", exclude_demo=True)
        _add_date_filter(ar_conditions, ar_params, date_from, date_to, mes, anio, "i.dateinvoiced")

        ar_where = " AND ".join(ar_conditions)
        ar_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS facturas_pendientes, "
            f"COALESCE(SUM({_OPEN_EXPR}), 0) AS total_por_cobrar "
            f"FROM adempiere.c_invoice i "
            f"{_ALLOC_JOIN}"
            f"WHERE {ar_where} "
            f"GROUP BY {cur_label} ORDER BY total_por_cobrar DESC"
        )
        ar_rows = db.execute(ar_q, ar_params).fetchall()
        receivables = {
            "facturas_pendientes": sum(r[1] for r in ar_rows),
            "total_por_cobrar": sum(float(r[2]) for r in ar_rows),
            "por_moneda": [
                {"moneda": r[0], "facturas": r[1], "total": float(r[2])}
                for r in ar_rows
            ],
        }

        # Overdue receivables - also by currency
        overdue_conds = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
            f"{_OPEN_EXPR} > 0",
            "(i.dateinvoiced + CASE WHEN COALESCE(pt.netdays, 0) = 0 THEN 30 ELSE pt.netdays END) < CURRENT_DATE",
        ]
        overdue_params: dict = {}
        _add_org_filter(overdue_conds, overdue_params, org_ids, "i")
        overdue_where = " AND ".join(overdue_conds)
        overdue_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS facturas_vencidas, "
            f"COALESCE(SUM({_OPEN_EXPR}), 0) AS total_vencido "
            f"FROM adempiere.c_invoice i "
            f"{_ALLOC_JOIN}"
            f"LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id "
            f"WHERE {overdue_where} "
            f"GROUP BY {cur_label}"
        )
        overdue_rows = db.execute(overdue_q, overdue_params).fetchall()
        receivables["facturas_vencidas"] = sum(r[1] for r in overdue_rows)
        receivables["total_vencido"] = sum(float(r[2]) for r in overdue_rows)
        receivables["vencidas_por_moneda"] = [
            {"moneda": r[0], "facturas": r[1], "total": float(r[2])}
            for r in overdue_rows
        ]

        # Accounts payable (unpaid purchase invoices)
        ap_conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
            f"{_OPEN_EXPR} > 0",
        ]
        ap_params: dict = {}
        _add_org_filter(ap_conditions, ap_params, org_ids, "i", exclude_demo=True)
        _add_date_filter(ap_conditions, ap_params, date_from, date_to, mes, anio, "i.dateinvoiced")

        ap_where = " AND ".join(ap_conditions)
        ap_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS facturas_pendientes, "
            f"COALESCE(SUM({_OPEN_EXPR}), 0) AS total_por_pagar "
            f"FROM adempiere.c_invoice i "
            f"{_ALLOC_JOIN}"
            f"WHERE {ap_where} "
            f"GROUP BY {cur_label} ORDER BY total_por_pagar DESC"
        )
        ap_rows = db.execute(ap_q, ap_params).fetchall()
        payables = {
            "facturas_pendientes": sum(r[1] for r in ap_rows),
            "total_por_pagar": sum(float(r[2]) for r in ap_rows),
            "por_moneda": [
                {"moneda": r[0], "facturas": r[1], "total": float(r[2])}
                for r in ap_rows
            ],
        }

        # Overdue payables
        overdue_ap_conds = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
            f"{_OPEN_EXPR} > 0",
            "(i.dateinvoiced + CASE WHEN COALESCE(pt.netdays, 0) = 0 THEN 30 ELSE pt.netdays END) < CURRENT_DATE",
        ]
        overdue_ap_params: dict = {}
        _add_org_filter(overdue_ap_conds, overdue_ap_params, org_ids, "i")
        overdue_ap_where = " AND ".join(overdue_ap_conds)
        overdue_ap_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS facturas_vencidas, "
            f"COALESCE(SUM({_OPEN_EXPR}), 0) AS total_vencido "
            f"FROM adempiere.c_invoice i "
            f"{_ALLOC_JOIN}"
            f"LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id "
            f"WHERE {overdue_ap_where} "
            f"GROUP BY {cur_label}"
        )
        overdue_ap_rows = db.execute(overdue_ap_q, overdue_ap_params).fetchall()
        payables["facturas_vencidas"] = sum(r[1] for r in overdue_ap_rows)
        payables["total_vencido"] = sum(float(r[2]) for r in overdue_ap_rows)
        payables["vencidas_por_moneda"] = [
            {"moneda": r[0], "facturas": r[1], "total": float(r[2])}
            for r in overdue_ap_rows
        ]

        return {
            "anio": anio,
            "mes": mes,
            "saldos_bancarios": banks,
            "saldos_bancarios_ves": banks_ves,
            "saldos_bancarios_usd": banks_usd,
            "saldos_bancarios_otras": banks_other,
            "total_saldo_bancario": total_saldo_bancario,
            "totales_por_moneda": totals_by_currency,
            "cuentas_por_cobrar": receivables,
            "cuentas_por_pagar": payables,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------

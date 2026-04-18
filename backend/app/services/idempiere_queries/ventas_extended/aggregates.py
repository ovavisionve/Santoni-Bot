"""Small aggregate queries: exchange rates, tax summary, sales by branch."""

from sqlalchemy import text

from app.database import IdempiereSession

from ..common import (
    _add_currency_filter,
    _add_date_filter,
    _add_org_filter,
    _add_org_name_filter,
    _get_session,
)
from ..ventas_helpers import _currency_label


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

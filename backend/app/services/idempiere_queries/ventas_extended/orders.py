"""Sales orders queries (c_order pipeline)."""

from sqlalchemy import text

from ..common import (
    _add_currency_filter,
    _add_date_filter,
    _add_org_filter,
    _add_org_name_filter,
    _get_session,
)
from ..ventas_helpers import _currency_label, _dedupe_salesrep_rows


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

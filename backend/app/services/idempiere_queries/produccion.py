"""Production queries: summary and orders."""

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
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = ["io.isactive = 'Y'", "io.docstatus IN ('CO', 'CL')"]
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
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = ["io.isactive = 'Y'", "io.docstatus IN ('CO', 'CL')"]
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

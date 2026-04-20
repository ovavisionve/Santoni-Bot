"""Core ventas queries: sales summary, collection summary, top clients."""

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
from .ventas_helpers import (
    _ZONE_TO_REGION,
    _region_case_sql,
    _currency_label,
    _add_salesrep_filter,
    _dedupe_salesrep_rows,
)

from app.database import IdempiereSession

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
    """Sales summary from iDempiere c_invoice (issotrx='Y').

    Excludes credit notes (ARC) from the main totals and shows them
    separately so the user sees net sales = facturas - notas de crédito.

    NOTA SOBRE FLUJO DE DOCUMENTOS (REGLA #8 — 15/Abr/2026):
    En Santoni los c_invoice incluyen DOS tipos de documentos con el mismo
    docbasetype='ARI': (1) ProFormas (dt.name ILIKE '%Proforma%' o
    '%ProDolares%') — USD preliminar, corazón del reporte USD — y (2)
    Facturas Legales (dt.name con 'AR Invoice B/F/E', 'Factura AGA',
    'AR Invoice Dolares', etc.) — cierre legal Bs.

    Esta función AGRUPA AMBOS tipos sin distinguir. Para queries donde el
    usuario necesita desagregar ProForma vs Factura (típicamente reportes
    USD vs cierre SENIAT), SQL Directo maneja la distinción directamente
    vía c_doctype.name — este agente clásico es fallback y retorna el
    total combinado sin distinción.

    TODO (post-validación con esalas/Darwin): considerar agregar parámetro
    `doctype_filter: Literal["facturas_legales", "proformas", "todas"]`
    para devolver métricas separadas. Pendiente hasta confirmar semántica
    con el equipo de contabilidad de Santoni.
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        # INFR-102: exclude_demo=True para evitar que orgs demo de iDempiere
        # contaminen los totales USD cuando no hay filtro de org explícito.
        _add_org_filter(conditions, params, org_ids, "i", exclude_demo=True)
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
            "LEFT JOIN adempiere.ad_user sr "
            "ON i.salesrep_id = sr.ad_user_id "
            "LEFT JOIN client_zone cz "
            "ON i.c_bpartner_id = cz.c_bpartner_id "
            "JOIN adempiere.c_doctype dt "
            "ON i.c_doctypetarget_id = dt.c_doctype_id "
        )

        # Only regular invoices (ARI), exclude credit notes (ARC)
        where_invoices = f"{where} AND dt.docbasetype = 'ARI'"
        where_credit = f"{where} AND dt.docbasetype = 'ARC'"

        # Totals (only invoices)
        totals_q = text(
            f"{zone_cte}"
            f"SELECT COUNT(*) AS total_facturas, "
            f"COALESCE(SUM(i.totallines), 0) AS total_facturado, "
            f"COALESCE(SUM(i.totallines), 0) AS total_neto, "
            f"COALESCE(SUM(i.grandtotal - i.totallines), 0) AS total_iva "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where_invoices}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_facturas": row[0] if row else 0,
            "total_facturado": float(row[1]) if row else 0.0,
            "total_neto": float(row[2]) if row else 0.0,
            "total_iva": float(row[3]) if row else 0.0,
        }

        # Credit notes totals
        credit_q = text(
            f"{zone_cte}"
            f"SELECT COUNT(*) AS total_nc, "
            f"COALESCE(SUM(i.totallines), 0) AS total_nc_monto "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where_credit}"
        )
        cn_row = db.execute(credit_q, params).fetchone()
        notas_credito = {
            "total_notas_credito": cn_row[0] if cn_row else 0,
            "monto_notas_credito": float(cn_row[1]) if cn_row else 0.0,
        }
        totals["total_notas_credito"] = notas_credito["total_notas_credito"]
        totals["monto_notas_credito"] = notas_credito["monto_notas_credito"]
        totals["venta_neta"] = totals["total_neto"] - notas_credito["monto_notas_credito"]

        # By sales region (zona) - only invoices, net of credit notes
        by_zone_q = text(
            f"{zone_cte}"
            f"SELECT COALESCE(cz.zona_name, 'Sin Zona') AS zona, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines ELSE 0 END), 0) AS total_bruto, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.totallines ELSE 0 END), 0) AS total_nc, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END), 0) AS total_neto "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY cz.zona_name ORDER BY total_neto DESC"
        )
        by_zone = [
            {"zona": r[0], "facturas": r[1], "total_bruto": float(r[2]),
             "notas_credito": float(r[3]), "total": float(r[4])}
            for r in db.execute(by_zone_q, params).fetchall()
        ]

        # By macro region (groups zones into Llanos, Centro, Occidente, etc.)
        region_case = _region_case_sql()
        by_region_q = text(
            f"{zone_cte}"
            f"SELECT {region_case} AS region, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY {region_case} ORDER BY total DESC"
        )
        by_region = [
            {"region": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_region_q, params).fetchall()
        ]

        # By salesperson (salesrep_id → ad_user)
        by_salesperson_q = text(
            f"{zone_cte}"
            f"SELECT COALESCE(sr.name, 'Sin Vendedor') AS vendedor, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines ELSE 0 END), 0) AS total_bruto, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.totallines ELSE 0 END), 0) AS monto_nc, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY sr.name ORDER BY total_bruto DESC"
        )
        by_salesperson = [
            {
                "vendedor": r[0], "facturas": r[1], "notas_credito": r[2],
                "total_bruto": float(r[3]), "monto_nc": float(r[4]),
                "total": float(r[5]),
            }
            for r in db.execute(by_salesperson_q, params).fetchall()
        ]
        # Consolida nombres duplicados del mismo vendedor
        # (ej: "ROJAS OBANDO RENEE" == "RENEE ROJAS OBANDO")
        by_salesperson = _dedupe_salesrep_rows(
            by_salesperson,
            numeric_keys=["facturas", "notas_credito", "total_bruto", "monto_nc", "total"],
            sort_key="total_bruto",
        )

        # By month - net of credit notes
        by_month_q = text(
            f"{zone_cte}"
            f"SELECT EXTRACT(MONTH FROM i.dateinvoiced)::int AS mes, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY EXTRACT(MONTH FROM i.dateinvoiced) ORDER BY mes"
        )
        by_month = [
            {"mes": r[0], "facturas": r[1], "notas_credito": r[2], "total": float(r[3])}
            for r in db.execute(by_month_q, params).fetchall()
        ]

        # By currency (so user sees totals per currency instead of mixed)
        cur_label = _currency_label("i")
        by_currency_q = text(
            f"{zone_cte}"
            f"SELECT {cur_label} AS moneda, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines ELSE 0 END), 0) AS total_facturado, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.totallines ELSE 0 END), 0) AS monto_nc, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END), 0) AS venta_neta "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY {cur_label} ORDER BY venta_neta DESC"
        )
        by_currency = [
            {"moneda": r[0], "facturas": r[1], "notas_credito": r[2],
             "total_facturado": float(r[3]), "monto_notas_credito": float(r[4]),
             "venta_neta": float(r[5])}
            for r in db.execute(by_currency_q, params).fetchall()
        ]

        # Embed per-currency totals directly in totales so the LLM
        # always sees the Bs./USD breakdown prominently
        totals["por_moneda"] = by_currency

        return {
            "anio": anio,
            "filtros": {"zona": zona, "vendedor": vendedor, "mes": mes},
            "totales": totals,
            "por_region": by_region,
            "por_zona": by_zone,
            "por_vendedor": by_salesperson,
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
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "p.isreceipt = 'Y'",
            "p.docstatus IN ('CO', 'CL')",
            "p.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "p", exclude_demo=True)
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
            f"  WHEN 'A' THEN 'Depósito Directo' "
            f"  WHEN 'C' THEN 'Cheque' "
            f"  WHEN 'D' THEN 'Débito Directo' "
            f"  WHEN 'J' THEN 'Comisión Bancaria' "
            f"  WHEN 'K' THEN 'Cheque' "
            f"  WHEN 'P' THEN 'Impuesto' "
            f"  WHEN 'Q' THEN 'Giro' "
            f"  WHEN 'R' THEN 'Dólar IGTF' "
            f"  WHEN 'S' THEN 'Transferencia Empresas' "
            f"  WHEN 'T' THEN 'Cuenta' "
            f"  WHEN 'U' THEN 'Euro Transferencia' "
            f"  WHEN 'W' THEN 'Transferencia' "
            f"  WHEN 'X' THEN 'Efectivo' "
            f"  WHEN 'Y' THEN 'Dólar Efectivo' "
            f"  WHEN 'Z' THEN 'Dólar Transferencia' "
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
    """Top clients by net invoiced amount from iDempiere.

    Uses client_zone CTE to avoid JOIN multiplication from
    c_bpartner_location having multiple rows per client.

    Credit notes (ARC) are subtracted from the client's total so the
    ranking reflects net sales per client.
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
            "bp.iscustomer = 'Y'",
        ]
        params: dict = {"limit": limit}
        _add_org_filter(conditions, params, org_ids, "i", exclude_demo=True)
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
        # GROUP BY solo por cliente + moneda para evitar duplicados
        # cuando un cliente tiene facturas con diferentes vendedores o zonas.
        # Zona y tipología se toman del cliente (1:1), vendedor se agrega con MODE().
        q = text(
            f"{zone_cte}"
            f"SELECT bp.value AS codigo, bp.name AS nombre, "
            f"COALESCE(MAX(cz.zona_name), 'Sin Zona') AS zona, "
            f"COALESCE(MODE() WITHIN GROUP (ORDER BY sr.name), 'Sin Vendedor') AS vendedor, "
            f"COALESCE(MAX(bpg.name), 'Sin Tipología') AS tipologia, "
            f"{cur_label} AS moneda, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines ELSE 0 END), 0) AS total_bruto, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.totallines ELSE 0 END), 0) AS monto_nc, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.totallines "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.totallines ELSE 0 END), 0) AS total_facturado "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"LEFT JOIN adempiere.ad_user sr ON i.salesrep_id = sr.ad_user_id "
            f"LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id "
            f"LEFT JOIN adempiere.c_bp_group bpg ON bp.c_bp_group_id = bpg.c_bp_group_id "
            f"JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id "
            f"WHERE {where} "
            f"GROUP BY bp.value, bp.name, {cur_label} "
            f"ORDER BY total_bruto DESC "
            f"LIMIT :limit"
        )
        logger.info("build_top_clients SQL WHERE: %s | params: %s", where, {k: v for k, v in params.items() if k != "limit"})
        rows = db.execute(q, params).fetchall()
        logger.info("build_top_clients returned %d rows", len(rows))
        return [
            {
                "codigo": r[0],
                "nombre": r[1],
                "zona": r[2],
                "vendedor": r[3],
                "tipologia": r[4],
                "moneda": r[5],
                "facturas": r[6],
                "notas_credito": r[7],
                "total_bruto": float(r[8]),
                "monto_nc": float(r[9]),
                "total_facturado": float(r[10]),
            }
            for r in rows
        ]
    finally:
        db.close()


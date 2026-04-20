"""Sales query wrappers: summary, collection, top clients, etc."""

import logging

from sqlalchemy import text

from app.database import SessionLocal
from .core import _is_production, _rows_to_dicts, _convert_value

logger = logging.getLogger("santonibot.query_service")

# ---------------------------------------------------------------------------
# Pre-built queries: VENTAS (Sales)
# ---------------------------------------------------------------------------

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
    """Sales summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_sales_summary as _prod
        return _prod(
            zona=zona, vendedor=vendedor, mes=mes, anio=anio,
            org_ids=org_ids, salesrep_id=salesrep_id,
            date_from=date_from, date_to=date_to,
            currency_ids=currency_ids, org_name=org_name,
        )

    db = SessionLocal()
    try:
        conditions = ["EXTRACT(YEAR FROM f.fecha) = :anio", "f.estado != 'anulada'"]
        params: dict = {"anio": anio}

        if zona:
            conditions.append("f.zona = :zona")
            params["zona"] = zona
        if vendedor:
            conditions.append("f.vendedor = :vendedor")
            params["vendedor"] = vendedor
        if mes:
            conditions.append("EXTRACT(MONTH FROM f.fecha) = :mes")
            params["mes"] = mes

        where = " AND ".join(conditions)

        totals_q = text(
            f"SELECT COUNT(*) AS total_facturas, "
            f"COALESCE(SUM(f.monto_total), 0) AS total_facturado, "
            f"COALESCE(SUM(f.monto_neto), 0) AS total_neto, "
            f"COALESCE(SUM(f.monto_iva), 0) AS total_iva "
            f"FROM demo_facturas_venta f WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_facturas": row[0] if row else 0,
            "total_facturado": float(row[1]) if row else 0.0,
            "total_neto": float(row[2]) if row else 0.0,
            "total_iva": float(row[3]) if row else 0.0,
        }

        by_zone_q = text(
            f"SELECT f.zona, COUNT(*) AS facturas, "
            f"COALESCE(SUM(f.monto_total), 0) AS total "
            f"FROM demo_facturas_venta f WHERE {where} "
            f"GROUP BY f.zona ORDER BY total DESC"
        )
        by_zone = [
            {"zona": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_zone_q, params).fetchall()
        ]

        by_vendor_q = text(
            f"SELECT f.vendedor, COUNT(*) AS facturas, "
            f"COALESCE(SUM(f.monto_total), 0) AS total "
            f"FROM demo_facturas_venta f WHERE {where} "
            f"GROUP BY f.vendedor ORDER BY total DESC"
        )
        by_vendor = [
            {"vendedor": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_vendor_q, params).fetchall()
        ]

        by_month_q = text(
            f"SELECT EXTRACT(MONTH FROM f.fecha)::int AS mes, COUNT(*) AS facturas, "
            f"COALESCE(SUM(f.monto_total), 0) AS total "
            f"FROM demo_facturas_venta f WHERE {where} "
            f"GROUP BY mes ORDER BY mes"
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
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> dict:
    """Collection summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_collection_summary as _prod
        return _prod(
            zona=zona, vendedor=vendedor, mes=mes, anio=anio,
            org_ids=org_ids, salesrep_id=salesrep_id,
            date_from=date_from, date_to=date_to,
            currency_ids=currency_ids, org_name=org_name,
        )

    db = SessionLocal()
    try:
        conditions = ["EXTRACT(YEAR FROM c.fecha) = :anio"]
        params: dict = {"anio": anio}

        if zona:
            conditions.append("c.zona = :zona")
            params["zona"] = zona
        if vendedor:
            conditions.append("c.vendedor = :vendedor")
            params["vendedor"] = vendedor
        if mes:
            conditions.append("EXTRACT(MONTH FROM c.fecha) = :mes")
            params["mes"] = mes

        where = " AND ".join(conditions)

        totals_q = text(
            f"SELECT COUNT(*) AS total_recibos, "
            f"COALESCE(SUM(c.monto), 0) AS total_cobrado "
            f"FROM demo_cobranzas c WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_recibos": row[0] if row else 0,
            "total_cobrado": float(row[1]) if row else 0.0,
        }

        by_method_q = text(
            f"SELECT c.metodo_pago, COUNT(*) AS recibos, "
            f"COALESCE(SUM(c.monto), 0) AS total "
            f"FROM demo_cobranzas c WHERE {where} "
            f"GROUP BY c.metodo_pago ORDER BY total DESC"
        )
        by_method = [
            {"metodo_pago": r[0], "recibos": r[1], "total": float(r[2])}
            for r in db.execute(by_method_q, params).fetchall()
        ]

        by_vendor_q = text(
            f"SELECT c.vendedor, COUNT(*) AS recibos, "
            f"COALESCE(SUM(c.monto), 0) AS total "
            f"FROM demo_cobranzas c WHERE {where} "
            f"GROUP BY c.vendedor ORDER BY total DESC"
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
    """Top clients - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_top_clients as _prod
        return _prod(
            limit=limit, zona=zona, vendedor=vendedor, mes=mes, anio=anio,
            org_ids=org_ids, salesrep_id=salesrep_id,
            date_from=date_from, date_to=date_to,
            currency_ids=currency_ids, org_name=org_name,
        )

    db = SessionLocal()
    try:
        conditions = [
            "EXTRACT(YEAR FROM f.fecha) = :anio",
            "f.estado != 'anulada'",
        ]
        params: dict = {"anio": anio, "limit": limit}

        if zona:
            conditions.append("f.zona = :zona")
            params["zona"] = zona
        if vendedor:
            conditions.append("f.vendedor = :vendedor")
            params["vendedor"] = vendedor

        where = " AND ".join(conditions)

        q = text(
            f"SELECT cl.codigo, cl.nombre, cl.zona, cl.vendedor, cl.tipologia, "
            f"COUNT(f.id) AS facturas, "
            f"COALESCE(SUM(f.monto_total), 0) AS total_facturado "
            f"FROM demo_facturas_venta f "
            f"JOIN demo_clientes cl ON cl.id = f.cliente_id "
            f"WHERE {where} "
            f"GROUP BY cl.codigo, cl.nombre, cl.zona, cl.vendedor, cl.tipologia "
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


def build_overdue_receivables(org_ids: list[int] | None = None, salesrep_id: int | None = None) -> list[dict]:
    """Overdue receivables - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_overdue_receivables as _prod
        return _prod(org_ids=org_ids, salesrep_id=salesrep_id)

    db = SessionLocal()
    try:
        q = text(
            "SELECT f.numero_factura, cl.nombre AS cliente, f.vendedor, f.zona, "
            "f.monto_total, f.fecha, f.fecha_vencimiento, "
            "CURRENT_DATE - f.fecha_vencimiento AS dias_vencido "
            "FROM demo_facturas_venta f "
            "JOIN demo_clientes cl ON cl.id = f.cliente_id "
            "WHERE f.estado = 'pendiente' AND f.fecha_vencimiento < CURRENT_DATE "
            "ORDER BY dias_vencido DESC"
        )
        rows = db.execute(q).fetchall()
        return [
            {
                "numero_factura": r[0],
                "cliente": r[1],
                "vendedor": r[2],
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
    """Sales by product - routes to iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_sales_by_product as _prod
        return _prod(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
            currency_ids=currency_ids, org_name=org_name,
            product_search=product_search, category_search=category_search,
            only_skus=only_skus, limit=limit,
        )
    # No demo implementation — return empty structure
    return {"anio": anio, "top_productos": [], "por_categoria": []}


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
    """Sales orders - routes to iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_sales_orders as _prod
        return _prod(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
            currency_ids=currency_ids, org_name=org_name,
            only_pending=only_pending,
        )
    return {"anio": anio, "por_estado": [], "por_vendedor": [], "por_cliente": [], "por_moneda": [], "por_sucursal": []}


def build_exchange_rates(limit: int = 30) -> list[dict]:
    """Exchange rates - routes to iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_exchange_rates as _prod
        return _prod(limit=limit)
    return []


def build_sales_tax_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> dict:
    """Sales tax summary - routes to iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_sales_tax_summary as _prod
        return _prod(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
            currency_ids=currency_ids, org_name=org_name,
        )
    return {"anio": anio, "por_impuesto": [], "retenciones": []}


def build_sales_by_branch(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> list[dict]:
    """Sales by branch - routes to iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_sales_by_branch as _prod
        return _prod(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
            currency_ids=currency_ids, org_name=org_name,
        )
    return []


# ---------------------------------------------------------------------------
# Pre-built queries: PRODUCCION (Production)
# ---------------------------------------------------------------------------

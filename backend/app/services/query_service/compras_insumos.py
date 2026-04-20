"""Supply purchase query wrappers."""

import logging

from sqlalchemy import text

from app.database import SessionLocal
from .core import _is_production, _rows_to_dicts, _convert_value

logger = logging.getLogger("santonibot.query_service")

def build_supply_purchases(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | list[str] | None = None,
) -> dict:
    """Supply purchases - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_supply_purchases as _prod
        return _prod(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
            currency_ids=currency_ids, org_name=org_name,
        )

    # Demo fallback
    db = SessionLocal()
    try:
        totals_q = text(
            "SELECT COUNT(*) AS total_ordenes, "
            "COALESCE(SUM(o.monto_total), 0) AS total_monto "
            "FROM demo_ordenes_compra_insumos o"
        )
        row = db.execute(totals_q).fetchone()
        return {
            "anio": anio,
            "mes": mes,
            "totales": {
                "total_ordenes": row[0] if row else 0,
                "total_monto": float(row[1]) if row else 0.0,
            },
            "por_proveedor": [],
            "por_mes": [],
            "por_producto": [],
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
    org_name: str | None = None,
) -> list[dict]:
    """Product purchase history - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_product_purchase_history as _prod
        return _prod(
            product_search=product_search, org_ids=org_ids,
            date_from=date_from, date_to=date_to, mes=mes, anio=anio,
            org_name=org_name,
        )
    return []


def build_pending_purchase_orders(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    product_search: str | None = None,
    org_name: str | list[str] | None = None,
) -> dict:
    """Pending purchase orders - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_pending_purchase_orders as _prod
        return _prod(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
            currency_ids=currency_ids, product_search=product_search,
            org_name=org_name,
        )
    return {
        "anio": anio, "mes": mes,
        "totales": {"total_ordenes": 0, "total_monto": 0.0},
        "por_estado": [], "por_proveedor": [], "detalle_ordenes": [],
    }


def build_supplier_price_comparison(
    product_search: str,
    org_ids: list[int] | None = None,
    anio: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
) -> list[dict]:
    """Supplier price comparison - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_supplier_price_comparison as _prod
        return _prod(
            product_search=product_search, org_ids=org_ids,
            anio=anio, date_from=date_from, date_to=date_to,
            org_name=org_name,
        )
    return []


def build_purchase_payment_status(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | list[str] | None = None,
) -> dict:
    """Purchase payment status - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_purchase_payment_status as _prod
        return _prod(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
            org_name=org_name,
        )
    return {"resumen_pago": [], "facturas_vencidas": []}


# ---------------------------------------------------------------------------
# Pre-built queries: CONTABILIDAD (Accounting)
# ---------------------------------------------------------------------------


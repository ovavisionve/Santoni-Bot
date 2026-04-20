"""Inventory query wrappers: stock levels."""

import logging

from sqlalchemy import text

from app.database import SessionLocal
from .core import _is_production, _rows_to_dicts, _convert_value

logger = logging.getLogger("santonibot.query_service")

def build_inventory_stock(
    org_ids: list[int] | None = None,
    product_search: str | None = None,
    category_search: str | None = None,
    warehouse_search: str | None = None,
    org_name: str | list[str] | None = None,
) -> dict:
    """Inventory stock - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_inventory_stock as _prod
        return _prod(
            org_ids=org_ids, product_search=product_search,
            category_search=category_search, warehouse_search=warehouse_search,
            org_name=org_name,
        )

    # Demo fallback
    return {
        "totales": {
            "productos_con_stock": 0,
            "cantidad_total": 0.0,
        },
        "filtros": {
            "producto": product_search,
            "categoria": category_search,
            "almacen": warehouse_search,
        },
        "por_organizacion": [],
        "por_categoria": [],
        "detalle_productos": [],
    }

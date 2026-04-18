"""Production query wrappers: summary and orders."""

import logging

from sqlalchemy import text

from app.database import SessionLocal
from .core import _is_production, _rows_to_dicts, _convert_value

logger = logging.getLogger("santonibot.query_service")


def build_production_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Production summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_production_summary as _prod
        return _prod(mes=mes, anio=anio, org_ids=org_ids, date_from=date_from, date_to=date_to)

    db = SessionLocal()
    try:
        conditions = ["EXTRACT(YEAR FROM p.fecha) = :anio"]
        params: dict = {"anio": anio}

        if mes:
            conditions.append("EXTRACT(MONTH FROM p.fecha) = :mes")
            params["mes"] = mes

        where = " AND ".join(conditions)

        totals_q = text(
            f"SELECT COALESCE(SUM(p.cantidad_kg), 0) AS total_producido_kg, "
            f"COALESCE(SUM(p.desperdicio_kg), 0) AS total_desperdicio_kg, "
            f"COALESCE(SUM(p.horas_operacion), 0) AS total_horas_operacion, "
            f"COALESCE(SUM(p.horas_parada), 0) AS total_horas_parada "
            f"FROM demo_produccion_diaria p WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        total_prod = float(row[0]) if row else 0.0
        total_desp = float(row[1]) if row else 0.0
        totals = {
            "total_producido_kg": total_prod,
            "total_desperdicio_kg": total_desp,
            "porcentaje_desperdicio": round(
                (total_desp / total_prod * 100) if total_prod > 0 else 0, 2
            ),
            "total_horas_operacion": float(row[2]) if row else 0.0,
            "total_horas_parada": float(row[3]) if row else 0.0,
        }

        by_plant_q = text(
            f"SELECT p.planta, COALESCE(SUM(p.cantidad_kg), 0) AS producido, "
            f"COALESCE(SUM(p.desperdicio_kg), 0) AS desperdicio, "
            f"COALESCE(SUM(p.horas_operacion), 0) AS horas_op, "
            f"COALESCE(SUM(p.horas_parada), 0) AS horas_par "
            f"FROM demo_produccion_diaria p WHERE {where} "
            f"GROUP BY p.planta ORDER BY producido DESC"
        )
        by_plant = [
            {
                "planta": r[0],
                "producido_kg": float(r[1]),
                "desperdicio_kg": float(r[2]),
                "horas_operacion": float(r[3]),
                "horas_parada": float(r[4]),
            }
            for r in db.execute(by_plant_q, params).fetchall()
        ]

        by_product_q = text(
            f"SELECT p.producto, COALESCE(SUM(p.cantidad_kg), 0) AS producido "
            f"FROM demo_produccion_diaria p WHERE {where} "
            f"GROUP BY p.producto ORDER BY producido DESC"
        )
        by_product = [
            {"producto": r[0], "producido_kg": float(r[1])}
            for r in db.execute(by_product_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "mes": mes,
            "totales": totals,
            "por_planta": by_plant,
            "por_producto": by_product,
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
    """Manufacturing orders - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_production_orders as _prod
        return _prod(mes=mes, anio=anio, org_ids=org_ids, date_from=date_from, date_to=date_to)

    # Demo fallback
    return []


# ---------------------------------------------------------------------------
# Pre-built queries: COMPRAS PRODUCTORES (Producer Purchases)
# ---------------------------------------------------------------------------


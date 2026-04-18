"""Producer purchase query wrappers."""

import logging

from sqlalchemy import text

from app.database import SessionLocal
from .core import _is_production, _rows_to_dicts, _convert_value

logger = logging.getLogger("santonibot.query_service")

def build_producer_purchases(
    producto: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
) -> dict:
    """Producer purchases - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_producer_purchases as _prod
        return _prod(
            producto=producto, mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to, org_name=org_name,
        )

    db = SessionLocal()
    try:
        conditions = ["EXTRACT(YEAR FROM cp.fecha) = :anio"]
        params: dict = {"anio": anio}

        if mes:
            conditions.append("EXTRACT(MONTH FROM cp.fecha) = :mes")
            params["mes"] = mes

        if producto:
            conditions.append("LOWER(cp.producto) LIKE :producto")
            params["producto"] = f"%{producto.lower()}%"

        where = " AND ".join(conditions)

        totals_q = text(
            f"SELECT COUNT(*) AS total_guias, "
            f"COALESCE(SUM(cp.peso_neto_kg), 0) AS total_peso_neto_kg, "
            f"COALESCE(SUM(cp.monto_total), 0) AS total_monto "
            f"FROM demo_compras_productores cp WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_guias": row[0] if row else 0,
            "total_peso_neto_kg": float(row[1]) if row else 0.0,
            "total_monto": float(row[2]) if row else 0.0,
        }

        by_product_q = text(
            f"SELECT cp.producto, COUNT(*) AS guias, "
            f"COALESCE(SUM(cp.peso_neto_kg), 0) AS peso_neto_kg, "
            f"COALESCE(SUM(cp.monto_total), 0) AS monto_total, "
            f"COALESCE(AVG(cp.humedad_porcentaje), 0) AS humedad_promedio, "
            f"COALESCE(AVG(cp.impureza_porcentaje), 0) AS impureza_promedio "
            f"FROM demo_compras_productores cp WHERE {where} "
            f"GROUP BY cp.producto ORDER BY monto_total DESC"
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

        by_producer_q = text(
            f"SELECT pr.nombre, pr.estado, pr.municipio, "
            f"COUNT(*) AS guias, "
            f"COALESCE(SUM(cp.peso_neto_kg), 0) AS peso_neto_kg, "
            f"COALESCE(SUM(cp.monto_total), 0) AS monto_total "
            f"FROM demo_compras_productores cp "
            f"JOIN demo_productores pr ON pr.id = cp.productor_id "
            f"WHERE {where} "
            f"GROUP BY pr.nombre, pr.estado, pr.municipio "
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
    """Registered producers/vendors - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_registered_producers as _prod
        return _prod(org_ids=org_ids)

    db = SessionLocal()
    try:
        q = text(
            "SELECT nombre AS productor, cedula AS codigo, estado AS ciudad "
            "FROM demo_productores WHERE activo = true ORDER BY nombre LIMIT 50"
        )
        return [
            {"productor": r[0], "codigo": r[1], "ciudad": r[2]}
            for r in db.execute(q).fetchall()
        ]
    finally:
        db.close()


def build_producer_pending_payments(
    producto: str | None = None,
    org_ids: list[int] | None = None,
    producer_name: str | None = None,
    currency_ids: list[int] | None = None,
) -> list[dict]:
    """Pending producer payments - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_producer_pending_payments as _prod
        return _prod(producto=producto, org_ids=org_ids, producer_name=producer_name, currency_ids=currency_ids)

    db = SessionLocal()
    try:
        q = text(
            "SELECT p.nombre AS productor, c.id::text AS documento, "
            "c.fecha::text AS fecha, c.monto_total "
            "FROM demo_compras_productores c "
            "JOIN demo_productores p ON c.productor_id = p.id "
            "WHERE c.estado_pago = 'pendiente' ORDER BY c.monto_total DESC"
        )
        return [
            {
                "productor": r[0], "documento": r[1], "fecha": str(r[2]),
                "monto_total": float(r[3]),
            }
            for r in db.execute(q).fetchall()
        ]
    finally:
        db.close()


def build_producer_price_analysis(
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Price analysis for producer purchases - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_producer_price_analysis as _prod
        return _prod(anio=anio, org_ids=org_ids, date_from=date_from, date_to=date_to)

    db = SessionLocal()
    try:
        q = text(
            "SELECT producto, "
            "MIN(precio_kg) AS precio_min, AVG(precio_kg) AS precio_promedio, "
            "MAX(precio_kg) AS precio_max, COUNT(*) AS compras "
            "FROM demo_compras_productores "
            "WHERE EXTRACT(YEAR FROM fecha) = :anio GROUP BY producto"
        )
        return [
            {
                "producto": r[0], "precio_min": float(r[1]),
                "precio_promedio": float(r[2]), "precio_max": float(r[3]),
                "compras": r[4],
            }
            for r in db.execute(q, {"anio": anio}).fetchall()
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pre-built queries: FINANZAS (Finance)
# ---------------------------------------------------------------------------


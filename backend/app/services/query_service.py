"""
Query service for AI agents - routes queries to the correct data source.

- APP_ENV=development → demo tables (internal PostgreSQL, fake data for QA)
- APP_ENV=production  → iDempiere tables (192.168.1.73, real data)

Agents import from this module and are unaware of the data source.
"""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.database import SessionLocal, IdempiereSession
from app.config import get_settings

logger = logging.getLogger("santonibot.query_service")


def _is_production() -> bool:
    """Check if we should use iDempiere (production) or demo tables."""
    return get_settings().app_env == "production"


# ---------------------------------------------------------------------------
# Helpers (shared)
# ---------------------------------------------------------------------------

def _convert_value(val):
    """Convert non-JSON-serializable types to serializable ones."""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, date):
        return val.isoformat()
    return val


def _rows_to_dicts(rows, columns) -> list[dict]:
    """Convert SQLAlchemy result rows to a list of dicts with clean values."""
    return [
        {col: _convert_value(row[i]) for i, col in enumerate(columns)}
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Core query function (generic SQL execution)
# ---------------------------------------------------------------------------

def execute_demo_query(query: str, params: dict | None = None) -> list[dict]:
    """Execute a read-only SELECT query against the active data source.
    In development: queries demo_* tables in internal DB.
    In production: queries adempiere.* tables in iDempiere."""
    q = query.strip().rstrip(";")
    if not q.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    if _is_production():
        from app.services.idempiere_queries import execute_idempiere_query
        return execute_idempiere_query(query, params)

    db = SessionLocal()
    try:
        result = db.execute(text(q), params or {})
        columns = list(result.keys())
        rows = result.fetchall()
        return _rows_to_dicts(rows, columns)
    finally:
        db.close()


def get_table_schema(table_name: str) -> list[dict]:
    """Get column info for a table."""
    session_class = IdempiereSession if _is_production() else SessionLocal
    schema = "adempiere" if _is_production() else None

    db = session_class()
    try:
        conditions = "table_name = :table_name"
        params = {"table_name": table_name}
        if schema:
            conditions += " AND table_schema = :schema"
            params["schema"] = schema

        result = db.execute(
            text(
                f"SELECT column_name, data_type, is_nullable "
                f"FROM information_schema.columns "
                f"WHERE {conditions} "
                f"ORDER BY ordinal_position"
            ),
            params,
        )
        return [
            {
                "column": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
            }
            for row in result.fetchall()
        ]
    finally:
        db.close()


def get_available_tables() -> list[str]:
    """Return list of available table names."""
    if _is_production():
        db = IdempiereSession()
        try:
            result = db.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'adempiere' "
                    "ORDER BY table_name"
                )
            )
            return [row[0] for row in result.fetchall()]
        finally:
            db.close()

    db = SessionLocal()
    try:
        result = db.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name LIKE 'demo_%' "
                "ORDER BY table_name"
            )
        )
        return [row[0] for row in result.fetchall()]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pre-built queries: VENTAS (Sales)
# ---------------------------------------------------------------------------

def build_sales_summary(
    zona: str | None = None,
    vendedor: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
) -> dict:
    """Sales summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_sales_summary as _prod
        return _prod(zona=zona, vendedor=vendedor, mes=mes, anio=anio)

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
) -> dict:
    """Collection summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_collection_summary as _prod
        return _prod(zona=zona, vendedor=vendedor, mes=mes, anio=anio)

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
    anio: int | None = None,
) -> list[dict]:
    """Top clients - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_top_clients as _prod
        return _prod(limit=limit, zona=zona, vendedor=vendedor, anio=anio)

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


def build_overdue_receivables() -> list[dict]:
    """Overdue receivables - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_overdue_receivables as _prod
        return _prod()

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


# ---------------------------------------------------------------------------
# Pre-built queries: PRODUCCION (Production)
# ---------------------------------------------------------------------------

def build_production_summary(mes: int | None = None, anio: int | None = None) -> dict:
    """Production summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_production_summary as _prod
        return _prod(mes=mes, anio=anio)

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


# ---------------------------------------------------------------------------
# Pre-built queries: COMPRAS PRODUCTORES (Producer Purchases)
# ---------------------------------------------------------------------------

def build_producer_purchases(
    producto: str | None = None, anio: int | None = None
) -> dict:
    """Producer purchases - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_producer_purchases as _prod
        return _prod(producto=producto, anio=anio)

    db = SessionLocal()
    try:
        conditions = ["EXTRACT(YEAR FROM cp.fecha) = :anio"]
        params: dict = {"anio": anio}

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


# ---------------------------------------------------------------------------
# Pre-built queries: FINANZAS (Finance)
# ---------------------------------------------------------------------------

def build_financial_summary(mes: int | None = None, anio: int | None = None) -> dict:
    """Financial summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_financial_summary as _prod
        return _prod(mes=mes, anio=anio)

    db = SessionLocal()
    try:
        bank_q = text(
            "SELECT banco, numero_cuenta, tipo, moneda, saldo, fecha_saldo "
            "FROM demo_cuentas_bancarias ORDER BY banco"
        )
        banks = [
            {
                "banco": r[0],
                "numero_cuenta": r[1],
                "tipo": r[2],
                "moneda": r[3],
                "saldo": float(r[4]),
                "fecha_saldo": r[5].isoformat() if r[5] else None,
            }
            for r in db.execute(bank_q).fetchall()
        ]
        total_saldo_bancario = sum(b["saldo"] for b in banks)

        ar_conditions = [
            "f.estado = 'pendiente'",
            "EXTRACT(YEAR FROM f.fecha) = :anio",
        ]
        ar_params: dict = {"anio": anio}
        if mes:
            ar_conditions.append("EXTRACT(MONTH FROM f.fecha) = :mes")
            ar_params["mes"] = mes

        ar_where = " AND ".join(ar_conditions)
        ar_q = text(
            f"SELECT COUNT(*) AS facturas_pendientes, "
            f"COALESCE(SUM(f.monto_total), 0) AS total_por_cobrar "
            f"FROM demo_facturas_venta f WHERE {ar_where}"
        )
        ar_row = db.execute(ar_q, ar_params).fetchone()
        receivables = {
            "facturas_pendientes": ar_row[0] if ar_row else 0,
            "total_por_cobrar": float(ar_row[1]) if ar_row else 0.0,
        }

        overdue_q = text(
            "SELECT COUNT(*) AS facturas_vencidas, "
            "COALESCE(SUM(f.monto_total), 0) AS total_vencido "
            "FROM demo_facturas_venta f "
            "WHERE f.estado = 'pendiente' AND f.fecha_vencimiento < CURRENT_DATE"
        )
        overdue_row = db.execute(overdue_q).fetchone()
        receivables["facturas_vencidas"] = overdue_row[0] if overdue_row else 0
        receivables["total_vencido"] = float(overdue_row[1]) if overdue_row else 0.0

        ap_conditions = ["cpp.estado != 'pagada'"]
        ap_params: dict = {}
        if mes:
            ap_conditions.append("EXTRACT(MONTH FROM cpp.fecha_factura) = :mes")
            ap_params["mes"] = mes

        ap_where = " AND ".join(ap_conditions)
        ap_q = text(
            f"SELECT COUNT(*) AS facturas_pendientes, "
            f"COALESCE(SUM(cpp.monto_pendiente), 0) AS total_por_pagar "
            f"FROM demo_cuentas_por_pagar cpp WHERE {ap_where}"
        )
        ap_row = db.execute(ap_q, ap_params).fetchone()
        payables = {
            "facturas_pendientes": ap_row[0] if ap_row else 0,
            "total_por_pagar": float(ap_row[1]) if ap_row else 0.0,
        }

        overdue_ap_q = text(
            "SELECT COUNT(*) AS facturas_vencidas, "
            "COALESCE(SUM(cpp.monto_pendiente), 0) AS total_vencido "
            "FROM demo_cuentas_por_pagar cpp "
            "WHERE cpp.estado != 'pagada' AND cpp.fecha_vencimiento < CURRENT_DATE"
        )
        overdue_ap_row = db.execute(overdue_ap_q).fetchone()
        payables["facturas_vencidas"] = overdue_ap_row[0] if overdue_ap_row else 0
        payables["total_vencido"] = float(overdue_ap_row[1]) if overdue_ap_row else 0.0

        return {
            "anio": anio,
            "mes": mes,
            "saldos_bancarios": banks,
            "total_saldo_bancario": total_saldo_bancario,
            "cuentas_por_cobrar": receivables,
            "cuentas_por_pagar": payables,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pre-built queries: RRHH (Human Resources)
# ---------------------------------------------------------------------------

def build_employee_summary() -> dict:
    """Employee summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_employee_summary as _prod
        return _prod()

    db = SessionLocal()
    try:
        totals_q = text(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN activo THEN 1 ELSE 0 END) AS activos, "
            "SUM(CASE WHEN NOT activo THEN 1 ELSE 0 END) AS inactivos "
            "FROM demo_empleados"
        )
        row = db.execute(totals_q).fetchone()
        totals = {
            "total": row[0] if row else 0,
            "activos": row[1] if row else 0,
            "inactivos": row[2] if row else 0,
        }

        by_dept_q = text(
            "SELECT departamento, COUNT(*) AS total, "
            "SUM(CASE WHEN activo THEN 1 ELSE 0 END) AS activos "
            "FROM demo_empleados GROUP BY departamento ORDER BY total DESC"
        )
        by_dept = [
            {"departamento": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_dept_q).fetchall()
        ]

        by_location_q = text(
            "SELECT ubicacion, COUNT(*) AS total, "
            "SUM(CASE WHEN activo THEN 1 ELSE 0 END) AS activos "
            "FROM demo_empleados GROUP BY ubicacion ORDER BY total DESC"
        )
        by_location = [
            {"ubicacion": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_location_q).fetchall()
        ]

        by_shift_q = text(
            "SELECT turno, COUNT(*) AS total "
            "FROM demo_empleados WHERE activo = true "
            "GROUP BY turno ORDER BY total DESC"
        )
        by_shift = [
            {"turno": r[0], "total": r[1]}
            for r in db.execute(by_shift_q).fetchall()
        ]

        return {
            "totales": totals,
            "por_departamento": by_dept,
            "por_ubicacion": by_location,
            "por_turno": by_shift,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pre-built queries: COMPRAS INSUMOS (Supply Purchases)
# ---------------------------------------------------------------------------

def build_supply_purchases(mes: int | None = None, anio: int | None = None) -> dict:
    """Supply purchases - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_supply_purchases as _prod
        return _prod(mes=mes, anio=anio)

    # Demo fallback
    db = SessionLocal()
    try:
        conditions = ["1=1"]
        params: dict = {"anio": anio}

        totals_q = text(
            "SELECT COUNT(*) AS total_ordenes, "
            "COALESCE(SUM(o.monto_total), 0) AS total_monto "
            "FROM demo_ordenes_compra_insumos o"
        )
        row = db.execute(totals_q, params).fetchone()
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


# ---------------------------------------------------------------------------
# Pre-built queries: CONTABILIDAD (Accounting)
# ---------------------------------------------------------------------------

def build_accounting_summary(mes: int | None = None, anio: int | None = None) -> dict:
    """Accounting summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_accounting_summary as _prod
        return _prod(mes=mes, anio=anio)

    # Demo fallback
    db = SessionLocal()
    try:
        p = f"{anio}-{mes:02d}" if mes else f"{anio}-06"
        data = db.execute(
            text(
                "SELECT tipo_cuenta, SUM(saldo) as total "
                "FROM demo_balance_general WHERE periodo = :periodo "
                "GROUP BY tipo_cuenta ORDER BY tipo_cuenta"
            ),
            {"periodo": p},
        ).fetchall()
        return {
            "anio": anio,
            "mes": mes,
            "totales": {"total_asientos": 0, "total_debe": 0.0, "total_haber": 0.0},
            "por_tipo_cuenta": [
                {"tipo_cuenta": r[0], "saldo": float(r[1])} for r in data
            ],
            "balance": [],
            "cuentas_con_mayor_movimiento": [],
        }
    finally:
        db.close()

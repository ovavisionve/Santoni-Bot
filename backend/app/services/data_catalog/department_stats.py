"""Department-level statistics queries against iDempiere."""

import logging

from sqlalchemy import text

logger = logging.getLogger("santonibot.data_catalog")


def build_department_stats(session) -> dict[str, dict]:
    """Genera estadísticas específicas por departamento."""
    stats: dict[str, dict] = {}

    # ── Ventas ──
    try:
        r = session.execute(text("""
            SELECT
                COUNT(*) AS total_facturas,
                COUNT(DISTINCT c_bpartner_id) AS clientes_unicos,
                MIN(dateinvoiced) AS primera_factura,
                MAX(dateinvoiced) AS ultima_factura
            FROM adempiere.c_invoice
            WHERE issotrx = 'Y' AND docstatus IN ('CO', 'CL')
        """))
        row = r.fetchone()
        if row:
            stats["ventas"] = {
                "total_facturas_venta": row[0],
                "clientes_unicos": row[1],
                "primera_factura": str(row[2]) if row[2] else None,
                "ultima_factura": str(row[3]) if row[3] else None,
            }
    except Exception as e:
        logger.debug("Error stats ventas: %s", e)

    # ── Zonas de venta ──
    try:
        r = session.execute(text("""
            SELECT name, isactive
            FROM adempiere.c_salesregion
            WHERE isactive = 'Y'
            ORDER BY name
        """))
        zonas = [row[0] for row in r]
        stats.setdefault("ventas", {})["zonas_activas"] = zonas
    except Exception as e:
        logger.debug("Error stats zonas: %s", e)

    # ── Organizaciones activas ──
    try:
        r = session.execute(text("""
            SELECT ad_org_id, name
            FROM adempiere.ad_org
            WHERE isactive = 'Y' AND ad_org_id > 0
            ORDER BY name
        """))
        orgs = [{"id": row[0], "name": row[1]} for row in r]
        stats["organizaciones"] = orgs
    except Exception as e:
        logger.debug("Error stats organizaciones: %s", e)

    # ── Monedas ──
    try:
        r = session.execute(text("""
            SELECT c_currency_id, iso_code, cursymbol, description
            FROM adempiere.c_currency
            WHERE isactive = 'Y'
              AND c_currency_id IN (
                  SELECT DISTINCT c_currency_id FROM adempiere.c_invoice
                  WHERE docstatus IN ('CO', 'CL') LIMIT 20
              )
            ORDER BY iso_code
        """))
        monedas = [{"id": row[0], "iso_code": row[1], "symbol": row[2], "description": row[3]} for row in r]
        stats["monedas"] = monedas
    except Exception as e:
        logger.debug("Error stats monedas: %s", e)

    # ── RRHH ──
    try:
        r = session.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE isactive = 'Y') AS activos,
                COUNT(*) FILTER (WHERE isactive = 'N') AS inactivos,
                COUNT(*) AS total
            FROM adempiere.hr_employee
        """))
        row = r.fetchone()
        if row:
            stats["rrhh"] = {
                "empleados_activos": row[0],
                "empleados_inactivos": row[1],
                "total_empleados": row[2],
            }
    except Exception as e:
        logger.debug("Error stats rrhh: %s", e)

    # ── Departamentos HR ──
    try:
        r = session.execute(text("""
            SELECT name FROM adempiere.hr_department
            WHERE isactive = 'Y' ORDER BY name
        """))
        stats.setdefault("rrhh", {})["departamentos"] = [row[0] for row in r]
    except Exception as e:
        logger.debug("Error stats hr_department: %s", e)

    # ── Cargos HR ──
    try:
        r = session.execute(text("""
            SELECT name FROM adempiere.hr_job
            WHERE isactive = 'Y' ORDER BY name
        """))
        stats.setdefault("rrhh", {})["cargos"] = [row[0] for row in r]
    except Exception as e:
        logger.debug("Error stats hr_job: %s", e)

    # ── Productos más facturados ──
    try:
        r = session.execute(text("""
            SELECT p.name, COUNT(*) AS veces
            FROM adempiere.c_invoiceline il
            JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id
            JOIN adempiere.c_invoice i ON il.c_invoice_id = i.c_invoice_id
            WHERE i.docstatus IN ('CO', 'CL') AND i.issotrx = 'Y'
            GROUP BY p.name
            ORDER BY veces DESC
            LIMIT 30
        """))
        stats["productos_top"] = [{"nombre": row[0], "frecuencia": row[1]} for row in r]
    except Exception as e:
        logger.debug("Error stats productos: %s", e)

    # ── Categorías de producto ──
    try:
        r = session.execute(text("""
            SELECT name FROM adempiere.m_product_category
            WHERE isactive = 'Y' ORDER BY name
        """))
        stats["categorias_producto"] = [row[0] for row in r]
    except Exception as e:
        logger.debug("Error stats categorias: %s", e)

    # ── Proveedores (compras) ──
    try:
        r = session.execute(text("""
            SELECT COUNT(DISTINCT bp.c_bpartner_id) AS total_proveedores
            FROM adempiere.c_bpartner bp
            WHERE bp.isvendor = 'Y' AND bp.isactive = 'Y'
        """))
        row = r.fetchone()
        if row:
            stats["compras"] = {"total_proveedores_activos": row[0]}
    except Exception as e:
        logger.debug("Error stats proveedores: %s", e)

    # ── Almacenes ──
    try:
        r = session.execute(text("""
            SELECT m_warehouse_id, name
            FROM adempiere.m_warehouse
            WHERE isactive = 'Y'
            ORDER BY name
        """))
        stats["almacenes"] = [{"id": row[0], "name": row[1]} for row in r]
    except Exception as e:
        logger.debug("Error stats almacenes: %s", e)

    return stats

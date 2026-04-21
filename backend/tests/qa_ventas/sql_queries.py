"""
Queries SQL de verificación contra iDempiere (read-only) para el agente Ventas.

Basadas en la referencia autoritativa de Geovanna Antonieta Quintero Timaure
(ver `docs/SCHEMA_IDEMPIERE_VENTAS.md`). Reglas clave:

  - Ventas: `issotrx='Y'` en c_invoice / c_order
  - Moneda: c_currency_id=205 es Bs., cualquier otro ID en USD_IDS es USD
  - Vendedor: salesrep_id → ad_user (no c_bpartner)
  - Cobros: c_payment con `isreceipt='Y'`
  - Totales: `docstatus IN ('CO','CL')` (completed o closed)
  - Notas de crédito: `docbasetype='ARC'` (restar para neto)

IMPORTANTE: para que la comparación bot-vs-SQL sea justa, estas queries
usan el MISMO scope que el bot (sin excluir "demo orgs"). Si en el futuro
se descubre que ciertos ad_org_id son basura, agregarlos al filtro aquí
Y en el bot a la vez.
"""

from datetime import date
from typing import Any

from sqlalchemy import text

from app.database import IdempiereSession

# Monedas en iDempiere Santoni
VES_IDS = (205,)
USD_IDS = (100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017)


def _month_range(mes: int, anio: int) -> tuple[date, date]:
    """Primer y último día del mes (inclusive)."""
    start = date(anio, mes, 1)
    if mes == 12:
        end = date(anio + 1, 1, 1)
    else:
        end = date(anio, mes + 1, 1)
    return start, end


def total_sales_month(mes: int, anio: int, org_name: str | None = None) -> dict[str, Any]:
    """Total de ventas del mes, separado por moneda.

    SQL: suma grandtotal de c_invoice issotrx='Y', docstatus IN ('CO','CL'),
    docbasetype='ARI' en el rango de fechas. Excluye notas de crédito (ARC).
    """
    start, end = _month_range(mes, anio)
    org_clause = ""
    params: dict = {"start": start, "end": end}
    if org_name:
        org_clause = "AND o.name ILIKE :org_name "
        params["org_name"] = f"%{org_name}%"

    sql = text(f"""
        SELECT
            CASE
                WHEN i.c_currency_id IN {USD_IDS} THEN 'USD'
                WHEN i.c_currency_id = 205 THEN 'VES'
                ELSE 'OTRO'
            END AS moneda,
            COUNT(*) AS facturas,
            COALESCE(SUM(i.grandtotal), 0) AS total
        FROM adempiere.c_invoice i
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        JOIN adempiere.ad_org o ON i.ad_org_id = o.ad_org_id
        WHERE i.issotrx = 'Y'
          AND i.docstatus IN ('CO', 'CL')
          AND i.isactive = 'Y'
          AND dt.docbasetype = 'ARI'
          AND i.dateinvoiced >= :start
          AND i.dateinvoiced < :end

          {org_clause}
        GROUP BY moneda
    """)

    db = IdempiereSession()
    try:
        rows = db.execute(sql, params).fetchall()
        return {
            "label": f"Ventas {mes:02d}/{anio}" + (f" ({org_name})" if org_name else ""),
            "by_currency": {r[0]: {"facturas": r[1], "total": float(r[2])} for r in rows},
        }
    finally:
        db.close()


def top_clients_year(anio: int, limit: int = 20, org_name: str | None = None) -> dict[str, Any]:
    """Top N clientes del año por total facturado.

    Retorna lista ordenada desc por total, con nombre + total + facturas.
    """
    org_clause = ""
    params: dict = {"anio": anio, "limit": limit}
    if org_name:
        org_clause = "AND o.name ILIKE :org_name "
        params["org_name"] = f"%{org_name}%"

    sql = text(f"""
        SELECT
            bp.name AS cliente,
            COUNT(*) AS facturas,
            COALESCE(SUM(i.grandtotal), 0) AS total
        FROM adempiere.c_invoice i
        JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        JOIN adempiere.ad_org o ON i.ad_org_id = o.ad_org_id
        WHERE i.issotrx = 'Y'
          AND i.docstatus IN ('CO', 'CL')
          AND i.isactive = 'Y'
          AND dt.docbasetype = 'ARI'
          AND EXTRACT(YEAR FROM i.dateinvoiced) = :anio

          {org_clause}
        GROUP BY bp.name
        ORDER BY total DESC
        LIMIT :limit
    """)

    db = IdempiereSession()
    try:
        rows = db.execute(sql, params).fetchall()
        return {
            "label": f"Top {limit} clientes {anio}" + (f" ({org_name})" if org_name else ""),
            "clients": [
                {"cliente": r[0], "facturas": r[1], "total": float(r[2])}
                for r in rows
            ],
        }
    finally:
        db.close()


def collection_month(mes: int, anio: int, org_name: str | None = None) -> dict[str, Any]:
    """Total cobrado (pagos recibidos) en el mes por moneda.

    SQL: suma payamt de c_payment isreceipt='Y', docstatus IN ('CO','CL').
    """
    start, end = _month_range(mes, anio)
    org_clause = ""
    params: dict = {"start": start, "end": end}
    if org_name:
        org_clause = "AND o.name ILIKE :org_name "
        params["org_name"] = f"%{org_name}%"

    sql = text(f"""
        SELECT
            CASE
                WHEN p.c_currency_id IN {USD_IDS} THEN 'USD'
                WHEN p.c_currency_id = 205 THEN 'VES'
                ELSE 'OTRO'
            END AS moneda,
            COUNT(*) AS pagos,
            COALESCE(SUM(p.payamt), 0) AS total
        FROM adempiere.c_payment p
        JOIN adempiere.ad_org o ON p.ad_org_id = o.ad_org_id
        WHERE p.isreceipt = 'Y'
          AND p.docstatus IN ('CO', 'CL')
          AND p.isactive = 'Y'
          AND p.datetrx >= :start
          AND p.datetrx < :end

          {org_clause}
        GROUP BY moneda
    """)

    db = IdempiereSession()
    try:
        rows = db.execute(sql, params).fetchall()
        return {
            "label": f"Cobranza {mes:02d}/{anio}" + (f" ({org_name})" if org_name else ""),
            "by_currency": {r[0]: {"pagos": r[1], "total": float(r[2])} for r in rows},
        }
    finally:
        db.close()


def overdue_receivables_totals(org_name: str | None = None) -> dict[str, Any]:
    """Total de cuentas por cobrar vencidas por moneda.

    Usa la misma lógica que `build_overdue_receivables`:
    facturas con `ispaid='N'`, `dateinvoiced` en últimos 3 años,
    grandtotal > 100, y vencidas (fecha_venc = dateinvoiced + netdays < hoy).
    """
    org_clause = ""
    params: dict = {}
    if org_name:
        org_clause = "AND o.name ILIKE :org_name "
        params["org_name"] = f"%{org_name}%"

    sql = text(f"""
        SELECT
            CASE
                WHEN i.c_currency_id IN {USD_IDS} THEN 'USD'
                WHEN i.c_currency_id = 205 THEN 'VES'
                ELSE 'OTRO'
            END AS moneda,
            COUNT(*) AS facturas,
            COALESCE(SUM(i.grandtotal), 0) AS total_vencido
        FROM adempiere.c_invoice i
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        JOIN adempiere.ad_org o ON i.ad_org_id = o.ad_org_id
        LEFT JOIN adempiere.c_paymentterm pterm ON i.c_paymentterm_id = pterm.c_paymentterm_id
        WHERE i.issotrx = 'Y'
          AND i.docstatus IN ('CO', 'CL')
          AND i.ispaid = 'N'
          AND i.isactive = 'Y'
          AND dt.docbasetype = 'ARI'
          AND i.dateinvoiced >= (CURRENT_DATE - INTERVAL '3 years')
          AND i.grandtotal > 100
          AND (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END) < CURRENT_DATE

          {org_clause}
        GROUP BY moneda
    """)

    db = IdempiereSession()
    try:
        rows = db.execute(sql, params).fetchall()
        return {
            "label": "CxC vencidas" + (f" ({org_name})" if org_name else ""),
            "by_currency": {r[0]: {"facturas": r[1], "total_vencido": float(r[2])} for r in rows},
        }
    finally:
        db.close()


def top_overdue_clients(limit: int = 5) -> dict[str, Any]:
    """Top N morosos (clientes con más deuda vencida).

    Misma lógica que overdue_receivables_totals pero agrupado por cliente.
    Retorna top_clients con nombre + total adeudado.
    """
    sql = text(f"""
        SELECT
            bp.name AS cliente,
            COUNT(*) AS facturas,
            COALESCE(SUM(i.grandtotal), 0) AS total_adeudado
        FROM adempiere.c_invoice i
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id
        LEFT JOIN adempiere.c_paymentterm pterm ON i.c_paymentterm_id = pterm.c_paymentterm_id
        WHERE i.issotrx = 'Y'
          AND i.docstatus IN ('CO', 'CL')
          AND i.ispaid = 'N'
          AND i.isactive = 'Y'
          AND dt.docbasetype = 'ARI'
          AND i.dateinvoiced >= (CURRENT_DATE - INTERVAL '3 years')
          AND i.grandtotal > 100
          AND (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END) < CURRENT_DATE
        GROUP BY bp.name
        ORDER BY total_adeudado DESC
        LIMIT :limit
    """)

    db = IdempiereSession()
    try:
        rows = db.execute(sql, {"limit": limit}).fetchall()
        return {
            "label": f"Top {limit} morosos",
            "top_clients": [
                {"cliente": r[0], "facturas": r[1], "total_adeudado": float(r[2])}
                for r in rows
            ],
        }
    finally:
        db.close()


def total_sales_year(anio: int, org_name: str | None = None) -> dict[str, Any]:
    """Total de ventas del año entero, separado por moneda."""
    org_clause = ""
    params: dict = {"anio": anio}
    if org_name:
        org_clause = "AND o.name ILIKE :org_name "
        params["org_name"] = f"%{org_name}%"

    sql = text(f"""
        SELECT
            CASE
                WHEN i.c_currency_id IN {USD_IDS} THEN 'USD'
                WHEN i.c_currency_id = 205 THEN 'VES'
                ELSE 'OTRO'
            END AS moneda,
            COUNT(*) AS facturas,
            COALESCE(SUM(i.grandtotal), 0) AS total
        FROM adempiere.c_invoice i
        JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
        JOIN adempiere.ad_org o ON i.ad_org_id = o.ad_org_id
        WHERE i.issotrx = 'Y'
          AND i.docstatus IN ('CO', 'CL')
          AND i.isactive = 'Y'
          AND dt.docbasetype = 'ARI'
          AND EXTRACT(YEAR FROM i.dateinvoiced) = :anio

          {org_clause}
        GROUP BY moneda
    """)

    db = IdempiereSession()
    try:
        rows = db.execute(sql, params).fetchall()
        return {
            "label": f"Ventas año {anio}" + (f" ({org_name})" if org_name else ""),
            "by_currency": {r[0]: {"facturas": r[1], "total": float(r[2])} for r in rows},
        }
    finally:
        db.close()

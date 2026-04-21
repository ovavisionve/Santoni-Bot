"""
Queries SQL de verificación contra iDempiere para el agente Contabilidad.

Tablas clave:
  - fact_acct: hechos contables (asientos)
  - c_elementvalue: cuentas contables (value=código, name=nombre)
  - ad_org: organización
"""

from typing import Any

from sqlalchemy import text

from app.database import IdempiereSession


def accounting_summary_year(anio: int) -> dict[str, Any]:
    """Resumen contable del año: total débitos/créditos por tipo de cuenta."""
    sql = text("""
        SELECT
            ev.accounttype AS tipo,
            CASE ev.accounttype
                WHEN 'A' THEN 'Activo'
                WHEN 'L' THEN 'Pasivo'
                WHEN 'O' THEN 'Patrimonio'
                WHEN 'E' THEN 'Gasto'
                WHEN 'R' THEN 'Ingreso'
                ELSE ev.accounttype
            END AS tipo_nombre,
            COUNT(*) AS movimientos,
            COALESCE(SUM(fa.amtacctdr), 0) AS total_debito,
            COALESCE(SUM(fa.amtacctcr), 0) AS total_credito
        FROM adempiere.fact_acct fa
        JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id
        WHERE fa.isactive = 'Y'
          AND EXTRACT(YEAR FROM fa.dateacct) = :anio
        GROUP BY ev.accounttype
        ORDER BY total_debito DESC
    """)
    db = IdempiereSession()
    try:
        rows = db.execute(sql, {"anio": anio}).fetchall()
        return {
            "label": f"Resumen contable {anio}",
            "by_type": [
                {
                    "tipo": r[0],
                    "tipo_nombre": r[1],
                    "movimientos": r[2],
                    "total_debito": float(r[3]),
                    "total_credito": float(r[4]),
                }
                for r in rows
            ],
        }
    finally:
        db.close()


def account_detail(account_code: str, anio: int) -> dict[str, Any]:
    """Detalle de una cuenta contable por código (ej: '1.01.04')."""
    sql = text("""
        SELECT
            ev.value AS codigo,
            ev.name AS cuenta,
            COUNT(*) AS movimientos,
            COALESCE(SUM(fa.amtacctdr), 0) AS total_debito,
            COALESCE(SUM(fa.amtacctcr), 0) AS total_credito,
            COALESCE(SUM(fa.amtacctdr), 0) - COALESCE(SUM(fa.amtacctcr), 0) AS saldo
        FROM adempiere.fact_acct fa
        JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id
        WHERE fa.isactive = 'Y'
          AND ev.value LIKE :code_prefix
          AND EXTRACT(YEAR FROM fa.dateacct) = :anio
        GROUP BY ev.value, ev.name
        ORDER BY ev.value
    """)
    db = IdempiereSession()
    try:
        rows = db.execute(sql, {"code_prefix": f"{account_code}%", "anio": anio}).fetchall()
        return {
            "label": f"Cuenta {account_code} en {anio}",
            "accounts": [
                {
                    "codigo": r[0],
                    "cuenta": r[1],
                    "movimientos": r[2],
                    "debito": float(r[3]),
                    "credito": float(r[4]),
                    "saldo": float(r[5]),
                }
                for r in rows
            ],
        }
    finally:
        db.close()


def top_accounts_by_movement(anio: int, limit: int = 10) -> dict[str, Any]:
    """Top N cuentas con más movimientos contables en el año."""
    sql = text("""
        SELECT
            ev.value AS codigo,
            ev.name AS cuenta,
            COUNT(*) AS movimientos
        FROM adempiere.fact_acct fa
        JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id
        WHERE fa.isactive = 'Y'
          AND EXTRACT(YEAR FROM fa.dateacct) = :anio
        GROUP BY ev.value, ev.name
        ORDER BY movimientos DESC
        LIMIT :limit
    """)
    db = IdempiereSession()
    try:
        rows = db.execute(sql, {"anio": anio, "limit": limit}).fetchall()
        return {
            "label": f"Top {limit} cuentas {anio}",
            "accounts": [
                {"codigo": r[0], "cuenta": r[1], "movimientos": r[2]}
                for r in rows
            ],
        }
    finally:
        db.close()

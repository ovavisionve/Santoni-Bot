"""Financial query wrappers: bank balances, AR/AP."""

import logging

from sqlalchemy import text

from app.database import SessionLocal
from .core import _is_production, _rows_to_dicts, _convert_value

logger = logging.getLogger("santonibot.query_service")

def build_financial_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Financial summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_financial_summary as _prod
        return _prod(mes=mes, anio=anio, org_ids=org_ids, date_from=date_from, date_to=date_to)

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
                "organizacion": "Demo",
            }
            for r in db.execute(bank_q).fetchall()
        ]

        # Separate totals by currency
        totals_by_currency: dict[str, float] = {}
        for b in banks:
            cur = b["moneda"]
            totals_by_currency[cur] = totals_by_currency.get(cur, 0.0) + b["saldo"]

        banks_ves = [b for b in banks if b["moneda"] == "VES"]
        banks_usd = [b for b in banks if b["moneda"] == "USD"]
        banks_other = [b for b in banks if b["moneda"] not in ("VES", "USD")]

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
            "saldos_bancarios_ves": banks_ves,
            "saldos_bancarios_usd": banks_usd,
            "saldos_bancarios_otras": banks_other,
            "total_saldo_bancario": total_saldo_bancario,
            "totales_por_moneda": totals_by_currency,
            "cuentas_por_cobrar": receivables,
            "cuentas_por_pagar": payables,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pre-built queries: RRHH (Human Resources)
# ---------------------------------------------------------------------------


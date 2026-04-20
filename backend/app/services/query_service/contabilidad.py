"""Accounting query wrappers: balance sheet, account detail."""

import logging

from sqlalchemy import text

from app.database import SessionLocal
from .core import _is_production, _rows_to_dicts, _convert_value

logger = logging.getLogger("santonibot.query_service")

def build_accounting_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Accounting summary - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_accounting_summary as _prod
        return _prod(mes=mes, anio=anio, org_ids=org_ids, date_from=date_from, date_to=date_to)

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


def build_account_detail(
    account_code: str,
    date_from: str | None = None,
    date_to: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    currency_ids: list[int] | None = None,
) -> dict:
    """Detail for a specific account code - routes to demo or iDempiere."""
    if _is_production():
        from app.services.idempiere_queries import build_account_detail as _prod
        return _prod(
            account_code=account_code,
            date_from=date_from,
            date_to=date_to,
            mes=mes,
            anio=anio,
            org_ids=org_ids,
            currency_ids=currency_ids,
        )

    # Demo fallback - return minimal response
    return {
        "cuenta_codigo": account_code,
        "cuenta_nombre": f"Cuenta {account_code} (demo)",
        "tipo_cuenta": "N/A",
        "periodo": f"{date_from} al {date_to}" if date_from else f"{mes}/{anio}" if mes else str(anio),
        "moneda": "VES",
        "movimientos": 0,
        "total_debe": 0.0,
        "total_haber": 0.0,
        "saldo_inicial": 0.0,
        "saldo_final": 0.0,
        "detalle_diario": [],
    }


# ---------------------------------------------------------------------------
# Pre-built queries: INVENTARIO (Inventory / Stock)
# ---------------------------------------------------------------------------


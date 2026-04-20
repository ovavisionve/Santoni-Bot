"""Accounting queries: balance sheet, account detail."""

from sqlalchemy import text

from .common import (
    _add_currency_filter,
    _add_date_filter,
    _add_org_filter,
    _add_org_name_filter,
    _convert_value,
    _get_session,
    _rows_to_dicts,
    _ALLOC_JOIN,
    _OPEN_EXPR,
    _IDEMPIERE_DEMO_ORGS,
    _SANTONI_ORG_FILTER,
    execute_idempiere_query,
    logger,
)

# ---------------------------------------------------------------------------
# CONTABILIDAD (Accounting)
# ---------------------------------------------------------------------------

def build_accounting_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Accounting summary from iDempiere fact_acct (posted accounting facts)."""
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "fa.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "fa")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "fa.dateacct")

        where = " AND ".join(conditions)

        # Totals
        totals_q = text(
            f"SELECT COUNT(*) AS total_asientos, "
            f"COALESCE(SUM(fa.amtacctdr), 0) AS total_debe, "
            f"COALESCE(SUM(fa.amtacctcr), 0) AS total_haber "
            f"FROM adempiere.fact_acct fa WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_asientos": row[0] if row else 0,
            "total_debe": float(row[1]) if row else 0.0,
            "total_haber": float(row[2]) if row else 0.0,
        }

        # By account type (using element value)
        by_account_q = text(
            f"SELECT CASE "
            f"  WHEN ev.accounttype = 'A' THEN 'Activo' "
            f"  WHEN ev.accounttype = 'L' THEN 'Pasivo' "
            f"  WHEN ev.accounttype = 'O' THEN 'Patrimonio' "
            f"  WHEN ev.accounttype = 'R' THEN 'Ingreso' "
            f"  WHEN ev.accounttype = 'E' THEN 'Gasto' "
            f"  WHEN ev.accounttype = 'M' THEN 'Memorándum' "
            f"  ELSE ev.accounttype END AS tipo_cuenta, "
            f"COALESCE(SUM(fa.amtacctdr), 0) AS debe, "
            f"COALESCE(SUM(fa.amtacctcr), 0) AS haber, "
            f"COALESCE(SUM(fa.amtacctdr), 0) - COALESCE(SUM(fa.amtacctcr), 0) AS saldo "
            f"FROM adempiere.fact_acct fa "
            f"JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id "
            f"WHERE {where} "
            f"GROUP BY ev.accounttype ORDER BY ev.accounttype"
        )
        by_account_type = [
            {"tipo_cuenta": r[0], "debe": float(r[1]), "haber": float(r[2]), "saldo": float(r[3])}
            for r in db.execute(by_account_q, params).fetchall()
        ]

        # Balance: Assets, Liabilities, Equity
        # Use correct sign convention: A=debit-normal, L/O=credit-normal
        balance_conds = [
            "ev.accounttype IN ('A', 'L', 'O')",
            "fa.isactive = 'Y'",
        ]
        balance_params: dict = {}
        _add_org_filter(balance_conds, balance_params, org_ids, "fa")
        if anio:
            balance_conds.append("EXTRACT(YEAR FROM fa.dateacct) <= :anio")
            balance_params["anio"] = anio

        balance_where = " AND ".join(balance_conds)
        balance_q = text(
            f"SELECT CASE "
            f"  WHEN ev.accounttype = 'A' THEN 'Activo' "
            f"  WHEN ev.accounttype = 'L' THEN 'Pasivo' "
            f"  WHEN ev.accounttype = 'O' THEN 'Patrimonio' "
            f"  END AS tipo, "
            f"CASE "
            f"  WHEN ev.accounttype = 'A' THEN COALESCE(SUM(fa.amtacctdr - fa.amtacctcr), 0) "
            f"  ELSE COALESCE(SUM(fa.amtacctcr - fa.amtacctdr), 0) "
            f"END AS saldo "
            f"FROM adempiere.fact_acct fa "
            f"JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id "
            f"WHERE {balance_where} "
            f"GROUP BY ev.accounttype ORDER BY ev.accounttype"
        )
        balance = [
            {"tipo": r[0], "saldo": float(r[1])}
            for r in db.execute(balance_q, balance_params).fetchall()
        ]

        # Top accounts by movement (current period)
        top_accounts_q = text(
            f"SELECT ev.value AS codigo, ev.name AS cuenta, "
            f"COALESCE(SUM(fa.amtacctdr), 0) AS debe, "
            f"COALESCE(SUM(fa.amtacctcr), 0) AS haber "
            f"FROM adempiere.fact_acct fa "
            f"JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id "
            f"WHERE {where} "
            f"GROUP BY ev.value, ev.name "
            f"ORDER BY (COALESCE(SUM(fa.amtacctdr), 0) + COALESCE(SUM(fa.amtacctcr), 0)) DESC "
            f"LIMIT 20"
        )
        top_accounts = [
            {"codigo": r[0], "cuenta": r[1], "debe": float(r[2]), "haber": float(r[3])}
            for r in db.execute(top_accounts_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "mes": mes,
            "totales": totals,
            "por_tipo_cuenta": by_account_type,
            "balance": balance,
            "cuentas_con_mayor_movimiento": top_accounts,
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
    """Query detail for a specific account code from fact_acct.

    Parameters:
        account_code: Account code like '2.01.01.10'
        date_from: Start date 'YYYY-MM-DD' (overrides mes/anio if provided)
        date_to: End date 'YYYY-MM-DD' (overrides mes/anio if provided)
        mes: Month number (used if date_from/to not provided)
        anio: Year (used if date_from/to not provided)
        org_ids: List of allowed organization IDs
        currency_ids: List of iDempiere c_currency_id values. Filters fact_acct entries.

    Returns dict with account info, period totals, opening/closing balance.

    IMPORTANT - Balance sign convention:
    - Debit-normal accounts (A=Activo, E=Gasto): saldo = debe - haber
    - Credit-normal accounts (L=Pasivo, O=Patrimonio, R=Ingreso): saldo = haber - debe
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        # 1. Find the account by code
        acct_q = text(
            "SELECT ev.c_elementvalue_id, ev.value, ev.name, ev.accounttype "
            "FROM adempiere.c_elementvalue ev "
            "WHERE ev.value = :code AND ev.isactive = 'Y' "
            "LIMIT 1"
        )
        acct_row = db.execute(acct_q, {"code": account_code}).fetchone()
        if not acct_row:
            return {
                "error": f"Cuenta '{account_code}' no encontrada en el plan de cuentas",
                "cuenta_codigo": account_code,
            }

        acct_id = acct_row[0]
        acct_name = acct_row[2]
        acct_type = acct_row[3]  # A=Activo, L=Pasivo, O=Patrimonio, R=Ingreso, E=Gasto

        # Determine balance sign: credit-normal accounts flip the sign
        # L (Pasivo), O (Patrimonio), R (Ingreso) → saldo = haber - debe
        # A (Activo), E (Gasto) → saldo = debe - haber
        is_credit_normal = acct_type in ("L", "O", "R")

        # 2. Build date conditions
        period_conditions = ["fa.isactive = 'Y'", "fa.account_id = :acct_id"]
        period_params: dict = {"acct_id": acct_id}
        _add_org_filter(period_conditions, period_params, org_ids, "fa")
        _add_currency_filter(period_conditions, period_params, currency_ids, "fa")

        if date_from and date_to:
            period_conditions.append("fa.dateacct >= :date_from")
            period_conditions.append("fa.dateacct <= :date_to")
            period_params["date_from"] = date_from
            period_params["date_to"] = date_to
            period_label = f"{date_from} al {date_to}"
        elif mes and anio:
            period_conditions.append("EXTRACT(YEAR FROM fa.dateacct) = :anio")
            period_conditions.append("EXTRACT(MONTH FROM fa.dateacct) = :mes")
            period_params["anio"] = anio
            period_params["mes"] = mes
            period_label = f"{mes:02d}/{anio}"
        elif anio:
            period_conditions.append("EXTRACT(YEAR FROM fa.dateacct) = :anio")
            period_params["anio"] = anio
            period_label = f"Año {anio}"
        else:
            period_label = "Todos los períodos"

        period_where = " AND ".join(period_conditions)

        # 3. Period totals (debit/credit in the period)
        totals_q = text(
            f"SELECT COUNT(*) AS movimientos, "
            f"COALESCE(SUM(fa.amtacctdr), 0) AS total_debe, "
            f"COALESCE(SUM(fa.amtacctcr), 0) AS total_haber "
            f"FROM adempiere.fact_acct fa WHERE {period_where}"
        )
        row = db.execute(totals_q, period_params).fetchone()
        movimientos = row[0] if row else 0
        total_debe = float(row[1]) if row else 0.0
        total_haber = float(row[2]) if row else 0.0

        # 4. Opening balance (all movements BEFORE the period start)
        # Use the correct sign convention based on account type
        saldo_sql_expr = (
            "COALESCE(SUM(fa.amtacctcr - fa.amtacctdr), 0)"
            if is_credit_normal
            else "COALESCE(SUM(fa.amtacctdr - fa.amtacctcr), 0)"
        )

        saldo_inicial = 0.0
        if date_from:
            opening_conds = [
                "fa.isactive = 'Y'",
                "fa.account_id = :acct_id",
                "fa.dateacct < :date_from",
            ]
            opening_params: dict = {"acct_id": acct_id, "date_from": date_from}
            _add_org_filter(opening_conds, opening_params, org_ids, "fa")
            _add_currency_filter(opening_conds, opening_params, currency_ids, "fa")
            opening_q = text(
                f"SELECT {saldo_sql_expr} "
                f"FROM adempiere.fact_acct fa "
                f"WHERE {' AND '.join(opening_conds)}"
            )
            r = db.execute(opening_q, opening_params).fetchone()
            saldo_inicial = float(r[0]) if r else 0.0
        elif mes and anio:
            opening_conds = [
                "fa.isactive = 'Y'",
                "fa.account_id = :acct_id",
                "fa.dateacct < :opening_date",
            ]
            opening_params2: dict = {"acct_id": acct_id, "opening_date": f"{anio}-{mes:02d}-01"}
            _add_org_filter(opening_conds, opening_params2, org_ids, "fa")
            _add_currency_filter(opening_conds, opening_params2, currency_ids, "fa")
            opening_q = text(
                f"SELECT {saldo_sql_expr} "
                f"FROM adempiere.fact_acct fa "
                f"WHERE {' AND '.join(opening_conds)}"
            )
            r = db.execute(opening_q, opening_params2).fetchone()
            saldo_inicial = float(r[0]) if r else 0.0

        # Closing balance: apply period movements with correct sign
        if is_credit_normal:
            saldo_final = saldo_inicial + total_haber - total_debe
        else:
            saldo_final = saldo_inicial + total_debe - total_haber

        # 5. Daily breakdown with running balance
        daily_q = text(
            f"SELECT fa.dateacct::date AS fecha, "
            f"COALESCE(SUM(fa.amtacctdr), 0) AS debe, "
            f"COALESCE(SUM(fa.amtacctcr), 0) AS haber, "
            f"COUNT(*) AS asientos "
            f"FROM adempiere.fact_acct fa WHERE {period_where} "
            f"GROUP BY fa.dateacct::date ORDER BY fa.dateacct::date "
            f"LIMIT 31"
        )
        daily_rows = db.execute(daily_q, period_params).fetchall()
        daily = []
        running_balance = saldo_inicial
        for r in daily_rows:
            debe_dia = float(r[1])
            haber_dia = float(r[2])
            if is_credit_normal:
                running_balance += haber_dia - debe_dia
            else:
                running_balance += debe_dia - haber_dia
            daily.append({
                "fecha": str(r[0]),
                "debe": debe_dia,
                "haber": haber_dia,
                "asientos": r[3],
                "saldo": round(running_balance, 2),
            })

        # 6. Currency info
        currency_name = "VES"
        if currency_ids:
            # Show label based on the first currency ID
            curr_q = text(
                "SELECT c.iso_code FROM adempiere.c_currency c "
                "WHERE c.c_currency_id = :cid"
            )
            curr_row = db.execute(curr_q, {"cid": currency_ids[0]}).fetchone()
            if curr_row:
                currency_name = curr_row[0]
        else:
            curr_q = text(
                "SELECT DISTINCT c.iso_code FROM adempiere.fact_acct fa "
                "JOIN adempiere.c_currency c ON fa.c_currency_id = c.c_currency_id "
                "WHERE fa.account_id = :acct_id AND fa.isactive = 'Y' LIMIT 3"
            )
            curr_rows = db.execute(curr_q, {"acct_id": acct_id}).fetchall()
            if curr_rows:
                currency_name = ", ".join(r[0] for r in curr_rows)

        acct_type_labels = {
            "A": "Activo", "L": "Pasivo", "O": "Patrimonio",
            "R": "Ingreso", "E": "Gasto", "M": "Memorándum",
        }
        naturaleza = "Crédito" if is_credit_normal else "Débito"

        return {
            "cuenta_codigo": account_code,
            "cuenta_nombre": acct_name,
            "tipo_cuenta": acct_type_labels.get(acct_type, acct_type),
            "naturaleza": naturaleza,
            "periodo": period_label,
            "moneda": currency_name,
            "movimientos": movimientos,
            "total_debe": total_debe,
            "total_haber": total_haber,
            "saldo_inicial": round(saldo_inicial, 2),
            "saldo_final": round(saldo_final, 2),
            "detalle_diario": daily,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------

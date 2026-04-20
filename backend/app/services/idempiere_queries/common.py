"""Shared helpers, constants and utilities for iDempiere queries.

Used by all domain modules (ventas, rrhh, finanzas, etc.).

Includes:
  - Historical data routing (_get_session, _is_before_cutoff)
  - Row conversion helpers (_convert_value, _rows_to_dicts)
  - Demo org blacklist (_IDEMPIERE_DEMO_ORGS, _SANTONI_ORG_FILTER)
  - Filter builders (_add_org_filter, _add_org_name_filter, _add_currency_filter,
    _add_date_filter, _add_product_search_filter)
  - Allocation JOIN for open amount calculation (_ALLOC_JOIN, _OPEN_EXPR)
  - execute_idempiere_query
"""

import logging
import re
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import text

from app.database import IdempiereSession, HistoricalSession

logger = logging.getLogger("santonibot.idempiere_queries")


# ---------------------------------------------------------------------------
# Historical data routing
# ---------------------------------------------------------------------------

def _is_historical_enabled() -> bool:
    try:
        from app.config import get_settings
        s = get_settings()
        return s.historical_data_enabled
    except Exception:
        return False


def _get_cutoff_date() -> str:
    try:
        from app.config import get_settings
        cutoff = get_settings().historical_data_cutoff
        if cutoff and cutoff.lower() != "today":
            return cutoff
    except Exception:
        pass
    return date.today().isoformat()


def _is_before_cutoff(
    date_from: str | None = None,
    date_to: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
) -> bool:
    cutoff = _get_cutoff_date()
    try:
        cutoff_date = datetime.strptime(cutoff, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False

    if date_to:
        try:
            end = datetime.strptime(str(date_to), "%Y-%m-%d").date()
            return end < cutoff_date
        except (ValueError, TypeError):
            return False

    if mes and anio:
        if mes == 12:
            month_end = date(anio + 1, 1, 1)
        else:
            month_end = date(anio, mes + 1, 1)
        return month_end <= cutoff_date

    if anio and not mes:
        year_end = date(anio + 1, 1, 1)
        return year_end <= cutoff_date

    return False


def _get_session(
    date_from: str | None = None,
    date_to: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
):
    if _is_historical_enabled() and _is_before_cutoff(date_from, date_to, mes, anio):
        logger.info(
            "Using HISTORICAL (local) DB for date_from=%s, date_to=%s, mes=%s, anio=%s",
            date_from, date_to, mes, anio,
        )
        return HistoricalSession()
    return IdempiereSession()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _convert_value(val):
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, date):
        return val.isoformat()
    return val


def _rows_to_dicts(rows, columns) -> list[dict]:
    return [
        {col: _convert_value(row[i]) for i, col in enumerate(columns)}
        for row in rows
    ]


_IDEMPIERE_DEMO_ORGS = (
    "HQ", "Fertilizer", "Furniture",
    "Store Central", "Store East", "Store North", "Store South", "Store West",
    "Stores", "*",
)
_SANTONI_ORG_FILTER = (
    "{alias}.ad_org_id IN ("
    "SELECT ad_org_id FROM adempiere.ad_org WHERE isactive = 'Y' AND "
    + " AND ".join(f"name NOT ILIKE '{n}'" for n in _IDEMPIERE_DEMO_ORGS)
    + ")"
)


def _add_org_filter(
    conditions: list[str],
    params: dict,
    org_ids: list[int] | None,
    table_alias: str,
    exclude_demo: bool = False,
) -> None:
    if org_ids:
        placeholders = ", ".join(f":org_{i}" for i in range(len(org_ids)))
        conditions.append(f"{table_alias}.ad_org_id IN ({placeholders})")
        for i, org_id in enumerate(org_ids):
            params[f"org_{i}"] = org_id
    elif exclude_demo:
        conditions.append(_SANTONI_ORG_FILTER.format(alias=table_alias))


def _add_org_name_filter(
    conditions: list[str],
    params: dict,
    org_name: str | list[str] | None,
    table_alias: str,
) -> None:
    if not org_name:
        return
    patterns = [org_name] if isinstance(org_name, str) else list(org_name)
    patterns = [p for p in patterns if p]
    if not patterns:
        return
    like_clauses = []
    for i, pat in enumerate(patterns):
        key = f"org_name_filter_{i}"
        like_clauses.append(f"o.name ILIKE :{key}")
        params[key] = f"%{pat}%"
    conditions.append(
        f"{table_alias}.ad_org_id IN ("
        f"SELECT o.ad_org_id FROM adempiere.ad_org o "
        f"WHERE {' OR '.join(like_clauses)})"
    )


def _add_currency_filter(
    conditions: list[str],
    params: dict,
    currency_ids: list[int] | None,
    table_alias: str,
) -> None:
    if currency_ids:
        placeholders = ", ".join(f":cur_{i}" for i in range(len(currency_ids)))
        conditions.append(f"{table_alias}.c_currency_id IN ({placeholders})")
        for i, cid in enumerate(currency_ids):
            params[f"cur_{i}"] = cid


def _add_date_filter(
    conditions: list[str],
    params: dict,
    date_from: str | None,
    date_to: str | None,
    mes: int | None,
    anio: int | None,
    date_column: str,
) -> None:
    logger.info(
        "Date filter: date_from=%s, date_to=%s, mes=%s, anio=%s, col=%s",
        date_from, date_to, mes, anio, date_column,
    )
    if date_from and date_to:
        conditions.append(f"{date_column} >= :date_from")
        conditions.append(f"{date_column} <= :date_to")
        params["date_from"] = date_from
        params["date_to"] = date_to
        return

    if mes and anio:
        if mes == 12:
            next_month_year = anio + 1
            next_month = 1
        else:
            next_month_year = anio
            next_month = mes + 1
        conditions.append(f"{date_column} >= :perf_date_from")
        conditions.append(f"{date_column} < :perf_date_to_excl")
        params["perf_date_from"] = f"{anio}-{mes:02d}-01"
        params["perf_date_to_excl"] = f"{next_month_year}-{next_month:02d}-01"
        return

    if anio and not mes:
        conditions.append(f"{date_column} >= :perf_date_from")
        conditions.append(f"{date_column} < :perf_date_to_excl")
        params["perf_date_from"] = f"{anio}-01-01"
        params["perf_date_to_excl"] = f"{anio + 1}-01-01"
        return

    if mes and not anio:
        conditions.append(f"EXTRACT(MONTH FROM {date_column}) = :mes")
        params["mes"] = mes


# ---------------------------------------------------------------------------
# Invoice open amount
# ---------------------------------------------------------------------------

_ALLOC_JOIN = (
    "LEFT JOIN ("
    "SELECT al.c_invoice_id, "
    "SUM(COALESCE(al.amount, 0) + COALESCE(al.discountamt, 0) + COALESCE(al.writeoffamt, 0)) AS paid "
    "FROM adempiere.c_allocationline al "
    "JOIN adempiere.c_allocationhdr ah ON al.c_allocationhdr_id = ah.c_allocationhdr_id "
    "WHERE ah.isactive = 'Y' AND ah.docstatus IN ('CO', 'CL') "
    "AND ah.dateacct >= (CURRENT_DATE - INTERVAL '3 years') "
    "GROUP BY al.c_invoice_id"
    ") alloc ON alloc.c_invoice_id = i.c_invoice_id "
)

_OPEN_EXPR = "(i.grandtotal - COALESCE(alloc.paid, 0))"


# ---------------------------------------------------------------------------
# Product search helpers
# ---------------------------------------------------------------------------

_PRODUCT_STOP_WORDS = {
    'de', 'del', 'las', 'los', 'en', 'el', 'la', 'para', 'por',
    'con', 'sin', 'un', 'una', 'al', 'que', 'se', 'ha', 'y',
}


def _normalize_search_word(w: str) -> str:
    _accent_map = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u',
    }
    normalized = ''.join(_accent_map.get(c, c) for c in w.lower())
    if len(normalized) > 3 and normalized.endswith('s') and normalized[-2] in 'aeiou':
        normalized = normalized[:-1]
    if len(normalized) > 4 and normalized.endswith('es') and normalized[-3] not in 'aeiou':
        normalized = normalized[:-2]
    return normalized


def _add_product_search_filter(
    conditions: list[str],
    params: dict,
    product_search: str,
    prefix: str = "prod",
) -> None:
    if re.search(r'[A-Za-z]{2,}-[A-Za-z]{2,}-\d+', product_search):
        params[f"{prefix}_search"] = f"%{product_search}%"
        conditions.append(
            f"(p.name ILIKE :{prefix}_search OR p.value ILIKE :{prefix}_search)"
        )
        return

    words = [
        w for w in product_search.lower().split()
        if w not in _PRODUCT_STOP_WORDS and len(w) >= 2
    ]

    if not words:
        params[f"{prefix}_search"] = f"%{product_search}%"
        conditions.append(
            f"(p.name ILIKE :{prefix}_search OR p.value ILIKE :{prefix}_search)"
        )
        return

    clean_words = [_normalize_search_word(w) for w in words]
    original_words = list(words)

    word_conds = []
    for i, w in enumerate(clean_words):
        pk = f"{prefix}_w{i}"
        params[pk] = f"%{w}%"
        cond = f"(p.name ILIKE :{pk} OR p.value ILIKE :{pk})"
        if original_words[i] != w:
            pk_orig = f"{prefix}_wo{i}"
            params[pk_orig] = f"%{original_words[i]}%"
            cond = f"(p.name ILIKE :{pk} OR p.value ILIKE :{pk} OR p.name ILIKE :{pk_orig} OR p.value ILIKE :{pk_orig})"
        word_conds.append(cond)

    if len(word_conds) <= 2:
        conditions.append(f"({' AND '.join(word_conds)})")
    else:
        conditions.append(
            f"({word_conds[0]} AND ({' OR '.join(word_conds[1:])}))"
        )


def execute_idempiere_query(query: str, params: dict | None = None) -> list[dict]:
    q = query.strip().rstrip(";")
    if not q.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed on iDempiere.")

    db = IdempiereSession()
    try:
        result = db.execute(text(q), params or {})
        columns = list(result.keys())
        rows = result.fetchall()
        return _rows_to_dicts(rows, columns)
    finally:
        db.close()

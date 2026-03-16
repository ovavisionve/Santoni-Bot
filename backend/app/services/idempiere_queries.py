"""
iDempiere query functions for production environment.
All queries target the adempiere schema on PostgreSQL 13 (192.168.1.73).
User 'ova' has SELECT-only permissions.

IMPORTANT: These queries are based on standard iDempiere table structure.
They need validation after connecting to Santoni's actual iDempiere instance
(Phase 4 of deployment). Column names and custom tables may differ.

Convention:
- issotrx = 'Y' → Sales transaction (venta)
- issotrx = 'N' → Purchase transaction (compra)
- docstatus IN ('CO', 'CL') → Completed or Closed document
- isactive = 'Y' → Active record

Historical data routing (Mar 2026+):
- When HISTORICAL_DATA_ENABLED=true, queries for dates before the cutoff
  are routed to the local DB (adempiere schema) instead of iDempiere.
- This avoids hitting iDempiere for historical data.
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
    """Check if historical data routing is enabled."""
    try:
        from app.config import get_settings
        s = get_settings()
        return s.historical_data_enabled
    except Exception:
        return False


def _get_cutoff_date() -> str:
    """Get the cutoff date string (YYYY-MM-DD).

    If HISTORICAL_DATA_CUTOFF is 'today' or empty, uses today's date.
    This means only queries for TODAY go to iDempiere; everything else
    is served from the local historical cache.
    """
    try:
        from app.config import get_settings
        cutoff = get_settings().historical_data_cutoff
        if cutoff and cutoff.lower() != "today":
            return cutoff
    except Exception:
        pass
    # Default: today's date (only today's queries go to iDempiere)
    return date.today().isoformat()


def _is_before_cutoff(
    date_from: str | None = None,
    date_to: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
) -> bool:
    """Determine if the requested date range falls entirely before the cutoff.

    Returns True only if ALL requested data is before the cutoff date.
    Returns False if:
    - No date filters specified (defaults to current/live data)
    - Date range extends beyond cutoff
    - Only year specified and it's the cutoff year
    """
    cutoff = _get_cutoff_date()
    try:
        cutoff_date = datetime.strptime(cutoff, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False

    # Explicit date range
    if date_to:
        try:
            end = datetime.strptime(str(date_to), "%Y-%m-%d").date()
            return end < cutoff_date
        except (ValueError, TypeError):
            return False

    # Month + year
    if mes and anio:
        # End of the specified month
        if mes == 12:
            month_end = date(anio + 1, 1, 1)
        else:
            month_end = date(anio, mes + 1, 1)
        return month_end <= cutoff_date

    # Only year
    if anio and not mes:
        year_end = date(anio + 1, 1, 1)
        return year_end <= cutoff_date

    # No date filters → use live iDempiere
    return False


def _get_session(
    date_from: str | None = None,
    date_to: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
):
    """Get the appropriate DB session based on date range.

    Returns HistoricalSession (local DB) for queries entirely before cutoff,
    IdempiereSession (live) otherwise.
    """
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


def _add_org_filter(
    conditions: list[str],
    params: dict,
    org_ids: list[int] | None,
    table_alias: str,
) -> None:
    """Add ad_org_id IN (...) filter if org_ids is provided.
    Modifies conditions and params in place."""
    if org_ids:
        placeholders = ", ".join(f":org_{i}" for i in range(len(org_ids)))
        conditions.append(f"{table_alias}.ad_org_id IN ({placeholders})")
        for i, org_id in enumerate(org_ids):
            params[f"org_{i}"] = org_id


def _add_org_name_filter(
    conditions: list[str],
    params: dict,
    org_name: str | None,
    table_alias: str,
) -> None:
    """Add org name ILIKE filter via a subquery on ad_org.
    E.g. org_name='inpromaiz' → i.ad_org_id IN (SELECT ad_org_id FROM ad_org WHERE name ILIKE '%inpromaiz%')"""
    if org_name:
        conditions.append(
            f"{table_alias}.ad_org_id IN ("
            f"SELECT o.ad_org_id FROM adempiere.ad_org o "
            f"WHERE o.name ILIKE :org_name_filter)"
        )
        params["org_name_filter"] = f"%{org_name}%"


# Internal Santoni group organizations that should be excluded from
# producer purchase analysis.  They have codigoproductor set in iDempiere
# (self-purchases / internal transfers) but are not real external producers.
_INTERNAL_ORG_NAMES = [
    "inproa santoni",
    "inpromaiz",
    "santoni service",
    "agropecuaria r.r",
    "aga agricola",
    "agroinproa",
    "inversiones aga",
    "agro import",
]


def _add_exclude_internal_orgs_filter(
    conditions: list[str],
    params: dict,
    table_alias: str = "bp",
) -> None:
    """Exclude internal Santoni group organizations from producer queries."""
    placeholders = ", ".join(f":_intorg_{i}" for i in range(len(_INTERNAL_ORG_NAMES)))
    conditions.append(f"LOWER({table_alias}.name) NOT IN ({placeholders})")
    for i, name in enumerate(_INTERNAL_ORG_NAMES):
        params[f"_intorg_{i}"] = name


def _add_currency_filter(
    conditions: list[str],
    params: dict,
    currency_ids: list[int] | None,
    table_alias: str,
) -> None:
    """Add c_currency_id IN (...) filter if currency_ids is provided.
    Supports multiple IDs because Santoni uses several currency entries for dollars.
    Modifies conditions and params in place."""
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
    """Add date filters. date_from/date_to override mes/anio when both provided."""
    logger.info(
        "Date filter: date_from=%s, date_to=%s, mes=%s, anio=%s, col=%s",
        date_from, date_to, mes, anio, date_column,
    )
    if date_from and date_to:
        conditions.append(f"{date_column} >= :date_from")
        conditions.append(f"{date_column} <= :date_to")
        params["date_from"] = date_from
        params["date_to"] = date_to
    else:
        if anio:
            conditions.append(f"EXTRACT(YEAR FROM {date_column}) = :anio")
            params["anio"] = anio
        if mes:
            conditions.append(f"EXTRACT(MONTH FROM {date_column}) = :mes")
            params["mes"] = mes


_PRODUCT_STOP_WORDS = {
    'de', 'del', 'las', 'los', 'en', 'el', 'la', 'para', 'por',
    'con', 'sin', 'un', 'una', 'al', 'que', 'se', 'ha', 'y',
}


def _normalize_search_word(w: str) -> str:
    """Normalize a Spanish word for search: remove accents, de-pluralize."""
    # Remove accents
    _accent_map = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u',
    }
    normalized = ''.join(_accent_map.get(c, c) for c in w.lower())
    # De-pluralize: strip trailing 's' for common Spanish plurals
    if len(normalized) > 3 and normalized.endswith('s') and normalized[-2] in 'aeiou':
        normalized = normalized[:-1]
    # Also handle -es plurals (e.g. laminas -> lamina already handled, but cajas -> caja)
    if len(normalized) > 4 and normalized.endswith('es') and normalized[-3] not in 'aeiou':
        normalized = normalized[:-2]
    return normalized


def _add_product_search_filter(
    conditions: list[str],
    params: dict,
    product_search: str,
    prefix: str = "prod",
) -> None:
    """Add flexible product search conditions on p.name / p.value.

    For product codes (e.g. REP-LAMI-0037), uses exact substring ILIKE.
    For text searches, splits into words and uses a flexible strategy:
    - If 1-2 words: ALL must match (AND)
    - If 3+ words: at least 2 must match (OR groups)
    With accent normalization and de-pluralization.
    """
    # Product code: exact substring match
    if re.search(r'[A-Za-z]{2,}-[A-Za-z]{2,}-\d+', product_search):
        params[f"{prefix}_search"] = f"%{product_search}%"
        conditions.append(
            f"(p.name ILIKE :{prefix}_search OR p.value ILIKE :{prefix}_search)"
        )
        return

    # Text search: split into meaningful words
    words = [
        w for w in product_search.lower().split()
        if w not in _PRODUCT_STOP_WORDS and len(w) >= 2
    ]

    if not words:
        # Fallback to exact substring
        params[f"{prefix}_search"] = f"%{product_search}%"
        conditions.append(
            f"(p.name ILIKE :{prefix}_search OR p.value ILIKE :{prefix}_search)"
        )
        return

    # Normalize words (remove accents + de-pluralize)
    clean_words = [_normalize_search_word(w) for w in words]
    # Also keep original words as alternates for ILIKE
    original_words = list(words)

    word_conds = []
    for i, w in enumerate(clean_words):
        pk = f"{prefix}_w{i}"
        # Use the normalized word for matching
        params[pk] = f"%{w}%"
        cond = f"(p.name ILIKE :{pk} OR p.value ILIKE :{pk})"
        # Also try the original word if different
        if original_words[i] != w:
            pk_orig = f"{prefix}_wo{i}"
            params[pk_orig] = f"%{original_words[i]}%"
            cond = f"(p.name ILIKE :{pk} OR p.value ILIKE :{pk} OR p.name ILIKE :{pk_orig} OR p.value ILIKE :{pk_orig})"
        word_conds.append(cond)

    if len(word_conds) <= 2:
        # For 1-2 words: ALL must match
        conditions.append(f"({' AND '.join(word_conds)})")
    else:
        # For 3+ words: require first word + at least one other
        # This avoids "cajas de carton para cereales" failing because
        # one word doesn't match exactly
        conditions.append(
            f"({word_conds[0]} AND ({' OR '.join(word_conds[1:])}))"
        )


def execute_idempiere_query(query: str, params: dict | None = None) -> list[dict]:
    """Execute a read-only query against iDempiere.
    The connection is enforced read-only at the database level."""
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


# ---------------------------------------------------------------------------
# VENTAS (Sales)
# ---------------------------------------------------------------------------

# Mapping of sales zones (c_salesregion) to macro regions for Venezuela
# This groups individual states/zones into broader commercial regions
_ZONE_TO_REGION = {
    "portuguesa": "Llanos",
    "barinas": "Llanos",
    "guanare": "Llanos",
    "cojedes": "Llanos",
    "apure": "Llanos",
    "lara": "Centro-Occidente",
    "yaracuy": "Centro-Occidente",
    "falcon": "Centro-Occidente",
    "carabobo": "Centro",
    "aragua": "Centro",
    "valencia": "Centro",
    "caracas": "Capital",
    "miranda": "Capital",
    "vargas": "Capital",
    "la guaira": "Capital",
    "zulia": "Occidente",
    "maracaibo": "Occidente",
    "cabimas": "Occidente",
    "trujillo": "Andes",
    "merida": "Andes",
    "mérida": "Andes",
    "tachira": "Andes",
    "táchira": "Andes",
    "san cristobal": "Andes",
    "san cristóbal": "Andes",
    "santa barbara": "Occidente",
    "margarita": "Oriente",
    "oriente": "Oriente",
    "anzoategui": "Oriente",
    "anzoátegui": "Oriente",
    "sucre": "Oriente",
    "monagas": "Oriente",
    "bolivar": "Guayana",
    "bolívar": "Guayana",
    "delta amacuro": "Guayana",
    "amazonas": "Guayana",
}


def _region_case_sql() -> str:
    """Build a SQL CASE expression that maps zone names to macro regions."""
    cases = []
    # Group by region to reduce SQL size
    region_zones: dict[str, list[str]] = {}
    for zone, region in _ZONE_TO_REGION.items():
        region_zones.setdefault(region, []).append(zone)

    for region, zones in region_zones.items():
        like_conds = " OR ".join(f"LOWER(cz.zona_name) LIKE '%{z}%'" for z in zones)
        cases.append(f"WHEN ({like_conds}) THEN '{region}'")

    return f"CASE {' '.join(cases)} ELSE 'Otra' END"


def _currency_label(alias: str = "i") -> str:
    """SQL CASE expression that groups Santoni's multiple USD currency entries
    into a single 'USD' label and VES into 'Bs.' for display."""
    return (
        f"CASE WHEN {alias}.c_currency_id = 205 THEN 'Bs.' "
        f"WHEN {alias}.c_currency_id IN "
        f"(100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) "
        f"THEN 'USD' ELSE 'Otro' END"
    )


def _add_salesrep_filter(conditions: list, params: dict, salesrep_id: int | None, alias: str = "i"):
    """Add salesrep_id filter to conditions if provided."""
    if salesrep_id:
        conditions.append(f"{alias}.salesrep_id = :salesrep_id")
        params["salesrep_id"] = salesrep_id


def build_sales_summary(
    zona: str | None = None,
    vendedor: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> dict:
    """Sales summary from iDempiere c_invoice (issotrx='Y').

    Excludes credit notes (ARC) from the main totals and shows them
    separately so the user sees net sales = facturas - notas de crédito.
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_salesrep_filter(conditions, params, salesrep_id, "i")
        _add_currency_filter(conditions, params, currency_ids, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")

        if vendedor:
            conditions.append("COALESCE(sr.name, '') ILIKE :vendedor")
            params["vendedor"] = f"%{vendedor}%"
        if zona:
            conditions.append("COALESCE(cz.zona_name, '') ILIKE :zona")
            params["zona"] = f"%{zona}%"

        where = " AND ".join(conditions)

        # CTE: one zone per client (avoids JOIN multiplication from
        # c_bpartner_location having multiple rows per client)
        zone_cte = (
            "WITH client_zone AS ("
            "SELECT DISTINCT ON (bpl.c_bpartner_id) "
            "bpl.c_bpartner_id, sreg.name AS zona_name "
            "FROM adempiere.c_bpartner_location bpl "
            "LEFT JOIN adempiere.c_salesregion sreg "
            "ON bpl.c_salesregion_id = sreg.c_salesregion_id "
            "WHERE bpl.isactive = 'Y' "
            "ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC) "
        )
        joins = (
            "LEFT JOIN adempiere.c_bpartner sr "
            "ON i.salesrep_id = sr.c_bpartner_id "
            "LEFT JOIN client_zone cz "
            "ON i.c_bpartner_id = cz.c_bpartner_id "
            "JOIN adempiere.c_doctype dt "
            "ON i.c_doctypetarget_id = dt.c_doctype_id "
        )

        # Only regular invoices (ARI), exclude credit notes (ARC)
        where_invoices = f"{where} AND dt.docbasetype = 'ARI'"
        where_credit = f"{where} AND dt.docbasetype = 'ARC'"

        # Totals (only invoices)
        totals_q = text(
            f"{zone_cte}"
            f"SELECT COUNT(*) AS total_facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_facturado, "
            f"COALESCE(SUM(i.totallines), 0) AS total_neto, "
            f"COALESCE(SUM(i.grandtotal - i.totallines), 0) AS total_iva "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where_invoices}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_facturas": row[0] if row else 0,
            "total_facturado": float(row[1]) if row else 0.0,
            "total_neto": float(row[2]) if row else 0.0,
            "total_iva": float(row[3]) if row else 0.0,
        }

        # Credit notes totals
        credit_q = text(
            f"{zone_cte}"
            f"SELECT COUNT(*) AS total_nc, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_nc_monto "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where_credit}"
        )
        cn_row = db.execute(credit_q, params).fetchone()
        notas_credito = {
            "total_notas_credito": cn_row[0] if cn_row else 0,
            "monto_notas_credito": float(cn_row[1]) if cn_row else 0.0,
        }
        totals["total_notas_credito"] = notas_credito["total_notas_credito"]
        totals["monto_notas_credito"] = notas_credito["monto_notas_credito"]
        totals["venta_neta"] = totals["total_facturado"] - notas_credito["monto_notas_credito"]

        # By sales region (zona) - only invoices, net of credit notes
        by_zone_q = text(
            f"{zone_cte}"
            f"SELECT COALESCE(cz.zona_name, 'Sin Zona') AS zona, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_bruto, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS total_nc, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS total_neto "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY cz.zona_name ORDER BY total_neto DESC"
        )
        by_zone = [
            {"zona": r[0], "facturas": r[1], "total_bruto": float(r[2]),
             "notas_credito": float(r[3]), "total": float(r[4])}
            for r in db.execute(by_zone_q, params).fetchall()
        ]

        # By macro region (groups zones into Llanos, Centro, Occidente, etc.)
        region_case = _region_case_sql()
        by_region_q = text(
            f"{zone_cte}"
            f"SELECT {region_case} AS region, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY {region_case} ORDER BY total DESC"
        )
        by_region = [
            {"region": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_region_q, params).fetchall()
        ]

        # By distributor (salesrep_id tracks distributors, not internal salespeople)
        by_distributor_q = text(
            f"{zone_cte}"
            f"SELECT COALESCE(sr.name, 'Sin Distribuidor') AS distribuidor, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY sr.name ORDER BY total DESC"
        )
        by_distributor = [
            {"distribuidor": r[0], "facturas": r[1], "total": float(r[2])}
            for r in db.execute(by_distributor_q, params).fetchall()
        ]

        # By month - net of credit notes (include year for cross-year ranges)
        by_month_q = text(
            f"{zone_cte}"
            f"SELECT EXTRACT(YEAR FROM i.dateinvoiced)::int AS anio, "
            f"EXTRACT(MONTH FROM i.dateinvoiced)::int AS mes, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY EXTRACT(YEAR FROM i.dateinvoiced), EXTRACT(MONTH FROM i.dateinvoiced) "
            f"ORDER BY anio, mes"
        )
        by_month = [
            {"anio": r[0], "mes": r[1], "facturas": r[2], "notas_credito": r[3], "total": float(r[4])}
            for r in db.execute(by_month_q, params).fetchall()
        ]

        # By currency (so user sees totals per currency instead of mixed)
        cur_label = _currency_label("i")
        by_currency_q = text(
            f"{zone_cte}"
            f"SELECT {cur_label} AS moneda, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS monto_nc, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta "
            f"FROM adempiere.c_invoice i "
            f"{joins}"
            f"WHERE {where} "
            f"GROUP BY {cur_label} ORDER BY venta_neta DESC"
        )
        by_currency = [
            {"moneda": r[0], "facturas": r[1], "notas_credito": r[2],
             "total_facturado": float(r[3]), "monto_notas_credito": float(r[4]),
             "venta_neta": float(r[5])}
            for r in db.execute(by_currency_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "filtros": {"zona": zona, "vendedor": vendedor, "mes": mes},
            "totales": totals,
            "por_region": by_region,
            "por_zona": by_zone,
            "por_distribuidor": by_distributor,
            "por_mes": by_month,
            "por_moneda": by_currency,
        }
    finally:
        db.close()


def build_collection_summary(
    zona: str | None = None,
    vendedor: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> dict:
    """Collection summary from iDempiere c_payment (isreceipt='Y')."""
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "p.isreceipt = 'Y'",
            "p.docstatus IN ('CO', 'CL')",
            "p.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "p")
        _add_org_name_filter(conditions, params, org_name, "p")
        _add_currency_filter(conditions, params, currency_ids, "p")
        # Payments don't have salesrep_id directly; filter via linked invoice
        if salesrep_id:
            conditions.append(
                "EXISTS (SELECT 1 FROM adempiere.c_allocationline al "
                "JOIN adempiere.c_invoice inv ON al.c_invoice_id = inv.c_invoice_id "
                "WHERE al.c_payment_id = p.c_payment_id AND inv.salesrep_id = :salesrep_id)"
            )
            params["salesrep_id"] = salesrep_id
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "p.datetrx")

        where = " AND ".join(conditions)

        # Totals
        totals_q = text(
            f"SELECT COUNT(*) AS total_recibos, "
            f"COALESCE(SUM(p.payamt), 0) AS total_cobrado "
            f"FROM adempiere.c_payment p WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_recibos": row[0] if row else 0,
            "total_cobrado": float(row[1]) if row else 0.0,
        }

        # By tender type (payment method)
        # Mapping from iDempiere ad_ref_list (C_Payment Tender Type)
        by_method_q = text(
            f"SELECT CASE p.tendertype "
            f"  WHEN 'A' THEN 'Depósito Directo' "
            f"  WHEN 'B' THEN 'Tarjeta de Débito' "
            f"  WHEN 'C' THEN 'Tarjeta de Crédito' "
            f"  WHEN 'D' THEN 'Débito Directo' "
            f"  WHEN 'E' THEN 'Euro Efectivo' "
            f"  WHEN 'G' THEN 'Depósito Bancario' "
            f"  WHEN 'I' THEN 'Débito Directo ITF' "
            f"  WHEN 'J' THEN 'Comisión Bancaria' "
            f"  WHEN 'K' THEN 'Cheque' "
            f"  WHEN 'P' THEN 'Impuesto' "
            f"  WHEN 'Q' THEN 'Giro' "
            f"  WHEN 'R' THEN 'Dólar IGTF' "
            f"  WHEN 'S' THEN 'Transferencia Empresas' "
            f"  WHEN 'T' THEN 'Cuenta' "
            f"  WHEN 'U' THEN 'Euro Transferencia' "
            f"  WHEN 'W' THEN 'Transferencia' "
            f"  WHEN 'X' THEN 'Efectivo' "
            f"  WHEN 'Y' THEN 'Dólar Efectivo' "
            f"  WHEN 'Z' THEN 'Dólar Transferencia' "
            f"  ELSE p.tendertype END AS metodo_pago, "
            f"COUNT(*) AS recibos, "
            f"COALESCE(SUM(p.payamt), 0) AS total "
            f"FROM adempiere.c_payment p WHERE {where} "
            f"GROUP BY p.tendertype ORDER BY total DESC"
        )
        by_method = [
            {"metodo_pago": r[0], "recibos": r[1], "total": float(r[2])}
            for r in db.execute(by_method_q, params).fetchall()
        ]

        # By client
        by_vendor_q = text(
            f"SELECT bp.name AS vendedor, COUNT(*) AS recibos, "
            f"COALESCE(SUM(p.payamt), 0) AS total "
            f"FROM adempiere.c_payment p "
            f"JOIN adempiere.c_bpartner bp ON p.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name ORDER BY total DESC LIMIT 30"
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
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    org_name: str | None = None,
) -> list[dict]:
    """Top clients by net invoiced amount from iDempiere.

    Uses client_zone CTE to avoid JOIN multiplication from
    c_bpartner_location having multiple rows per client.

    Credit notes (ARC) are subtracted from the client's total so the
    ranking reflects net sales per client.
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {"limit": limit}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_salesrep_filter(conditions, params, salesrep_id, "i")
        _add_currency_filter(conditions, params, currency_ids, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")

        where = " AND ".join(conditions)

        zone_cte = (
            "WITH client_zone AS ("
            "SELECT DISTINCT ON (bpl.c_bpartner_id) "
            "bpl.c_bpartner_id, sreg.name AS zona_name "
            "FROM adempiere.c_bpartner_location bpl "
            "LEFT JOIN adempiere.c_salesregion sreg "
            "ON bpl.c_salesregion_id = sreg.c_salesregion_id "
            "WHERE bpl.isactive = 'Y' "
            "ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC) "
        )

        q = text(
            f"{zone_cte}"
            f"SELECT bp.value AS codigo, bp.name AS nombre, "
            f"MIN(COALESCE(cz.zona_name, 'Sin Zona')) AS zona, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARI' THEN 1 ELSE 0 END) AS facturas, "
            f"SUM(CASE WHEN dt.docbasetype = 'ARC' THEN 1 ELSE 0 END) AS notas_credito, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal ELSE 0 END), 0) AS total_facturado, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARC' THEN i.grandtotal ELSE 0 END), 0) AS total_notas_credito, "
            f"COALESCE(SUM(CASE WHEN dt.docbasetype = 'ARI' THEN i.grandtotal "
            f"WHEN dt.docbasetype = 'ARC' THEN -i.grandtotal ELSE 0 END), 0) AS venta_neta "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id "
            f"LEFT JOIN adempiere.c_bp_group bpg ON bp.c_bp_group_id = bpg.c_bp_group_id "
            f"JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id "
            f"WHERE {where} "
            f"GROUP BY bp.value, bp.name "
            f"ORDER BY venta_neta DESC "
            f"LIMIT :limit"
        )
        logger.info("build_top_clients SQL WHERE: %s | params: %s", where, {k: v for k, v in params.items() if k != "limit"})
        rows = db.execute(q, params).fetchall()
        logger.info("build_top_clients returned %d rows", len(rows))
        return [
            {
                "codigo": r[0],
                "nombre": r[1],
                "zona": r[2],
                "facturas": r[3],
                "notas_credito": r[4],
                "total_facturado": float(r[5]),
                "total_notas_credito": float(r[6]),
                "venta_neta": float(r[7]),
            }
            for r in rows
        ]
    finally:
        db.close()


def build_overdue_receivables(
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
) -> list[dict]:
    """Overdue accounts receivable from iDempiere (unpaid sales invoices).

    Uses client_zone CTE for zone info, and filters to recent invoices
    (last 3 years) with amounts > 100 to exclude old residual balances.
    """
    db = IdempiereSession()
    try:
        # Build org filter for overdue receivables
        org_clause = ""
        org_params: dict = {}
        if org_ids:
            placeholders = ", ".join(f":org_{i}" for i in range(len(org_ids)))
            org_clause = f"AND i.ad_org_id IN ({placeholders}) "
            for i, org_id in enumerate(org_ids):
                org_params[f"org_{i}"] = org_id
        salesrep_clause = ""
        if salesrep_id:
            salesrep_clause = "AND i.salesrep_id = :salesrep_id "
            org_params["salesrep_id"] = salesrep_id

        q = text(
            "WITH client_zone AS ("
            "SELECT DISTINCT ON (bpl.c_bpartner_id) "
            "bpl.c_bpartner_id, sreg.name AS zona_name "
            "FROM adempiere.c_bpartner_location bpl "
            "LEFT JOIN adempiere.c_salesregion sreg "
            "ON bpl.c_salesregion_id = sreg.c_salesregion_id "
            "WHERE bpl.isactive = 'Y' "
            "ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC) "
            "SELECT i.documentno AS numero_factura, bp.name AS cliente, "
            "COALESCE(sr.name, '') AS distribuidor, "
            "COALESCE(cz.zona_name, '') AS zona, "
            "i.grandtotal AS monto_total, i.dateinvoiced AS fecha, "
            "(i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END)::date AS fecha_vencimiento, "
            "CURRENT_DATE - (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END) AS dias_vencido "
            "FROM adempiere.c_invoice i "
            "JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            "LEFT JOIN adempiere.c_bpartner sr ON i.salesrep_id = sr.c_bpartner_id "
            "LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id "
            "LEFT JOIN adempiere.c_paymentterm pterm ON i.c_paymentterm_id = pterm.c_paymentterm_id "
            "JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id "
            "WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.ispaid = 'N' "
            "AND i.isactive = 'Y' "
            "AND dt.docbasetype = 'ARI' "
            "AND i.dateinvoiced >= (CURRENT_DATE - INTERVAL '3 years') "
            "AND i.grandtotal > 100 "
            f"{org_clause}"
            f"{salesrep_clause}"
            "AND (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END) < CURRENT_DATE "
            "ORDER BY dias_vencido DESC "
            "LIMIT 50"
        )
        rows = db.execute(q, org_params).fetchall()
        return [
            {
                "numero_factura": r[0],
                "cliente": r[1],
                "distribuidor": r[2],
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


def build_top_delinquent_clients(
    org_ids: list[int] | None = None,
    salesrep_id: int | None = None,
    limit: int = 20,
) -> list[dict]:
    """Top delinquent clients aggregated by client (sum of overdue invoices).

    Groups overdue invoices by c_bpartner, sums grandtotal, counts invoices,
    and returns max days overdue per client. Filters to last 3 years, amounts > 100.
    """
    db = IdempiereSession()
    try:
        org_clause = ""
        params: dict = {}
        if org_ids:
            placeholders = ", ".join(f":org_{i}" for i in range(len(org_ids)))
            org_clause = f"AND i.ad_org_id IN ({placeholders}) "
            for i, org_id in enumerate(org_ids):
                params[f"org_{i}"] = org_id
        salesrep_clause = ""
        if salesrep_id:
            salesrep_clause = "AND i.salesrep_id = :salesrep_id "
            params["salesrep_id"] = salesrep_id

        params["limit"] = limit

        q = text(
            "WITH client_zone AS ("
            "SELECT DISTINCT ON (bpl.c_bpartner_id) "
            "bpl.c_bpartner_id, sreg.name AS zona_name "
            "FROM adempiere.c_bpartner_location bpl "
            "LEFT JOIN adempiere.c_salesregion sreg "
            "ON bpl.c_salesregion_id = sreg.c_salesregion_id "
            "WHERE bpl.isactive = 'Y' "
            "ORDER BY bpl.c_bpartner_id, bpl.c_bpartner_location_id DESC) "
            "SELECT bp.name AS cliente, "
            "COALESCE(cz.zona_name, '') AS zona, "
            "SUM(i.grandtotal) AS total_adeudado, "
            "COUNT(*) AS num_facturas, "
            "MAX(CURRENT_DATE - (i.dateinvoiced + "
            "  CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END"
            ")) AS max_dias_vencido, "
            f"{_currency_label('i')} AS moneda "
            "FROM adempiere.c_invoice i "
            "JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            "LEFT JOIN client_zone cz ON bp.c_bpartner_id = cz.c_bpartner_id "
            "LEFT JOIN adempiere.c_paymentterm pterm ON i.c_paymentterm_id = pterm.c_paymentterm_id "
            "JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id "
            "WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO', 'CL') AND i.ispaid = 'N' "
            "AND i.isactive = 'Y' "
            "AND dt.docbasetype = 'ARI' "
            "AND i.dateinvoiced >= (CURRENT_DATE - INTERVAL '3 years') "
            "AND i.grandtotal > 100 "
            f"{org_clause}"
            f"{salesrep_clause}"
            "AND (i.dateinvoiced + CASE WHEN COALESCE(pterm.netdays, 0) = 0 THEN 30 ELSE pterm.netdays END) < CURRENT_DATE "
            f"GROUP BY bp.name, cz.zona_name, {_currency_label('i')} "
            "ORDER BY total_adeudado DESC "
            "LIMIT :limit"
        )
        rows = db.execute(q, params).fetchall()
        return [
            {
                "cliente": r[0],
                "zona": r[1],
                "total_adeudado": float(r[2]),
                "num_facturas": r[3],
                "max_dias_vencido": r[4],
                "moneda": r[5],
            }
            for r in rows
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# FINANZAS (Finance)
# ---------------------------------------------------------------------------

def build_financial_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Financial summary from iDempiere: bank balances, receivables, payables."""
    # If date_from/date_to provided, nullify mes (range takes priority)
    if date_from and date_to:
        mes = None
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        # Bank balances (filtered by org if applicable)
        bank_conditions = ["ba.isactive = 'Y'"]
        bank_params: dict = {}
        _add_org_filter(bank_conditions, bank_params, org_ids, "ba")
        bank_where = " AND ".join(bank_conditions)
        # Group all USD iso_codes (DOL, DoL, Dol, USA, dol, DLA, Dla, US.)
        # into a single 'USD' label, same as _currency_label but for banks.
        bank_currency = (
            "CASE WHEN ba.c_currency_id = 205 THEN 'VES' "
            "WHEN ba.c_currency_id IN "
            "(100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017) "
            "THEN 'USD' ELSE 'Otro' END"
        )
        bank_q = text(
            f"SELECT b.name AS banco, ba.accountno AS numero_cuenta, "
            f"CASE WHEN ba.bankaccounttype = 'C' THEN 'Corriente' "
            f"     WHEN ba.bankaccounttype = 'S' THEN 'Ahorro' "
            f"     WHEN ba.bankaccounttype = 'I' THEN 'Inversión' "
            f"     ELSE ba.bankaccounttype END AS tipo, "
            f"{bank_currency} AS moneda, "
            f"ba.currentbalance AS saldo, "
            f"o.name AS organizacion "
            f"FROM adempiere.c_bankaccount ba "
            f"JOIN adempiere.c_bank b ON ba.c_bank_id = b.c_bank_id "
            f"LEFT JOIN adempiere.c_currency c ON ba.c_currency_id = c.c_currency_id "
            f"LEFT JOIN adempiere.ad_org o ON ba.ad_org_id = o.ad_org_id "
            f"WHERE {bank_where} "
            f"ORDER BY moneda, b.name"
        )
        banks = [
            {
                "banco": r[0],
                "numero_cuenta": r[1],
                "tipo": r[2],
                "moneda": r[3],
                "saldo": float(r[4]) if r[4] else 0.0,
                "organizacion": r[5] or "Sin asignar",
            }
            for r in db.execute(bank_q, bank_params).fetchall()
        ]

        # Separate totals by currency
        totals_by_currency: dict[str, float] = {}
        for b in banks:
            cur = b["moneda"]
            totals_by_currency[cur] = totals_by_currency.get(cur, 0.0) + b["saldo"]

        # Group banks by currency for clearer presentation
        banks_ves = [b for b in banks if b["moneda"] == "VES"]
        banks_usd = [b for b in banks if b["moneda"] == "USD"]
        banks_other = [b for b in banks if b["moneda"] not in ("VES", "USD")]

        total_saldo_bancario = sum(b["saldo"] for b in banks)

        # Accounts receivable (unpaid sales invoices) - separated by currency
        cur_label = _currency_label("i")
        ar_conditions = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.ispaid = 'N'",
            "i.isactive = 'Y'",
        ]
        ar_params: dict = {}
        _add_org_filter(ar_conditions, ar_params, org_ids, "i")
        _add_date_filter(ar_conditions, ar_params, date_from, date_to, mes, anio, "i.dateinvoiced")

        ar_where = " AND ".join(ar_conditions)
        ar_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS facturas_pendientes, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_por_cobrar "
            f"FROM adempiere.c_invoice i WHERE {ar_where} "
            f"GROUP BY {cur_label} ORDER BY total_por_cobrar DESC"
        )
        ar_rows = db.execute(ar_q, ar_params).fetchall()
        receivables = {
            "facturas_pendientes": sum(r[1] for r in ar_rows),
            "total_por_cobrar": sum(float(r[2]) for r in ar_rows),
            "por_moneda": [
                {"moneda": r[0], "facturas": r[1], "total": float(r[2])}
                for r in ar_rows
            ],
        }

        # Overdue receivables - also by currency
        overdue_conds = [
            "i.issotrx = 'Y'",
            "i.docstatus IN ('CO', 'CL')",
            "i.ispaid = 'N'",
            "i.isactive = 'Y'",
            "(i.dateinvoiced + CASE WHEN COALESCE(pt.netdays, 0) = 0 THEN 30 ELSE pt.netdays END) < CURRENT_DATE",
        ]
        overdue_params: dict = {}
        _add_org_filter(overdue_conds, overdue_params, org_ids, "i")
        overdue_where = " AND ".join(overdue_conds)
        overdue_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS facturas_vencidas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_vencido "
            f"FROM adempiere.c_invoice i "
            f"LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id "
            f"WHERE {overdue_where} "
            f"GROUP BY {cur_label}"
        )
        overdue_rows = db.execute(overdue_q, overdue_params).fetchall()
        receivables["facturas_vencidas"] = sum(r[1] for r in overdue_rows)
        receivables["total_vencido"] = sum(float(r[2]) for r in overdue_rows)
        receivables["vencidas_por_moneda"] = [
            {"moneda": r[0], "facturas": r[1], "total": float(r[2])}
            for r in overdue_rows
        ]

        # Accounts payable (unpaid purchase invoices) - separated by currency
        ap_conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.ispaid = 'N'",
            "i.isactive = 'Y'",
        ]
        ap_params: dict = {}
        _add_org_filter(ap_conditions, ap_params, org_ids, "i")
        _add_date_filter(ap_conditions, ap_params, date_from, date_to, mes, anio, "i.dateinvoiced")

        ap_where = " AND ".join(ap_conditions)
        ap_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS facturas_pendientes, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_por_pagar "
            f"FROM adempiere.c_invoice i WHERE {ap_where} "
            f"GROUP BY {cur_label} ORDER BY total_por_pagar DESC"
        )
        ap_rows = db.execute(ap_q, ap_params).fetchall()
        payables = {
            "facturas_pendientes": sum(r[1] for r in ap_rows),
            "total_por_pagar": sum(float(r[2]) for r in ap_rows),
            "por_moneda": [
                {"moneda": r[0], "facturas": r[1], "total": float(r[2])}
                for r in ap_rows
            ],
        }

        # Overdue payables - also by currency
        overdue_ap_conds = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.ispaid = 'N'",
            "i.isactive = 'Y'",
            "(i.dateinvoiced + CASE WHEN COALESCE(pt.netdays, 0) = 0 THEN 30 ELSE pt.netdays END) < CURRENT_DATE",
        ]
        overdue_ap_params: dict = {}
        _add_org_filter(overdue_ap_conds, overdue_ap_params, org_ids, "i")
        overdue_ap_where = " AND ".join(overdue_ap_conds)
        overdue_ap_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS facturas_vencidas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_vencido "
            f"FROM adempiere.c_invoice i "
            f"LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id "
            f"WHERE {overdue_ap_where} "
            f"GROUP BY {cur_label}"
        )
        overdue_ap_rows = db.execute(overdue_ap_q, overdue_ap_params).fetchall()
        payables["facturas_vencidas"] = sum(r[1] for r in overdue_ap_rows)
        payables["total_vencido"] = sum(float(r[2]) for r in overdue_ap_rows)
        payables["vencidas_por_moneda"] = [
            {"moneda": r[0], "facturas": r[1], "total": float(r[2])}
            for r in overdue_ap_rows
        ]

        # Top 10 suppliers with highest overdue payables
        top_ap_conds = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.ispaid = 'N'",
            "i.isactive = 'Y'",
            "(i.dateinvoiced + CASE WHEN COALESCE(pt.netdays, 0) = 0 THEN 30 ELSE pt.netdays END) < CURRENT_DATE",
        ]
        top_ap_params: dict = {}
        _add_org_filter(top_ap_conds, top_ap_params, org_ids, "i")
        top_ap_where = " AND ".join(top_ap_conds)
        top_ap_q = text(
            f"SELECT bp.name AS proveedor, "
            f"{cur_label} AS moneda, "
            f"COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_adeudado "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id "
            f"WHERE {top_ap_where} "
            f"GROUP BY bp.name, {cur_label} "
            f"ORDER BY total_adeudado DESC LIMIT 10"
        )
        top_ap_rows = db.execute(top_ap_q, top_ap_params).fetchall()
        payables["top_proveedores_vencidos"] = [
            {"proveedor": r[0], "moneda": r[1], "facturas": r[2], "total_adeudado": float(r[3])}
            for r in top_ap_rows
        ]

        # Top 10 clients with highest overdue receivables
        top_ar_conds = list(overdue_conds)  # reuse same conditions
        top_ar_params = dict(overdue_params)
        top_ar_where = " AND ".join(top_ar_conds)
        top_ar_q = text(
            f"SELECT bp.name AS cliente, "
            f"{cur_label} AS moneda, "
            f"COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_adeudado "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"LEFT JOIN adempiere.c_paymentterm pt ON i.c_paymentterm_id = pt.c_paymentterm_id "
            f"WHERE {top_ar_where} "
            f"GROUP BY bp.name, {cur_label} "
            f"ORDER BY total_adeudado DESC LIMIT 10"
        )
        top_ar_rows = db.execute(top_ar_q, top_ar_params).fetchall()
        receivables["top_clientes_morosos"] = [
            {"cliente": r[0], "moneda": r[1], "facturas": r[2], "total_adeudado": float(r[3])}
            for r in top_ar_rows
        ]

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


def build_cobros_pagos_summary(
    is_receipt: bool = True,
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Cobros recibidos (is_receipt=True) or pagos emitidos (is_receipt=False).

    Returns totals, breakdown by currency, by payment method, and top 30
    business partners — all with proper VES/USD currency separation.
    """
    if date_from and date_to:
        mes = None
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    cur_label = _currency_label("p")
    try:
        receipt_flag = "'Y'" if is_receipt else "'N'"
        conditions = [
            f"p.isreceipt = {receipt_flag}",
            "p.docstatus IN ('CO', 'CL')",
            "p.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "p")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "p.datetrx")

        where = " AND ".join(conditions)

        # Totals by currency
        totals_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(*) AS cantidad, "
            f"COALESCE(SUM(p.payamt), 0) AS total "
            f"FROM adempiere.c_payment p WHERE {where} "
            f"GROUP BY {cur_label} ORDER BY total DESC"
        )
        totals_rows = db.execute(totals_q, params).fetchall()
        por_moneda = [
            {"moneda": r[0], "cantidad": r[1], "total": float(r[2])}
            for r in totals_rows
        ]

        # By payment method + currency
        method_q = text(
            f"SELECT CASE p.tendertype "
            f"  WHEN 'A' THEN 'Depósito Directo' "
            f"  WHEN 'B' THEN 'Tarjeta de Débito' "
            f"  WHEN 'C' THEN 'Tarjeta de Crédito' "
            f"  WHEN 'D' THEN 'Débito Directo' "
            f"  WHEN 'K' THEN 'Cheque' "
            f"  WHEN 'S' THEN 'Transferencia Empresas' "
            f"  WHEN 'W' THEN 'Transferencia' "
            f"  WHEN 'X' THEN 'Efectivo' "
            f"  WHEN 'Y' THEN 'Dólar Efectivo' "
            f"  WHEN 'Z' THEN 'Dólar Transferencia' "
            f"  ELSE p.tendertype END AS metodo_pago, "
            f"{cur_label} AS moneda, "
            f"COUNT(*) AS cantidad, "
            f"COALESCE(SUM(p.payamt), 0) AS total "
            f"FROM adempiere.c_payment p WHERE {where} "
            f"GROUP BY p.tendertype, {cur_label} ORDER BY total DESC"
        )
        por_metodo = [
            {"metodo_pago": r[0], "moneda": r[1], "cantidad": r[2], "total": float(r[3])}
            for r in db.execute(method_q, params).fetchall()
        ]

        # Top 30 business partners by amount + currency
        bp_q = text(
            f"SELECT bp.name, "
            f"{cur_label} AS moneda, "
            f"COUNT(*) AS cantidad, "
            f"COALESCE(SUM(p.payamt), 0) AS total "
            f"FROM adempiere.c_payment p "
            f"JOIN adempiere.c_bpartner bp ON p.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name, {cur_label} ORDER BY total DESC LIMIT 30"
        )
        top_socios = [
            {"nombre": r[0], "moneda": r[1], "cantidad": r[2], "total": float(r[3])}
            for r in db.execute(bp_q, params).fetchall()
        ]

        # Monthly breakdown when querying a full year (or date range > 1 month)
        por_mes: list[dict] = []
        is_annual = anio and not mes and not date_from and not date_to
        is_wide_range = False
        if date_from and date_to:
            from datetime import datetime as _dt
            try:
                d0 = _dt.strptime(date_from, "%Y-%m-%d")
                d1 = _dt.strptime(date_to, "%Y-%m-%d")
                is_wide_range = (d1 - d0).days > 45
            except ValueError:
                pass
        if is_annual or is_wide_range:
            month_q = text(
                f"SELECT EXTRACT(MONTH FROM p.datetrx)::int AS mes, "
                f"EXTRACT(YEAR FROM p.datetrx)::int AS anio_val, "
                f"{cur_label} AS moneda, "
                f"COUNT(*) AS cantidad, "
                f"COALESCE(SUM(p.payamt), 0) AS total "
                f"FROM adempiere.c_payment p WHERE {where} "
                f"GROUP BY mes, anio_val, {cur_label} "
                f"ORDER BY anio_val, mes, moneda"
            )
            por_mes = [
                {
                    "mes": r[0], "anio": r[1], "moneda": r[2],
                    "cantidad": r[3], "total": float(r[4]),
                }
                for r in db.execute(month_q, params).fetchall()
            ]

        result = {
            "tipo": "cobros" if is_receipt else "pagos",
            "total_registros": sum(m["cantidad"] for m in por_moneda),
            "por_moneda": por_moneda,
            "por_metodo_pago": por_metodo,
            "top_socios": top_socios,
        }
        if por_mes:
            result["por_mes"] = por_mes
        return result
    finally:
        db.close()


# ---------------------------------------------------------------------------
# RRHH (Human Resources)
# ---------------------------------------------------------------------------

def build_employee_summary(org_ids: list[int] | None = None) -> dict:
    """Employee summary from iDempiere hr_employee (with DISTINCT to avoid duplicates).

    hr_employee has multiple rows per person (one per payroll period), so we use
    COUNT(DISTINCT e.c_bpartner_id) for accurate counts.  Organization is taken
    from hr_employee.ad_org_id (correctly assigned) instead of c_bpartner.ad_org_id
    (which often points to the wildcard '*' org).
    """
    db = IdempiereSession()
    try:
        # Overall counts (unique employees) — only active
        conditions = ["e.isactive = 'Y'", "bp.isactive = 'Y'"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "e")
        where = " AND ".join(conditions)
        bp_join = "JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id"

        totals_q = text(
            f"SELECT "
            f"COUNT(DISTINCT e.c_bpartner_id) AS total "
            f"FROM adempiere.hr_employee e "
            f"{bp_join} "
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total": row[0] if row else 0,
            "activos": row[0] if row else 0,
            "inactivos": 0,
        }

        # By organization (unique employees per org)
        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Organización') AS organizacion, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS total, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS activos "
            f"FROM adempiere.hr_employee e "
            f"{bp_join} "
            f"LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY total DESC"
        )
        by_org = [
            {"organizacion": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_org_q, params).fetchall()
        ]

        # By department (from hr_department)
        by_dept_q = text(
            f"SELECT COALESCE(d.name, 'Sin Departamento') AS departamento, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS total, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS activos "
            f"FROM adempiere.hr_employee e "
            f"{bp_join} "
            f"LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id "
            f"WHERE {where} "
            f"GROUP BY d.name ORDER BY total DESC LIMIT 20"
        )
        by_dept = [
            {"departamento": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_dept_q, params).fetchall()
        ]

        # By job/cargo (from hr_job)
        by_job_q = text(
            f"SELECT COALESCE(j.name, 'Sin Cargo') AS cargo, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS total, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS activos "
            f"FROM adempiere.hr_employee e "
            f"{bp_join} "
            f"LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id "
            f"WHERE {where} "
            f"GROUP BY j.name ORDER BY total DESC LIMIT 30"
        )
        by_job = [
            {"cargo": r[0], "total": r[1], "activos": r[2]}
            for r in db.execute(by_job_q, params).fetchall()
        ]

        return {
            "totales": totals,
            "por_organizacion": by_org,
            "por_departamento": by_dept,
            "por_cargo": by_job,
        }
    finally:
        db.close()


def build_employee_list(
    org_ids: list[int] | None = None,
    cargo_search: str | None = None,
    name_search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """List of unique active employees from iDempiere hr_employee + c_bpartner.

    Uses DISTINCT ON (bp.c_bpartner_id) to eliminate duplicate rows caused by
    hr_employee having multiple records per person (one per payroll period).
    Joins hr_department and hr_job for richer employee info.

    If cargo_search is provided, filters by job title using ILIKE.
    If name_search is provided, filters by employee name using ILIKE.
    If date_from/date_to provided, filters by startdate (fecha de ingreso).
    """
    db = _get_session(date_from=date_from, date_to=date_to)
    try:
        conditions = ["e.isactive = 'Y'", "bp.isactive = 'Y'"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "e")

        if name_search:
            # Split into words and require ALL words to appear in the name
            # e.g. "Eduardo Pérez" → bp.name ILIKE '%Eduardo%' AND bp.name ILIKE '%Pérez%'
            words = name_search.strip().split()
            for i, word in enumerate(words):
                key = f"name_w{i}"
                conditions.append(f"bp.name ILIKE :{key}")
                params[key] = f"%{word}%"

        if cargo_search:
            # Split into words and require ALL words to appear (handles plural/singular)
            # e.g. "obreros integrales" → j.name ILIKE '%obrero%' AND j.name ILIKE '%integral%'
            words = cargo_search.strip().split()
            for i, word in enumerate(words):
                # Strip trailing 's'/'es' for basic singular matching
                stem = word.rstrip("s")
                if stem.endswith("e") and word.endswith("es") and len(stem) > 3:
                    stem = stem[:-1]  # "integrales" → "integral"
                key = f"cargo_w{i}"
                conditions.append(f"j.name ILIKE :{key}")
                params[key] = f"%{stem}%"

        if date_from:
            conditions.append("e.startdate >= :date_from")
            params["date_from"] = date_from
        if date_to:
            conditions.append("e.startdate <= :date_to")
            params["date_to"] = date_to

        where = " AND ".join(conditions)

        q = text(
            f"SELECT DISTINCT ON (bp.c_bpartner_id) "
            f"bp.name AS nombre, bp.value AS codigo, "
            f"COALESCE(o.name, '') AS organizacion, "
            f"COALESCE(d.name, '') AS departamento, "
            f"COALESCE(j.name, '') AS cargo, "
            f"e.startdate AS fecha_ingreso "
            f"FROM adempiere.hr_employee e "
            f"JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id "
            f"LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id "
            f"LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id "
            f"LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id "
            f"WHERE {where} "
            f"ORDER BY bp.c_bpartner_id, e.startdate DESC"
        )
        rows = db.execute(q, params).fetchall()

        # Sort by name for display after deduplication
        results = [
            {
                "nombre": r[0],
                "codigo": r[1],
                "organizacion": r[2],
                "departamento": r[3],
                "cargo": r[4],
                "fecha_ingreso": str(r[5]) if r[5] else "",
            }
            for r in rows
        ]
        results.sort(key=lambda x: x["nombre"])
        # When filtering by cargo or name, allow more results; otherwise cap at 100
        limit = 200 if (cargo_search or name_search) else 100
        return results[:limit]
    finally:
        db.close()


def build_birthday_list(
    mes: int | None = None,
    org_ids: list[int] | None = None,
    org_name: str | None = None,
) -> list[dict]:
    """List employees whose birthday falls in the given month.

    Uses ad_user.birthday joined through c_bpartner to hr_employee.
    """
    db = _get_session(mes=mes)
    try:
        conditions = ["e.isactive = 'Y'", "bp.isactive = 'Y'", "bday.birthday IS NOT NULL"]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "e")
        _add_org_name_filter(conditions, params, org_name, "e")

        if mes:
            conditions.append("EXTRACT(MONTH FROM bday.birthday) = :mes")
            params["mes"] = mes

        where = " AND ".join(conditions)

        # Use LATERAL subquery to pick exactly one birthday per c_bpartner
        # (avoids duplicates when a partner has multiple ad_user rows)
        q = text(
            f"SELECT DISTINCT ON (bp.c_bpartner_id) "
            f"bp.name AS nombre, "
            f"EXTRACT(DAY FROM bday.birthday)::int AS dia, "
            f"EXTRACT(MONTH FROM bday.birthday)::int AS mes, "
            f"COALESCE(d.name, '') AS departamento, "
            f"COALESCE(o.name, '') AS organizacion, "
            f"COALESCE(j.name, '') AS cargo "
            f"FROM adempiere.hr_employee e "
            f"JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id "
            f"JOIN LATERAL ("
            f"  SELECT u.birthday FROM adempiere.ad_user u "
            f"  WHERE u.c_bpartner_id = bp.c_bpartner_id "
            f"  AND u.birthday IS NOT NULL "
            f"  ORDER BY u.ad_user_id LIMIT 1"
            f") bday ON TRUE "
            f"LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id "
            f"LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id "
            f"LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id "
            f"WHERE {where} "
            f"ORDER BY bp.c_bpartner_id, e.startdate DESC"
        )
        rows = db.execute(q, params).fetchall()

        results = [
            {
                "nombre": r[0],
                "dia": r[1],
                "mes": r[2],
                "departamento": r[3],
                "organizacion": r[4],
                "cargo": r[5],
            }
            for r in rows
        ]
        # Sort by day of month for display
        results.sort(key=lambda x: x["dia"])
        return results
    finally:
        db.close()


def build_payroll_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Payroll summary from iDempiere hr_process + hr_movement."""
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "hp.docstatus IN ('CO', 'CL')",
            "hp.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "hp")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "hp.dateacct")
        where = " AND ".join(conditions)

        # Process summary — use hr_concept.type to distinguish earnings ('E') vs deductions ('D')
        # In iDempiere, all hr_movement.amount values are positive; the concept type
        # determines whether it's an earning or deduction.
        totals_q = text(
            f"SELECT COUNT(DISTINCT hp.hr_process_id) AS total_procesos, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados_procesados, "
            f"COALESCE(SUM(CASE WHEN hc.type = 'E' THEN ABS(hm.amount) ELSE 0 END), 0) AS total_devengado, "
            f"COALESCE(SUM(CASE WHEN hc.type = 'D' THEN ABS(hm.amount) ELSE 0 END), 0) AS total_deducciones "
            f"FROM adempiere.hr_process hp "
            f"LEFT JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id "
            f"LEFT JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_procesos": row[0] if row else 0,
            "empleados_procesados": row[1] if row else 0,
            "total_devengado": float(row[2]) if row else 0.0,
            "total_deducciones": float(row[3]) if row else 0.0,
        }
        totals["neto_a_pagar"] = totals["total_devengado"] - totals["total_deducciones"]

        # By payroll type
        by_payroll_q = text(
            f"SELECT COALESCE(hpy.name, 'Sin tipo') AS nomina, "
            f"COUNT(DISTINCT hp.hr_process_id) AS procesos, "
            f"COALESCE(SUM(hm.amount), 0) AS total "
            f"FROM adempiere.hr_process hp "
            f"LEFT JOIN adempiere.hr_payroll hpy ON hp.hr_payroll_id = hpy.hr_payroll_id "
            f"LEFT JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id "
            f"WHERE {where} "
            f"GROUP BY hpy.name ORDER BY total DESC"
        )
        by_payroll = [
            {"nomina": r[0], "procesos": r[1], "total": float(r[2])}
            for r in db.execute(by_payroll_q, params).fetchall()
        ]

        # Top concepts
        by_concept_q = text(
            f"SELECT hc.name AS concepto, "
            f"COALESCE(SUM(hm.amount), 0) AS total, "
            f"COUNT(*) AS movimientos "
            f"FROM adempiere.hr_process hp "
            f"JOIN adempiere.hr_movement hm ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"WHERE {where} "
            f"GROUP BY hc.name ORDER BY ABS(SUM(hm.amount)) DESC LIMIT 20"
        )
        by_concept = [
            {"concepto": r[0], "total": float(r[1]), "movimientos": r[2]}
            for r in db.execute(by_concept_q, params).fetchall()
        ]

        return {
            "totales": totals,
            "por_tipo_nomina": by_payroll,
            "conceptos_principales": by_concept,
        }
    finally:
        db.close()


def build_attendance_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Attendance/absence indicators from hr_movement concepts.

    Looks for payroll concepts related to absences (inasistencia, falta,
    permiso, reposo, etc.) and summarises them by type and organisation.
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "hp.docstatus IN ('CO', 'CL')",
            "hp.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "hm")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "hp.dateacct")

        # Filter concepts related to absence / attendance
        absence_terms = [
            "%ausent%", "%ausencia%", "%inasist%", "%falta%",
            "%permiso%", "%reposo%", "%incapacidad%", "%licencia%",
        ]
        like_clauses = " OR ".join(
            f"LOWER(hc.name) LIKE :abs_{i}" for i in range(len(absence_terms))
        )
        conditions.append(f"({like_clauses})")
        for i, term in enumerate(absence_terms):
            params[f"abs_{i}"] = term

        where = " AND ".join(conditions)

        # Summary by concept
        # NOTE: hm.qty is always 0 for absence concepts in Santoni's iDempiere.
        # We use ABS(hm.amount) for monetary impact and COUNT(*) for occurrences.
        by_concept_q = text(
            f"SELECT hc.name AS concepto, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados_afectados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto_bs, "
            f"COUNT(*) AS registros "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"WHERE {where} "
            f"GROUP BY hc.name ORDER BY registros DESC LIMIT 20"
        )
        by_concept = [
            {
                "concepto": r[0],
                "empleados_afectados": r[1],
                "monto_bs": float(r[2]),
                "ocurrencias": r[3],
            }
            for r in db.execute(by_concept_q, params).fetchall()
        ]

        # Summary by org
        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados_afectados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto_bs, "
            f"COUNT(*) AS registros "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"LEFT JOIN adempiere.ad_org o ON hm.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY registros DESC"
        )
        by_org = [
            {
                "organizacion": r[0],
                "empleados_afectados": r[1],
                "monto_bs": float(r[2]),
                "ocurrencias": r[3],
            }
            for r in db.execute(by_org_q, params).fetchall()
        ]

        # Total active employees for rate calculation
        # Must JOIN c_bpartner to check bp.isactive = 'Y' (same as build_employee_summary)
        # Without this join, hr_employee alone returns ~1057 instead of 702
        emp_conditions = ["1=1"]
        emp_params: dict = {}
        _add_org_filter(emp_conditions, emp_params, org_ids, "e")
        emp_where = " AND ".join(emp_conditions)
        emp_q = text(
            f"SELECT COUNT(DISTINCT e.c_bpartner_id) "
            f"FROM adempiere.hr_employee e "
            f"JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE e.isactive = 'Y' AND bp.isactive = 'Y' AND {emp_where}"
        )
        emp_row = db.execute(emp_q, emp_params).fetchone()
        total_activos = emp_row[0] if emp_row else 0

        total_afectados = sum(c["empleados_afectados"] for c in by_concept)
        tasa = (total_afectados / total_activos * 100) if total_activos else 0

        total_ocurrencias = sum(c["ocurrencias"] for c in by_concept)
        total_monto_bs = sum(c["monto_bs"] for c in by_concept)
        totals = {
            "empleados_activos": total_activos,
            "empleados_con_ausencias": total_afectados,
            "total_ocurrencias": total_ocurrencias,
            "total_monto_bs": total_monto_bs,
            "tasa_ausentismo_pct": round(tasa, 2),
            "conceptos_encontrados": len(by_concept),
            "nota_horas": "No se dispone de horas-hombre en el sistema de nómina. Los datos se expresan en ocurrencias y monto (Bs.).",
        }

        if not by_concept:
            totals["nota"] = (
                "No se encontraron conceptos de ausentismo en nómina para este período. "
                "Los conceptos buscados incluyen: inasistencia, falta, permiso, "
                "reposo, incapacidad, licencia."
            )

        return {
            "totales": totals,
            "por_concepto": by_concept,
            "por_organizacion": by_org,
        }
    finally:
        db.close()


def build_turnover_summary(
    anio: int | None = None,
    org_ids: list[int] | None = None,
) -> dict:
    """Employee turnover (rotation) from hr_employee enddate.

    Counts employees whose enddate falls within the given year as 'bajas'.
    Calculates turnover rate = bajas / total_activos * 100.
    """
    from datetime import datetime

    if not anio:
        anio = datetime.now().year

    db = _get_session(anio=anio)
    try:
        # Bajas (employees with enddate in the given year)
        conditions = [
            "e.isactive = 'N'",
            "e.enddate >= :year_start",
            "e.enddate < :year_end",
        ]
        params: dict = {
            "year_start": f"{anio}-01-01",
            "year_end": f"{anio + 1}-01-01",
        }
        _add_org_filter(conditions, params, org_ids, "e")
        where = " AND ".join(conditions)

        # Bajas by org
        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"COUNT(DISTINCT e.c_bpartner_id) AS bajas "
            f"FROM adempiere.hr_employee e "
            f"LEFT JOIN adempiere.ad_org o ON e.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY bajas DESC"
        )
        by_org = [
            {"organizacion": r[0], "bajas": r[1]}
            for r in db.execute(by_org_q, params).fetchall()
        ]
        total_bajas = sum(r["bajas"] for r in by_org)

        # Total active employees for rate
        emp_conditions = ["1=1"]
        emp_params: dict = {}
        _add_org_filter(emp_conditions, emp_params, org_ids, "e")
        emp_where = " AND ".join(emp_conditions)
        emp_q = text(
            f"SELECT COUNT(DISTINCT e.c_bpartner_id) "
            f"FROM adempiere.hr_employee e "
            f"WHERE e.isactive = 'Y' AND {emp_where}"
        )
        emp_row = db.execute(emp_q, emp_params).fetchone()
        total_activos = emp_row[0] if emp_row else 0

        tasa = (total_bajas / total_activos * 100) if total_activos else 0

        return {
            "anio": anio,
            "totales": {
                "empleados_activos": total_activos,
                "bajas": total_bajas,
                "tasa_rotacion_pct": round(tasa, 2),
            },
            "por_organizacion": by_org,
        }
    finally:
        db.close()


def build_vacation_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
) -> dict:
    """Vacation data from hr_movement concepts containing 'vacacion' or 'bono vacacional'."""
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "hp.docstatus IN ('CO', 'CL')",
            "hp.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "hm")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "hp.dateacct")

        # Filter by org_name if provided
        if org_name:
            conditions.append("UPPER(o.name) LIKE :org_name_filter")
            params["org_name_filter"] = f"%{org_name.upper()}%"

        # Filter concepts related to vacations
        # Use unaccent-safe patterns: 'vacacion' matches both 'vacacion' and 'vacación'
        vacation_terms = ["%vacacion%", "%vacaci_n%", "%bono vacacional%", "%dias disfrut%"]
        like_clauses = " OR ".join(
            f"LOWER(hc.name) LIKE :vac_{i}" for i in range(len(vacation_terms))
        )
        conditions.append(f"({like_clauses})")
        for i, term in enumerate(vacation_terms):
            params[f"vac_{i}"] = term

        where = " AND ".join(conditions)

        # Optional org JOIN (needed when org_name filter is used)
        org_join = "LEFT JOIN adempiere.ad_org o ON hm.ad_org_id = o.ad_org_id " if org_name else ""

        # Totals
        totals_q = text(
            f"SELECT COUNT(DISTINCT hm.c_bpartner_id) AS total_empleados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS total_monto, "
            f"COUNT(*) AS total_ocurrencias "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"{org_join}"
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_empleados": row[0] if row else 0,
            "total_monto": float(row[1]) if row else 0.0,
            "total_ocurrencias": row[2] if row else 0,
        }

        if totals["total_empleados"] == 0:
            totals["nota"] = (
                "No se encontraron conceptos de vacaciones en nómina para este período. "
                "Los conceptos buscados incluyen: vacacion, bono vacacional, dias disfrutados."
            )

        # By concept
        by_concept_q = text(
            f"SELECT hc.name AS concepto, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto, "
            f"COUNT(*) AS ocurrencias "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"{org_join}"
            f"WHERE {where} "
            f"GROUP BY hc.name ORDER BY monto DESC"
        )
        by_concept = [
            {
                "concepto": r[0],
                "empleados": r[1],
                "monto": float(r[2]),
                "ocurrencias": r[3],
            }
            for r in db.execute(by_concept_q, params).fetchall()
        ]

        # By organization
        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"COUNT(DISTINCT hm.c_bpartner_id) AS empleados, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto, "
            f"COUNT(*) AS ocurrencias "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"LEFT JOIN adempiere.ad_org o ON hm.ad_org_id = o.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY monto DESC"
        )
        by_org = [
            {
                "organizacion": r[0],
                "empleados": r[1],
                "monto": float(r[2]),
                "ocurrencias": r[3],
            }
            for r in db.execute(by_org_q, params).fetchall()
        ]

        # Detail: top 30 employees with vacation amounts
        detail_q = text(
            f"SELECT bp.name AS empleado, "
            f"hc.name AS concepto, "
            f"COALESCE(SUM(ABS(hm.amount)), 0) AS monto "
            f"FROM adempiere.hr_movement hm "
            f"JOIN adempiere.hr_process hp ON hp.hr_process_id = hm.hr_process_id "
            f"JOIN adempiere.hr_concept hc ON hm.hr_concept_id = hc.hr_concept_id "
            f"JOIN adempiere.c_bpartner bp ON hm.c_bpartner_id = bp.c_bpartner_id "
            f"{org_join}"
            f"WHERE {where} "
            f"GROUP BY bp.name, hc.name ORDER BY monto DESC LIMIT 30"
        )
        detail = [
            {
                "empleado": r[0],
                "concepto": r[1],
                "monto": float(r[2]),
            }
            for r in db.execute(detail_q, params).fetchall()
        ]

        return {
            "totales": totals,
            "por_concepto": by_concept,
            "por_organizacion": by_org,
            "detalle_empleados": detail,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# PRODUCCION (Production)
# ---------------------------------------------------------------------------

def build_production_summary(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
) -> dict:
    """Production/inventory movement summary from iDempiere m_inout.

    Always uses live iDempiere — local DB has incomplete m_inout data.

    Santoni does not use the Manufacturing module (pp_order is empty).
    Instead, production activity is tracked via material movements:
    - V+ = Vendor Receipt (raw material incoming)
    - C- = Customer Shipment (finished product outgoing)
    - M+/M- = Internal inventory movements
    - P+/P- = Production receipts (rare)
    """
    db = IdempiereSession()  # Always live — local DB has incomplete m_inout
    try:
        conditions = ["io.isactive = 'Y'", "io.docstatus IN ('CO', 'CL')"]
        params: dict = {}
        _add_org_name_filter(conditions, params, org_name, "io")
        if not org_name:
            _add_org_filter(conditions, params, org_ids, "io")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "io.movementdate")
        where = " AND ".join(conditions)

        # Totals by movement type
        totals_q = text(
            f"SELECT "
            f"SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones_mp, "
            f"SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos_pt, "
            f"SUM(CASE WHEN io.movementtype IN ('M+','M-') THEN 1 ELSE 0 END) AS movimientos_internos, "
            f"SUM(CASE WHEN io.movementtype IN ('P+','P-') THEN 1 ELSE 0 END) AS movimientos_produccion, "
            f"COUNT(*) AS total_movimientos "
            f"FROM adempiere.m_inout io WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "recepciones_materia_prima": row[0] if row else 0,
            "despachos_producto_terminado": row[1] if row else 0,
            "movimientos_internos": row[2] if row else 0,
            "movimientos_produccion": row[3] if row else 0,
            "total_movimientos": row[4] if row else 0,
        }

        # Top products by quantity moved
        by_product_q = text(
            f"SELECT p.name AS producto, "
            f"SUM(CASE WHEN io.movementtype = 'V+' THEN iol.movementqty ELSE 0 END) AS recibido, "
            f"SUM(CASE WHEN io.movementtype = 'C-' THEN iol.movementqty ELSE 0 END) AS despachado, "
            f"SUM(ABS(iol.movementqty)) AS total_movido "
            f"FROM adempiere.m_inout io "
            f"JOIN adempiere.m_inoutline iol ON io.m_inout_id = iol.m_inout_id "
            f"JOIN adempiere.m_product p ON iol.m_product_id = p.m_product_id "
            f"WHERE {where} "
            f"GROUP BY p.name ORDER BY total_movido DESC LIMIT 20"
        )
        by_product = [
            {
                "producto": r[0],
                "recibido": float(r[1]),
                "despachado": float(r[2]),
                "total_movido": float(r[3]),
            }
            for r in db.execute(by_product_q, params).fetchall()
        ]

        # By month (include year for cross-year ranges)
        by_month_q = text(
            f"SELECT EXTRACT(YEAR FROM io.movementdate)::int AS anio, "
            f"EXTRACT(MONTH FROM io.movementdate)::int AS mes, "
            f"COUNT(*) AS movimientos, "
            f"SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones, "
            f"SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos "
            f"FROM adempiere.m_inout io WHERE {where} "
            f"GROUP BY EXTRACT(YEAR FROM io.movementdate), EXTRACT(MONTH FROM io.movementdate) "
            f"ORDER BY anio, mes"
        )
        by_month = [
            {"anio": r[0], "mes": r[1], "movimientos": r[2], "recepciones": r[3], "despachos": r[4]}
            for r in db.execute(by_month_q, params).fetchall()
        ]

        # By organization
        by_org_q = text(
            f"SELECT org.name AS organizacion, "
            f"COUNT(*) AS movimientos, "
            f"SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones, "
            f"SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos "
            f"FROM adempiere.m_inout io "
            f"JOIN adempiere.ad_org org ON io.ad_org_id = org.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY org.name ORDER BY movimientos DESC"
        )
        by_org = [
            {"organizacion": r[0], "movimientos": r[1], "recepciones": r[2], "despachos": r[3]}
            for r in db.execute(by_org_q, params).fetchall()
        ]

        # By date (daily breakdown — prevents LLM from inventing dates)
        by_date_q = text(
            f"SELECT io.movementdate::date AS fecha, "
            f"COUNT(*) AS movimientos, "
            f"SUM(CASE WHEN io.movementtype = 'V+' THEN 1 ELSE 0 END) AS recepciones, "
            f"SUM(CASE WHEN io.movementtype = 'C-' THEN 1 ELSE 0 END) AS despachos "
            f"FROM adempiere.m_inout io WHERE {where} "
            f"GROUP BY io.movementdate::date ORDER BY fecha DESC LIMIT 31"
        )
        by_date = [
            {
                "fecha": str(r[0]),
                "movimientos": r[1],
                "recepciones": r[2],
                "despachos": r[3],
            }
            for r in db.execute(by_date_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "mes": mes,
            "totales": totals,
            "por_producto": by_product,
            "por_mes": by_month,
            "por_organizacion": by_org,
            "por_fecha": by_date,
        }
    finally:
        db.close()


def build_production_orders(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
) -> list[dict]:
    """Recent material movement documents from iDempiere m_inout."""
    db = IdempiereSession()  # Always live — local DB has incomplete m_inout
    try:
        conditions = ["io.isactive = 'Y'", "io.docstatus IN ('CO', 'CL')"]
        params: dict = {}
        _add_org_name_filter(conditions, params, org_name, "io")
        if not org_name:
            _add_org_filter(conditions, params, org_ids, "io")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "io.movementdate")
        where = " AND ".join(conditions)

        q = text(
            f"SELECT io.documentno AS documento, "
            f"io.movementdate::date AS fecha, "
            f"CASE io.movementtype "
            f"  WHEN 'V+' THEN 'Recepción MP' "
            f"  WHEN 'C-' THEN 'Despacho PT' "
            f"  WHEN 'M+' THEN 'Mov. Entrada' "
            f"  WHEN 'M-' THEN 'Mov. Salida' "
            f"  WHEN 'P+' THEN 'Producción +' "
            f"  WHEN 'P-' THEN 'Producción -' "
            f"  ELSE io.movementtype END AS tipo, "
            f"org.name AS organizacion, "
            f"COALESCE(bp.name, '') AS socio_negocio "
            f"FROM adempiere.m_inout io "
            f"JOIN adempiere.ad_org org ON io.ad_org_id = org.ad_org_id "
            f"LEFT JOIN adempiere.c_bpartner bp ON io.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"ORDER BY io.movementdate DESC LIMIT 50"
        )
        return [
            {
                "documento": r[0],
                "fecha": str(r[1]) if r[1] else "",
                "tipo": r[2],
                "organizacion": r[3] or "",
                "socio_negocio": r[4] or "",
            }
            for r in db.execute(q, params).fetchall()
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# PRODUCCIÓN REAL (m_production + m_productionline)
# ---------------------------------------------------------------------------


def build_production_runs(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
    product_search: str | None = None,
) -> dict:
    """Production runs from m_production + m_productionline.

    Each production has lines: one 'header' line (isendproduct='Y', qty positive)
    for the finished product, and component lines (isendproduct='N', qty negative)
    for consumed raw materials.

    NOTE: m_production.productionqty is NEGATIVE in Santoni's iDempiere.
    Always use m_productionline.movementqty for real quantities.
    """
    db = IdempiereSession()  # Always live — local DB has incomplete m_production (only 32 vs 5,919+ records)
    try:
        conditions = ["pr.isactive = 'Y'", "pr.docstatus IN ('CO', 'CL')"]
        params: dict = {}
        _add_org_name_filter(conditions, params, org_name, "pr")
        if not org_name:
            _add_org_filter(conditions, params, org_ids, "pr")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "pr.movementdate")
        if product_search:
            prod_conds: list[str] = []
            _add_product_search_filter(prod_conds, params, product_search, prefix="prprod")
            if prod_conds:
                conditions.append(
                    f"pr.m_production_id IN ("
                    f"SELECT prl2.m_production_id FROM adempiere.m_productionline prl2 "
                    f"JOIN adempiere.m_product p ON prl2.m_product_id = p.m_product_id "
                    f"WHERE {prod_conds[0]})"
                )
        where = " AND ".join(conditions)

        # 1. Totals — simple JOIN, no nested subqueries
        totals_q = text(
            f"SELECT COUNT(DISTINCT pr.m_production_id) AS total_producciones, "
            f"COALESCE(SUM(CASE WHEN prl.isendproduct = 'Y' AND prl.movementqty > 0 "
            f"  THEN prl.movementqty ELSE 0 END), 0) AS qty_terminada, "
            f"COALESCE(SUM(CASE WHEN prl.isendproduct = 'N' OR prl.movementqty < 0 "
            f"  THEN ABS(prl.movementqty) ELSE 0 END), 0) AS qty_consumida "
            f"FROM adempiere.m_production pr "
            f"JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id "
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_producciones": row[0] if row else 0,
            "cantidad_producto_terminado": float(row[1]) if row else 0.0,
            "cantidad_insumos_consumidos": float(row[2]) if row else 0.0,
        }

        # 2. Top finished products (isendproduct = 'Y', qty > 0)
        by_product_q = text(
            f"SELECT p.name AS producto, "
            f"COUNT(DISTINCT pr.m_production_id) AS producciones, "
            f"COALESCE(SUM(prl.movementqty), 0) AS qty_producida "
            f"FROM adempiere.m_production pr "
            f"JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id "
            f"JOIN adempiere.m_product p ON prl.m_product_id = p.m_product_id "
            f"WHERE {where} AND prl.isendproduct = 'Y' AND prl.movementqty > 0 "
            f"GROUP BY p.name ORDER BY qty_producida DESC LIMIT 20"
        )
        by_product = [
            {
                "producto": r[0],
                "producciones": r[1],
                "cantidad_producida": float(r[2]),
            }
            for r in db.execute(by_product_q, params).fetchall()
        ]

        # 3. Top consumed raw materials (isendproduct = 'N' or qty < 0)
        by_insumo_q = text(
            f"SELECT p.name AS insumo, "
            f"COALESCE(SUM(ABS(prl.movementqty)), 0) AS qty_consumida "
            f"FROM adempiere.m_production pr "
            f"JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id "
            f"JOIN adempiere.m_product p ON prl.m_product_id = p.m_product_id "
            f"WHERE {where} AND (prl.isendproduct = 'N' OR prl.movementqty < 0) "
            f"GROUP BY p.name ORDER BY qty_consumida DESC LIMIT 20"
        )
        by_insumo = [
            {
                "insumo": r[0],
                "cantidad_consumida": float(r[1]),
            }
            for r in db.execute(by_insumo_q, params).fetchall()
        ]

        # 4. By month (qty from finished products in productionline, include year for cross-year ranges)
        by_month_q = text(
            f"SELECT EXTRACT(YEAR FROM pr.movementdate)::int AS anio, "
            f"EXTRACT(MONTH FROM pr.movementdate)::int AS mes, "
            f"COUNT(DISTINCT pr.m_production_id) AS producciones, "
            f"COALESCE(SUM(CASE WHEN prl.isendproduct = 'Y' AND prl.movementqty > 0 "
            f"  THEN prl.movementqty ELSE 0 END), 0) AS qty_terminada, "
            f"COALESCE(SUM(CASE WHEN prl.isendproduct = 'N' OR prl.movementqty < 0 "
            f"  THEN ABS(prl.movementqty) ELSE 0 END), 0) AS qty_consumida "
            f"FROM adempiere.m_production pr "
            f"JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id "
            f"WHERE {where} "
            f"GROUP BY EXTRACT(YEAR FROM pr.movementdate), EXTRACT(MONTH FROM pr.movementdate) "
            f"ORDER BY anio, mes"
        )
        by_month = [
            {"anio": r[0], "mes": r[1], "producciones": r[2],
             "cantidad_terminada": float(r[3]), "cantidad_consumida": float(r[4])}
            for r in db.execute(by_month_q, params).fetchall()
        ]

        # 5. By organization (qty from finished products in productionline)
        by_org_q = text(
            f"SELECT org.name AS organizacion, "
            f"COUNT(DISTINCT pr.m_production_id) AS producciones, "
            f"COALESCE(SUM(CASE WHEN prl.isendproduct = 'Y' AND prl.movementqty > 0 "
            f"  THEN prl.movementqty ELSE 0 END), 0) AS qty_terminada, "
            f"COALESCE(SUM(CASE WHEN prl.isendproduct = 'N' OR prl.movementqty < 0 "
            f"  THEN ABS(prl.movementqty) ELSE 0 END), 0) AS qty_consumida "
            f"FROM adempiere.m_production pr "
            f"JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id "
            f"JOIN adempiere.ad_org org ON pr.ad_org_id = org.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY org.name ORDER BY producciones DESC"
        )
        by_org = [
            {"organizacion": r[0], "producciones": r[1],
             "cantidad_terminada": float(r[2]), "cantidad_consumida": float(r[3])}
            for r in db.execute(by_org_q, params).fetchall()
        ]

        # 6. Daily breakdown (anti-hallucination, qty from productionline)
        by_date_q = text(
            f"SELECT pr.movementdate::date AS fecha, "
            f"COUNT(DISTINCT pr.m_production_id) AS producciones, "
            f"COALESCE(SUM(CASE WHEN prl.isendproduct = 'Y' AND prl.movementqty > 0 "
            f"  THEN prl.movementqty ELSE 0 END), 0) AS qty_terminada "
            f"FROM adempiere.m_production pr "
            f"JOIN adempiere.m_productionline prl ON pr.m_production_id = prl.m_production_id "
            f"WHERE {where} "
            f"GROUP BY pr.movementdate::date ORDER BY fecha DESC LIMIT 31"
        )
        by_date = [
            {"fecha": str(r[0]), "producciones": r[1], "cantidad_terminada": float(r[2])}
            for r in db.execute(by_date_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "mes": mes,
            "totales": totals,
            "productos_terminados": by_product,
            "insumos_consumidos": by_insumo,
            "por_mes": by_month,
            "por_organizacion": by_org,
            "por_fecha": by_date,
        }
    finally:
        db.close()


def build_bom_info(
    product_search: str | None = None,
    org_ids: list[int] | None = None,
    org_name: str | None = None,
) -> dict:
    """Bill of Materials (BOM) / recipes from pp_product_bom + pp_product_bomline.

    229 BOMs defined in Santoni (Arroz Santoni, Harina, Choco Toni, etc.)
    Always queries live iDempiere (BOMs are reference data, not temporal).
    """
    db = IdempiereSession()
    try:
        conditions = ["b.isactive = 'Y'"]
        params: dict = {}
        _add_org_name_filter(conditions, params, org_name, "b")
        if not org_name:
            _add_org_filter(conditions, params, org_ids, "b")
        if product_search:
            _add_product_search_filter(conditions, params, product_search, prefix="bomprod")
        where = " AND ".join(conditions)

        # List BOMs with line counts
        bom_q = text(
            f"SELECT b.pp_product_bom_id, b.name AS bom_nombre, "
            f"p.name AS producto, org.name AS organizacion, "
            f"(SELECT COUNT(*) FROM adempiere.pp_product_bomline bl "
            f" WHERE bl.pp_product_bom_id = b.pp_product_bom_id) AS num_componentes "
            f"FROM adempiere.pp_product_bom b "
            f"JOIN adempiere.m_product p ON b.m_product_id = p.m_product_id "
            f"JOIN adempiere.ad_org org ON b.ad_org_id = org.ad_org_id "
            f"WHERE {where} "
            f"ORDER BY b.name LIMIT 30"
        )
        boms = []
        for r in db.execute(bom_q, params).fetchall():
            bom_id = r[0]
            bom_entry = {
                "bom_nombre": r[1],
                "producto": r[2],
                "organizacion": r[3],
                "num_componentes": r[4],
            }

            # Get components for this BOM
            comp_q = text(
                "SELECT p.name AS componente, "
                "bl.qtybom AS cantidad, "
                "COALESCE(u.name, '-') AS unidad, "
                "bl.componenttype "
                "FROM adempiere.pp_product_bomline bl "
                "JOIN adempiere.m_product p ON bl.m_product_id = p.m_product_id "
                "LEFT JOIN adempiere.c_uom u ON bl.c_uom_id = u.c_uom_id "
                "WHERE bl.pp_product_bom_id = :bom_id AND bl.isactive = 'Y' "
                "ORDER BY bl.line"
            )
            components = [
                {
                    "componente": c[0],
                    "cantidad": float(c[1]) if c[1] else 0,
                    "unidad": c[2],
                    "tipo": c[3] or "CO",
                }
                for c in db.execute(comp_q, {"bom_id": bom_id}).fetchall()
            ]
            bom_entry["componentes"] = components
            boms.append(bom_entry)

        return {
            "total_boms": len(boms),
            "boms": boms,
        }
    finally:
        db.close()


def build_warehouse_movements(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
) -> dict:
    """Internal warehouse movements from m_movement + m_movementline.

    6,014+ completed movements in Santoni (transfers between warehouses/silos).
    """
    db = IdempiereSession()  # Always live — local DB has incomplete m_movement
    try:
        conditions = ["mv.isactive = 'Y'", "mv.docstatus IN ('CO', 'CL')"]
        params: dict = {}
        _add_org_name_filter(conditions, params, org_name, "mv")
        if not org_name:
            _add_org_filter(conditions, params, org_ids, "mv")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "mv.movementdate")
        where = " AND ".join(conditions)

        # 1. Totals
        totals_q = text(
            f"SELECT COUNT(*) AS total_movimientos "
            f"FROM adempiere.m_movement mv WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_movimientos": row[0] if row else 0,
        }

        # 2. Top products moved
        by_product_q = text(
            f"SELECT p.name AS producto, "
            f"SUM(ABS(ml.movementqty)) AS qty_movida, "
            f"COUNT(DISTINCT mv.m_movement_id) AS movimientos "
            f"FROM adempiere.m_movement mv "
            f"JOIN adempiere.m_movementline ml ON mv.m_movement_id = ml.m_movement_id "
            f"JOIN adempiere.m_product p ON ml.m_product_id = p.m_product_id "
            f"WHERE {where} "
            f"GROUP BY p.name ORDER BY qty_movida DESC LIMIT 20"
        )
        by_product = [
            {
                "producto": r[0],
                "cantidad_movida": float(r[1]),
                "movimientos": r[2],
            }
            for r in db.execute(by_product_q, params).fetchall()
        ]

        # 3. Movement flow: origin warehouse → destination warehouse
        by_warehouse_q = text(
            f"SELECT w_from.name AS almacen_origen, "
            f"w_to.name AS almacen_destino, "
            f"COUNT(DISTINCT mv.m_movement_id) AS movimientos, "
            f"SUM(ABS(ml.movementqty)) AS qty_total "
            f"FROM adempiere.m_movement mv "
            f"JOIN adempiere.m_movementline ml ON mv.m_movement_id = ml.m_movement_id "
            f"JOIN adempiere.m_locator l_from ON ml.m_locator_id = l_from.m_locator_id "
            f"JOIN adempiere.m_warehouse w_from ON l_from.m_warehouse_id = w_from.m_warehouse_id "
            f"JOIN adempiere.m_locator l_to ON ml.m_locatorto_id = l_to.m_locator_id "
            f"JOIN adempiere.m_warehouse w_to ON l_to.m_warehouse_id = w_to.m_warehouse_id "
            f"WHERE {where} "
            f"GROUP BY w_from.name, w_to.name ORDER BY qty_total DESC LIMIT 15"
        )
        by_warehouse = [
            {
                "almacen_origen": r[0],
                "almacen_destino": r[1],
                "movimientos": r[2],
                "cantidad_total": float(r[3]),
            }
            for r in db.execute(by_warehouse_q, params).fetchall()
        ]

        # 4. By organization
        by_org_q = text(
            f"SELECT org.name AS organizacion, "
            f"COUNT(*) AS movimientos "
            f"FROM adempiere.m_movement mv "
            f"JOIN adempiere.ad_org org ON mv.ad_org_id = org.ad_org_id "
            f"WHERE {where} "
            f"GROUP BY org.name ORDER BY movimientos DESC"
        )
        by_org = [
            {"organizacion": r[0], "movimientos": r[1]}
            for r in db.execute(by_org_q, params).fetchall()
        ]

        # 5. Recent documents
        docs_q = text(
            f"SELECT mv.documentno, mv.movementdate::date AS fecha, "
            f"COALESCE(mv.description, '') AS descripcion, "
            f"org.name AS organizacion "
            f"FROM adempiere.m_movement mv "
            f"JOIN adempiere.ad_org org ON mv.ad_org_id = org.ad_org_id "
            f"WHERE {where} "
            f"ORDER BY mv.movementdate DESC LIMIT 20"
        )
        docs = [
            {
                "documento": r[0],
                "fecha": str(r[1]),
                "descripcion": r[2],
                "organizacion": r[3],
            }
            for r in db.execute(docs_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "mes": mes,
            "totales": totals,
            "por_producto": by_product,
            "flujo_almacenes": by_warehouse,
            "por_organizacion": by_org,
            "documentos_recientes": docs,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# COMPRAS PRODUCTORES (Producer Purchases)
# ---------------------------------------------------------------------------

def build_producer_purchases(
    producto: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
) -> dict:
    """Producer purchases from iDempiere."""
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "o.issotrx = 'N'",
            "o.docstatus IN ('CO', 'CL')",
            "o.isactive = 'Y'",
            # Only real agricultural producers (exclude internal orgs like INPROA)
            "bp.codigoproductor IS NOT NULL",
            "bp.codigoproductor != ''",
        ]
        params: dict = {}
        _add_exclude_internal_orgs_filter(conditions, params, "bp")
        _add_org_filter(conditions, params, org_ids, "o")
        _add_org_name_filter(conditions, params, org_name, "o")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "o.dateordered")

        if producto:
            _add_product_search_filter(conditions, params, producto, prefix="pprod")

        where = " AND ".join(conditions)

        # Totals (JOIN c_bpartner to apply codigoproductor filter)
        totals_q = text(
            f"SELECT COUNT(DISTINCT o.c_order_id) AS total_guias, "
            f"COALESCE(SUM(ol.qtyordered), 0) AS total_peso_neto_kg, "
            f"COALESCE(SUM(ol.linenetamt), 0) AS total_monto "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id "
            f"JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id "
            f"JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where}"
        )
        row = db.execute(totals_q, params).fetchone()
        totals = {
            "total_guias": row[0] if row else 0,
            "total_peso_neto_kg": float(row[1]) if row else 0.0,
            "total_monto": float(row[2]) if row else 0.0,
        }

        # By product (no humedad/impureza — not available in c_order standard fields)
        by_product_q = text(
            f"SELECT p.name AS producto, "
            f"COUNT(DISTINCT o.c_order_id) AS guias, "
            f"COALESCE(SUM(ol.qtyordered), 0) AS peso_neto_kg, "
            f"COALESCE(SUM(ol.linenetamt), 0) AS monto_total "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id "
            f"JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id "
            f"JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY p.name ORDER BY monto_total DESC"
        )
        by_product = [
            {
                "producto": r[0],
                "guias": r[1],
                "peso_neto_kg": float(r[2]),
                "monto_total": float(r[3]),
            }
            for r in db.execute(by_product_q, params).fetchall()
        ]

        # By producer (top 20) with location data
        by_producer_q = text(
            f"SELECT bp.name AS nombre, "
            f"COALESCE(reg.name, '') AS estado, "
            f"COALESCE(ci.name, loc.city, '') AS municipio, "
            f"COUNT(DISTINCT o.c_order_id) AS guias, "
            f"COALESCE(SUM(ol.qtyordered), 0) AS peso_neto_kg, "
            f"COALESCE(SUM(ol.linenetamt), 0) AS monto_total "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id "
            f"JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id "
            f"JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
            f"LEFT JOIN adempiere.c_bpartner_location bpl "
            f"  ON bp.c_bpartner_id = bpl.c_bpartner_id AND bpl.isactive = 'Y' "
            f"LEFT JOIN adempiere.c_location loc "
            f"  ON bpl.c_location_id = loc.c_location_id "
            f"LEFT JOIN adempiere.c_city ci ON loc.c_city_id = ci.c_city_id "
            f"LEFT JOIN adempiere.c_region reg ON loc.c_region_id = reg.c_region_id "
            f"WHERE {where} "
            f"GROUP BY bp.name, reg.name, ci.name, loc.city "
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
    """Registered agricultural producers from iDempiere c_bpartner.

    Filters by codigoproductor IS NOT NULL (Santoni's custom field that
    identifies agricultural producers) instead of just isvendor='Y' which
    would return all 26,000+ vendors.
    Also joins to location tables for estado/municipio data.
    """
    db = IdempiereSession()
    try:
        conditions = [
            "bp.isactive = 'Y'",
            "bp.isvendor = 'Y'",
            "bp.codigoproductor IS NOT NULL",
            "bp.codigoproductor != ''",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "bp")

        q = text(
            f"SELECT DISTINCT ON (bp.c_bpartner_id) "
            f"bp.name AS productor, "
            f"COALESCE(bp.codigoproductor, bp.value) AS codigo, "
            f"COALESCE(ci.name, loc.city, '') AS ciudad, "
            f"COALESCE(reg.name, '') AS estado "
            f"FROM adempiere.c_bpartner bp "
            f"LEFT JOIN adempiere.c_bpartner_location bpl "
            f"  ON bp.c_bpartner_id = bpl.c_bpartner_id AND bpl.isactive = 'Y' "
            f"LEFT JOIN adempiere.c_location loc "
            f"  ON bpl.c_location_id = loc.c_location_id "
            f"LEFT JOIN adempiere.c_city ci ON loc.c_city_id = ci.c_city_id "
            f"LEFT JOIN adempiere.c_region reg ON loc.c_region_id = reg.c_region_id "
            f"WHERE {' AND '.join(conditions)} "
            f"ORDER BY bp.c_bpartner_id, bp.name LIMIT 100"
        )
        return [
            {
                "productor": r[0],
                "codigo": r[1],
                "ciudad": r[2],
                "estado": r[3],
            }
            for r in db.execute(q, params).fetchall()
        ]
    finally:
        db.close()


def build_producer_pending_payments(
    producto: str | None = None,
    org_ids: list[int] | None = None,
    producer_name: str | None = None,
    currency_ids: list[int] | None = None,
) -> list[dict]:
    """Pending purchase invoices (not fully paid) from iDempiere.

    Uses c_invoice (ispaid='N') instead of c_order, since c_order
    does not have a totalpaid column in Santoni's iDempiere.
    Supports filtering by producer name (ILIKE) for specific producer debt queries.
    """
    db = IdempiereSession()
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.ispaid = 'N'",
            "i.isactive = 'Y'",
            "i.dateinvoiced >= (CURRENT_DATE - INTERVAL '2 years')",
            # Only real agricultural producers (exclude internal orgs like INPROA)
            "bp.codigoproductor IS NOT NULL",
            "bp.codigoproductor != ''",
        ]
        params: dict = {}
        _add_exclude_internal_orgs_filter(conditions, params, "bp")
        _add_org_filter(conditions, params, org_ids, "i")
        _add_currency_filter(conditions, params, currency_ids, "i")

        if producto:
            _add_product_search_filter(conditions, params, producto, prefix="pend_prod")

        if producer_name:
            conditions.append("LOWER(bp.name) LIKE :producer_name")
            params["producer_name"] = f"%{producer_name.lower()}%"

        where = " AND ".join(conditions)

        currency_col = _currency_label("i")
        q = text(
            f"SELECT bp.name AS productor, i.documentno AS documento, "
            f"i.dateinvoiced::date AS fecha, "
            f"i.grandtotal AS monto_total, "
            f"{currency_col} AS moneda "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"{'JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id ' if producto else ''}"
            f"{'JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id ' if producto else ''}"
            f"WHERE {where} "
            f"ORDER BY i.grandtotal DESC LIMIT 30"
        )
        return [
            {
                "productor": r[0],
                "documento": r[1],
                "fecha": str(r[2]) if r[2] else "",
                "monto_total": float(r[3]) if r[3] else 0.0,
                "moneda": r[4] if r[4] else "",
            }
            for r in db.execute(q, params).fetchall()
        ]
    finally:
        db.close()


def build_producer_price_analysis(
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Price analysis per product for producer purchases from iDempiere."""
    db = _get_session(date_from=date_from, date_to=date_to, anio=anio)
    try:
        conditions = [
            "o.issotrx = 'N'",
            "o.docstatus IN ('CO', 'CL')",
            "o.isactive = 'Y'",
            # Only real agricultural producers (exclude internal orgs like INPROA)
            "bp.codigoproductor IS NOT NULL",
            "bp.codigoproductor != ''",
        ]
        params: dict = {}
        _add_exclude_internal_orgs_filter(conditions, params, "bp")
        _add_org_filter(conditions, params, org_ids, "o")
        _add_date_filter(conditions, params, date_from, date_to, None, anio, "o.dateordered")

        where = " AND ".join(conditions)

        q = text(
            f"SELECT p.name AS producto, "
            f"MIN(ol.priceactual) AS precio_min, "
            f"COALESCE(SUM(ol.linenetamt) / NULLIF(SUM(ol.qtyordered), 0), 0) AS precio_promedio, "
            f"MAX(ol.priceactual) AS precio_max, "
            f"COUNT(DISTINCT o.c_order_id) AS compras "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_orderline ol ON o.c_order_id = ol.c_order_id "
            f"JOIN adempiere.m_product p ON ol.m_product_id = p.m_product_id "
            f"JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY p.name ORDER BY compras DESC LIMIT 20"
        )
        return [
            {
                "producto": r[0],
                "precio_min": float(r[1]) if r[1] else 0.0,
                "precio_promedio": float(r[2]) if r[2] else 0.0,
                "precio_max": float(r[3]) if r[3] else 0.0,
                "compras": r[4],
            }
            for r in db.execute(q, params).fetchall()
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# COMPRAS INSUMOS (Supply Purchases)
# ---------------------------------------------------------------------------

def build_supply_purchases(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
) -> dict:
    """Supply purchases from iDempiere: purchase invoices (issotrx='N').

    When no currency filter is specified, separates results by currency
    to avoid mixing VES and USD in totals and rankings.
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")
        _add_currency_filter(conditions, params, currency_ids, "i")

        cur_label = _currency_label("i")
        where = " AND ".join(conditions)

        # Totals separated by currency
        totals_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(DISTINCT i.c_invoice_id) AS total_facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total_monto "
            f"FROM adempiere.c_invoice i WHERE {where} "
            f"GROUP BY {cur_label} ORDER BY total_monto DESC"
        )
        totals_rows = db.execute(totals_q, params).fetchall()
        totales_por_moneda = [
            {"moneda": r[0], "total_facturas": r[1], "total_monto": float(r[2])}
            for r in totals_rows
        ]
        totals = {
            "total_facturas": sum(r["total_facturas"] for r in totales_por_moneda),
            "total_monto_mixto": sum(r["total_monto"] for r in totales_por_moneda),
            "por_moneda": totales_por_moneda,
        }

        # By supplier (top 20) — include currency column
        by_supplier_q = text(
            f"SELECT bp.name AS proveedor, "
            f"{cur_label} AS moneda, "
            f"COUNT(DISTINCT i.c_invoice_id) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name, {cur_label} ORDER BY total DESC LIMIT 20"
        )
        by_supplier = [
            {"proveedor": r[0], "moneda": r[1], "facturas": r[2], "total": float(r[3])}
            for r in db.execute(by_supplier_q, params).fetchall()
        ]

        # By month — include currency column
        by_month_q = text(
            f"SELECT EXTRACT(YEAR FROM i.dateinvoiced)::int AS anio, "
            f"EXTRACT(MONTH FROM i.dateinvoiced)::int AS mes, "
            f"{cur_label} AS moneda, "
            f"COUNT(DISTINCT i.c_invoice_id) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total "
            f"FROM adempiere.c_invoice i WHERE {where} "
            f"GROUP BY EXTRACT(YEAR FROM i.dateinvoiced), "
            f"EXTRACT(MONTH FROM i.dateinvoiced), {cur_label} "
            f"ORDER BY anio, mes, moneda"
        )
        by_month = [
            {"anio": r[0], "mes": r[1], "moneda": r[2], "facturas": r[3], "total": float(r[4])}
            for r in db.execute(by_month_q, params).fetchall()
        ]

        # By product (top 20) — include currency column
        by_product_q = text(
            f"SELECT p.value AS codigo, p.name AS producto, "
            f"{cur_label} AS moneda, "
            f"COALESCE(SUM(il.linenetamt), 0) AS total "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id "
            f"JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id "
            f"WHERE {where} "
            f"GROUP BY p.value, p.name, {cur_label} ORDER BY total DESC LIMIT 20"
        )
        by_product = [
            {"codigo": r[0], "producto": r[1], "moneda": r[2], "total": float(r[3])}
            for r in db.execute(by_product_q, params).fetchall()
        ]

        # Determine currency label for the agent
        if currency_ids:
            _VES = [205]
            currency_label = "USD" if currency_ids != _VES else "Bs."
        else:
            currency_label = "Todas las monedas (separado por Bs. y USD)"

        return {
            "anio": anio,
            "mes": mes,
            "moneda": currency_label,
            "totales": totals,
            "por_proveedor": by_supplier,
            "por_mes": by_month,
            "por_producto": by_product,
        }
    finally:
        db.close()


def build_product_purchase_history(
    product_search: str,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
    org_name: str | None = None,
) -> list[dict]:
    """Purchase history for a specific product from iDempiere.

    Searches by product code (value) or name. Returns recent purchase invoices
    for that product with supplier, quantity, unit price, and total.
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")

        # Match by product value (code) or name (word-based for text searches)
        _add_product_search_filter(conditions, params, product_search, prefix="search")

        where = " AND ".join(conditions)

        cur_label = _currency_label("i")
        q = text(
            f"SELECT p.value AS codigo_producto, p.name AS producto, "
            f"bp.name AS proveedor, i.documentno AS factura, "
            f"i.dateinvoiced AS fecha, "
            f"il.qtyinvoiced AS cantidad, "
            f"il.priceactual AS precio_unitario, "
            f"il.linenetamt AS total_linea, "
            f"{cur_label} AS moneda "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id "
            f"JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"ORDER BY i.dateinvoiced DESC "
            f"LIMIT 50"
        )
        rows = db.execute(q, params).fetchall()
        return [
            {
                "codigo_producto": r[0],
                "producto": r[1],
                "proveedor": r[2],
                "factura": r[3],
                "fecha": r[4].isoformat() if r[4] else None,
                "cantidad": float(r[5]),
                "precio_unitario": float(r[6]),
                "total_linea": float(r[7]),
                "moneda": r[8],
            }
            for r in rows
        ]
    finally:
        db.close()


def build_pending_purchase_orders(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
    product_search: str | None = None,
) -> dict:
    """Pending purchase orders from iDempiere c_order (issotrx='N').

    Only includes orders NOT yet completed: drafts (DR) and in-progress (IP).
    CO (completed) orders are NOT pending — they have already been processed.
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "o.issotrx = 'N'",
            "o.isactive = 'Y'",
            "o.docstatus IN ('DR', 'IP')",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "o")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "o.dateordered")
        _add_currency_filter(conditions, params, currency_ids, "o")

        if product_search:
            conditions.append(
                "EXISTS (SELECT 1 FROM adempiere.c_orderline ol2 "
                "JOIN adempiere.m_product p2 ON ol2.m_product_id = p2.m_product_id "
                "WHERE ol2.c_order_id = o.c_order_id "
                "AND (p2.name ILIKE :po_prod OR p2.value ILIKE :po_prod))"
            )
            params["po_prod"] = f"%{product_search}%"

        cur_label = _currency_label("o")
        where = " AND ".join(conditions)

        # Totals separated by currency
        totals_q = text(
            f"SELECT {cur_label} AS moneda, "
            f"COUNT(DISTINCT o.c_order_id) AS total_ordenes, "
            f"COALESCE(SUM(o.grandtotal), 0) AS total_monto "
            f"FROM adempiere.c_order o WHERE {where} "
            f"GROUP BY {cur_label} ORDER BY total_monto DESC"
        )
        totals_rows = db.execute(totals_q, params).fetchall()
        totales_por_moneda = [
            {"moneda": r[0], "total_ordenes": r[1], "total_monto": float(r[2])}
            for r in totals_rows
        ]
        totals = {
            "total_ordenes": sum(r["total_ordenes"] for r in totales_por_moneda),
            "total_monto_mixto": sum(r["total_monto"] for r in totales_por_moneda),
            "por_moneda": totales_por_moneda,
        }

        # By status — include currency
        by_status_q = text(
            f"SELECT "
            f"CASE o.docstatus "
            f"  WHEN 'DR' THEN 'Borrador' "
            f"  WHEN 'IP' THEN 'En Proceso' "
            f"  ELSE o.docstatus END AS estado, "
            f"{cur_label} AS moneda, "
            f"COUNT(DISTINCT o.c_order_id) AS ordenes, "
            f"COALESCE(SUM(o.grandtotal), 0) AS total "
            f"FROM adempiere.c_order o WHERE {where} "
            f"GROUP BY o.docstatus, {cur_label} ORDER BY total DESC"
        )
        by_status = [
            {"estado": r[0], "moneda": r[1], "ordenes": r[2], "total": float(r[3])}
            for r in db.execute(by_status_q, params).fetchall()
        ]

        # By supplier (top 20) — include currency
        by_supplier_q = text(
            f"SELECT bp.name AS proveedor, "
            f"{cur_label} AS moneda, "
            f"COUNT(DISTINCT o.c_order_id) AS ordenes, "
            f"COALESCE(SUM(o.grandtotal), 0) AS total "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name, {cur_label} ORDER BY total DESC LIMIT 20"
        )
        by_supplier = [
            {"proveedor": r[0], "moneda": r[1], "ordenes": r[2], "total": float(r[3])}
            for r in db.execute(by_supplier_q, params).fetchall()
        ]

        # Recent orders detail (last 30)
        detail_q = text(
            f"SELECT o.documentno, o.dateordered, "
            f"bp.name AS proveedor, "
            f"CASE o.docstatus "
            f"  WHEN 'DR' THEN 'Borrador' "
            f"  WHEN 'IP' THEN 'En Proceso' "
            f"  ELSE o.docstatus END AS estado, "
            f"o.grandtotal, "
            f"COALESCE(org.name, '') AS organizacion, "
            f"{cur_label} AS moneda "
            f"FROM adempiere.c_order o "
            f"JOIN adempiere.c_bpartner bp ON o.c_bpartner_id = bp.c_bpartner_id "
            f"LEFT JOIN adempiere.ad_org org ON o.ad_org_id = org.ad_org_id "
            f"WHERE {where} "
            f"ORDER BY o.dateordered DESC LIMIT 30"
        )
        detail = [
            {
                "documento": r[0],
                "fecha": r[1].isoformat() if r[1] else None,
                "proveedor": r[2],
                "estado": r[3],
                "monto": float(r[4]) if r[4] else 0.0,
                "organizacion": r[5],
                "moneda": r[6],
            }
            for r in db.execute(detail_q, params).fetchall()
        ]

        return {
            "anio": anio,
            "mes": mes,
            "totales": totals,
            "por_estado": by_status,
            "por_proveedor": by_supplier,
            "detalle_ordenes": detail,
        }
    finally:
        db.close()


def build_supplier_price_comparison(
    product_search: str,
    org_ids: list[int] | None = None,
    anio: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    org_name: str | None = None,
) -> list[dict]:
    """Compare prices from different suppliers for a specific product.

    Returns min, avg, max price per supplier with last purchase date.
    """
    db = _get_session(date_from=date_from, date_to=date_to, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_org_name_filter(conditions, params, org_name, "i")
        _add_date_filter(conditions, params, date_from, date_to, None, anio, "i.dateinvoiced")
        _add_product_search_filter(conditions, params, product_search, prefix="cmp")

        where = " AND ".join(conditions)

        cur_label = _currency_label("i")
        q = text(
            f"SELECT bp.name AS proveedor, "
            f"p.name AS producto, "
            f"{cur_label} AS moneda, "
            f"COUNT(*) AS compras, "
            f"MIN(il.priceactual) AS precio_minimo, "
            f"AVG(il.priceactual) AS precio_promedio, "
            f"MAX(il.priceactual) AS precio_maximo, "
            f"MAX(i.dateinvoiced) AS ultima_compra, "
            f"SUM(il.qtyinvoiced) AS cantidad_total "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_invoiceline il ON i.c_invoice_id = il.c_invoice_id "
            f"JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {where} "
            f"GROUP BY bp.name, p.name, {cur_label} "
            f"ORDER BY moneda, precio_promedio ASC "
            f"LIMIT 30"
        )
        rows = db.execute(q, params).fetchall()
        return [
            {
                "proveedor": r[0],
                "producto": r[1],
                "moneda": r[2],
                "compras": r[3],
                "precio_minimo": float(r[4]) if r[4] else 0.0,
                "precio_promedio": float(r[5]) if r[5] else 0.0,
                "precio_maximo": float(r[6]) if r[6] else 0.0,
                "ultima_compra": r[7].isoformat() if r[7] else None,
                "cantidad_total": float(r[8]) if r[8] else 0.0,
            }
            for r in rows
        ]
    finally:
        db.close()


def build_purchase_payment_status(
    mes: int | None = None,
    anio: int | None = None,
    org_ids: list[int] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    currency_ids: list[int] | None = None,
) -> dict:
    """Purchase invoice payment status from iDempiere.

    Shows paid vs unpaid purchase invoices (c_invoice where issotrx='N').
    """
    db = _get_session(date_from=date_from, date_to=date_to, mes=mes, anio=anio)
    try:
        conditions = [
            "i.issotrx = 'N'",
            "i.docstatus IN ('CO', 'CL')",
            "i.isactive = 'Y'",
        ]
        params: dict = {}
        _add_org_filter(conditions, params, org_ids, "i")
        _add_date_filter(conditions, params, date_from, date_to, mes, anio, "i.dateinvoiced")
        _add_currency_filter(conditions, params, currency_ids, "i")

        cur_label = _currency_label("i")
        where = " AND ".join(conditions)

        q = text(
            f"SELECT "
            f"CASE WHEN i.ispaid = 'Y' THEN 'Pagada' ELSE 'Pendiente' END AS estado_pago, "
            f"{cur_label} AS moneda, "
            f"COUNT(*) AS facturas, "
            f"COALESCE(SUM(i.grandtotal), 0) AS total "
            f"FROM adempiere.c_invoice i WHERE {where} "
            f"GROUP BY i.ispaid, {cur_label} ORDER BY total DESC"
        )
        rows = db.execute(q, params).fetchall()
        summary = [
            {"estado_pago": r[0], "moneda": r[1], "facturas": r[2], "total": float(r[3])}
            for r in rows
        ]

        # Overdue unpaid invoices
        overdue_conditions = conditions + [
            "i.ispaid = 'N'",
            "i.dateinvoiced + COALESCE("
            "  (SELECT pt.netdays FROM adempiere.c_paymentterm pt "
            "   WHERE pt.c_paymentterm_id = i.c_paymentterm_id), 30"
            ") < CURRENT_DATE",
        ]
        overdue_where = " AND ".join(overdue_conditions)

        overdue_q = text(
            f"SELECT bp.name AS proveedor, "
            f"i.documentno, i.dateinvoiced, i.grandtotal, "
            f"CURRENT_DATE - i.dateinvoiced AS dias, "
            f"{cur_label} AS moneda "
            f"FROM adempiere.c_invoice i "
            f"JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id "
            f"WHERE {overdue_where} "
            f"ORDER BY i.grandtotal DESC LIMIT 20"
        )
        overdue = [
            {
                "proveedor": r[0],
                "factura": r[1],
                "fecha": r[2].isoformat() if r[2] else None,
                "monto": float(r[3]) if r[3] else 0.0,
                "dias_desde_factura": r[4],
                "moneda": r[5],
            }
            for r in db.execute(overdue_q, params).fetchall()
        ]

        return {
            "resumen_pago": summary,
            "facturas_vencidas": overdue,
        }
    finally:
        db.close()


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
    # Always use iDempiere live — local DB fact_acct only has data up to 2021
    db = IdempiereSession()
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
    # Always use iDempiere live — local DB fact_acct only has data up to 2021
    db = IdempiereSession()
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
# INVENTARIO (Inventory / Stock)
# ---------------------------------------------------------------------------

def build_inventory_stock(
    org_ids: list[int] | None = None,
    product_search: str | None = None,
    category_search: str | None = None,
    warehouse_search: str | None = None,
    org_name: str | None = None,
) -> dict:
    """Inventory stock from iDempiere m_storageonhand.

    m_storageonhand has multiple rows per product (one per lot/batch via
    m_attributesetinstance_id), so we SUM(qtyonhand) grouped by product.

    JOIN chain:
        m_storageonhand → m_locator → m_warehouse → ad_org
        m_storageonhand → m_product → m_product_category
    """
    db = IdempiereSession()
    try:
        conditions = ["s.isactive = 'Y'", "s.qtyonhand <> 0"]
        params: dict = {}

        # Org filter on warehouse org
        if org_name:
            _add_org_name_filter(conditions, params, org_name, "w")
        elif org_ids:
            placeholders = ", ".join(f":org_{i}" for i in range(len(org_ids)))
            conditions.append(f"w.ad_org_id IN ({placeholders})")
            for i, org_id in enumerate(org_ids):
                params[f"org_{i}"] = org_id

        if product_search:
            _add_product_search_filter(conditions, params, product_search)

        if category_search:
            conditions.append("pc.name ILIKE :cat_search")
            params["cat_search"] = f"%{category_search}%"

        if warehouse_search:
            conditions.append("w.name ILIKE :wh_search")
            params["wh_search"] = f"%{warehouse_search}%"

        where = " AND ".join(conditions)

        # ── Summary by organization ──
        by_org_q = text(
            f"SELECT COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"COUNT(DISTINCT p.m_product_id) AS productos, "
            f"SUM(s.qtyonhand) AS cantidad_total "
            f"FROM adempiere.m_storageonhand s "
            f"JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id "
            f"JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id "
            f"JOIN adempiere.ad_org o ON w.ad_org_id = o.ad_org_id "
            f"JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id "
            f"LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id "
            f"WHERE {where} "
            f"GROUP BY o.name ORDER BY cantidad_total DESC"
        )
        by_org = [
            {
                "organizacion": r[0],
                "productos": r[1],
                "cantidad_total": float(r[2]) if r[2] else 0.0,
            }
            for r in db.execute(by_org_q, params).fetchall()
        ]

        total_products = sum(r["productos"] for r in by_org)
        total_qty = sum(r["cantidad_total"] for r in by_org)

        # ── Summary by category ──
        by_cat_q = text(
            f"SELECT COALESCE(pc.name, 'Sin Categoría') AS categoria, "
            f"COUNT(DISTINCT p.m_product_id) AS productos, "
            f"SUM(s.qtyonhand) AS cantidad_total "
            f"FROM adempiere.m_storageonhand s "
            f"JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id "
            f"JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id "
            f"JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id "
            f"LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id "
            f"WHERE {where} "
            f"GROUP BY pc.name ORDER BY cantidad_total DESC LIMIT 20"
        )
        by_cat = [
            {
                "categoria": r[0],
                "productos": r[1],
                "cantidad_total": float(r[2]) if r[2] else 0.0,
            }
            for r in db.execute(by_cat_q, params).fetchall()
        ]

        # ── Detail by product (top 50 by quantity) ──
        detail_q = text(
            f"SELECT p.value AS codigo, p.name AS producto, "
            f"COALESCE(pc.name, 'Sin Categoría') AS categoria, "
            f"COALESCE(w.name, 'Sin Almacén') AS almacen, "
            f"COALESCE(o.name, 'Sin Org') AS organizacion, "
            f"SUM(s.qtyonhand) AS cantidad, "
            f"COALESCE(u.name, '-') AS unidad "
            f"FROM adempiere.m_storageonhand s "
            f"JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id "
            f"JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id "
            f"JOIN adempiere.ad_org o ON w.ad_org_id = o.ad_org_id "
            f"JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id "
            f"LEFT JOIN adempiere.m_product_category pc ON p.m_product_category_id = pc.m_product_category_id "
            f"LEFT JOIN adempiere.c_uom u ON p.c_uom_id = u.c_uom_id "
            f"WHERE {where} "
            f"GROUP BY p.value, p.name, pc.name, w.name, o.name, u.name "
            f"ORDER BY cantidad DESC LIMIT 50"
        )
        detail = [
            {
                "codigo": r[0],
                "producto": r[1],
                "categoria": r[2],
                "almacen": r[3],
                "organizacion": r[4],
                "cantidad": float(r[5]) if r[5] else 0.0,
                "unidad": r[6],
            }
            for r in db.execute(detail_q, params).fetchall()
        ]

        return {
            "totales": {
                "productos_con_stock": total_products,
                "cantidad_total": total_qty,
            },
            "filtros": {
                "producto": product_search,
                "categoria": category_search,
                "almacen": warehouse_search,
            },
            "por_organizacion": by_org,
            "por_categoria": by_cat,
            "detalle_productos": detail,
        }
    finally:
        db.close()

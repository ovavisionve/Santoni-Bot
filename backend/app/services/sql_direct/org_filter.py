"""Organization filter enforcement for SQL Direct.

Blacklist strategy: exclude known iDempiere demo orgs, include everything else.
"""

import logging
import re

logger = logging.getLogger("santonibot.sql_direct")

# Tablas donde aplica el filtro de orgs demo (tienen ad_org_id y datos
# financieros contaminados por orgs de fábrica de iDempiere).
ORG_ENFORCEMENT_TABLES = {
    "c_invoice", "c_payment", "c_order", "fact_acct",
}

# Nombres de orgs DEMO de iDempiere (a excluir explícitamente).
#
# 14/Abr/2026: cambio de estrategia whitelist → blacklist. Las 7 orgs reales
# de Santoni eran una lista cerrada, pero había orgs reales DURMIENTES que
# el whitelist ocultaba sin avisar (Ocean Equipment Industries LLC con
# $114,625 USD en marzo 2025, Venecauchos con 2,607 facturas históricas,
# Agro Import C.A. con 498 facturas).
#
# La blacklist lista solo las demos estándar de iDempiere (HQ, Store*,
# Furniture, Fertilizer, "*" system-wide). Cualquier otra org del ERP se
# considera real.
IDEMPIERE_DEMO_ORGS = (
    "HQ",
    "Fertilizer",
    "Furniture",
    "Store Central",
    "Store East",
    "Store North",
    "Store South",
    "Store West",
    "Stores",
    "*",
)


def build_santoni_org_filter(alias: str) -> str:
    """Construye el WHERE clause para excluir orgs demo de iDempiere."""
    names_sql = " AND ".join(
        f"name NOT ILIKE '{n}'" for n in IDEMPIERE_DEMO_ORGS
    )
    return (
        f"{alias}.ad_org_id IN (SELECT ad_org_id FROM adempiere.ad_org WHERE "
        f"isactive = 'Y' AND {names_sql})"
    )


def enforce_org_filter(sql: str) -> tuple[str, bool]:
    """Inyecta filtro de orgs reales de Santoni cuando falta (PROTECCIÓN DEFENSIVA).

    Se mantiene activa como PROTECCIÓN FUTURA para escenarios donde orgs demo
    contaminen los datos (restore de dump, org de prueba, migración de ERP).

    Criterios para inyectar:
      - El SQL toca una de las tablas financieras (ORG_ENFORCEMENT_TABLES)
      - Usa un alias identificable (ej. `FROM adempiere.c_invoice i`)
      - NO tiene ya un filtro `ad_org_id IN (...)` o `ad_org_id = N` en el WHERE

    Returns (sql_modificado, se_inyecto_flag).
    """
    sql_upper = sql.upper()

    where_match = re.search(r"\bWHERE\b", sql_upper)
    if where_match:
        where_and_after = sql_upper[where_match.end():]
        for tok in ("GROUP BY", "ORDER BY", "LIMIT"):
            m = re.search(rf"\b{tok}\b", where_and_after)
            if m:
                where_and_after = where_and_after[:m.start()]
                break
        if re.search(r"\bAD_ORG_ID\s*(=|IN|<>|!=)", where_and_after):
            return sql, False

    alias_to_enforce: str | None = None
    for table in ORG_ENFORCEMENT_TABLES:
        m = re.search(
            rf"FROM\s+adempiere\.{table}\s+(?:AS\s+)?(\w+)\b",
            sql,
            re.IGNORECASE,
        )
        if m:
            alias_to_enforce = m.group(1)
            break

    if not alias_to_enforce:
        return sql, False

    org_filter = build_santoni_org_filter(alias_to_enforce)
    insertion = f" AND {org_filter}\n"

    cut_tokens = ["GROUP BY", "ORDER BY", "LIMIT"]
    cut_pos = len(sql)
    for tok in cut_tokens:
        m = re.search(rf"\b{tok}\b", sql, re.IGNORECASE)
        if m and m.start() < cut_pos:
            cut_pos = m.start()

    modified = sql[:cut_pos].rstrip() + insertion + sql[cut_pos:]
    return modified, True

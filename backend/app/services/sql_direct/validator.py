"""SQL validation for SQL Direct — security and whitelist enforcement."""

import re

from .catalog import ALLOWED_TABLES

# Palabras prohibidas en SQL
_FORBIDDEN = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXECUTE|EXEC)\b',
    re.IGNORECASE,
)


def validate_sql(sql: str) -> tuple[bool, str]:
    """Validate that the SQL is safe to execute.

    Returns (is_valid, error_message_or_cleaned_sql).
    """
    sql_clean = sql.strip().rstrip(";")

    sql_upper = sql_clean.upper()
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "Solo se permiten queries SELECT (o WITH ... SELECT)"

    if _FORBIDDEN.search(sql_clean):
        match = _FORBIDDEN.search(sql_clean)
        return False, f"Operación prohibida: {match.group()}"

    # Remove EXTRACT(...FROM...) to avoid false positives on table detection
    sql_no_extract = re.sub(r'EXTRACT\s*\([^)]*\)', 'EXTRACT_REMOVED', sql_clean, flags=re.IGNORECASE)

    # Extract CTE names (temporary tables valid during execution)
    cte_names = set()
    for m in re.finditer(
        r'\bWITH\s+(?:RECURSIVE\s+)?(\w+)\s+AS\s*\(',
        sql_no_extract, re.IGNORECASE,
    ):
        cte_names.add(m.group(1).lower())
    for m in re.finditer(r'\)\s*,\s*(\w+)\s+AS\s*\(', sql_no_extract, re.IGNORECASE):
        cte_names.add(m.group(1).lower())
    if sql_no_extract.upper().lstrip().startswith("WITH"):
        for m in re.finditer(
            r'(?:^|[,\s])(\w+)\s+AS\s*\(\s*(?:SELECT|WITH)',
            sql_no_extract, re.IGNORECASE,
        ):
            name = m.group(1).lower()
            if name not in ("with", "select", "recursive", "as", "adempiere"):
                cte_names.add(name)

    # Find table references and check against whitelist
    table_refs = re.findall(
        r'(?:adempiere\.|\bFROM\s+|\bJOIN\s+)(\w+)',
        sql_no_extract,
        re.IGNORECASE,
    )
    for table in table_refs:
        table_lower = table.lower()
        if table_lower in ("adempiere", "extract_removed", "lateral", "select", "as"):
            continue
        if table_lower in cte_names:
            continue
        if table_lower not in ALLOWED_TABLES:
            return False, f"Tabla no permitida: {table_lower}. Solo se pueden consultar views lve_* y tablas del catálogo."

    # Must have LIMIT
    if "LIMIT" not in sql_clean.upper():
        sql_clean += " LIMIT 500"

    return True, sql_clean

"""Schema discovery, relationships, profiling, and sampling helpers."""

import logging
from typing import Any

from sqlalchemy import text

from .constants import DATE_COLUMNS, PROFILE_COLUMNS, get_all_relevant_tables

logger = logging.getLogger("santonibot.data_catalog")


def discover_schema(session, errors: list[str]) -> dict[str, dict]:
    """Descubre el schema de las tablas relevantes en iDempiere.

    Retorna: {table_name: {columns: [...], row_count: int, ...}}
    """
    tables = get_all_relevant_tables()
    schema: dict[str, dict] = {}

    for table_name in sorted(tables):
        try:
            col_query = text("""
                SELECT column_name, data_type, is_nullable,
                       character_maximum_length, numeric_precision
                FROM information_schema.columns
                WHERE table_schema = 'adempiere'
                  AND table_name = :table_name
                ORDER BY ordinal_position
            """)
            cols_result = session.execute(col_query, {"table_name": table_name})
            columns = []
            for row in cols_result:
                columns.append({
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[2] == "YES",
                    "max_length": row[3],
                    "precision": row[4],
                })

            if not columns:
                logger.debug("Tabla '%s' no encontrada en schema adempiere", table_name)
                continue

            count_query = text(f"SELECT COUNT(*) FROM adempiere.{table_name}")
            count_result = session.execute(count_query)
            row_count = count_result.scalar() or 0

            schema[table_name] = {
                "columns": columns,
                "row_count": row_count,
                "column_names": [c["name"] for c in columns],
            }

        except Exception as e:
            logger.warning("Error descubriendo schema de '%s': %s", table_name, e)
            errors.append(f"schema_{table_name}: {e}")

    return schema


def discover_relationships(session, errors: list[str]) -> list[dict]:
    """Descubre foreign keys entre las tablas relevantes."""
    tables = get_all_relevant_tables()
    tables_list = ", ".join(f"'{t}'" for t in tables)

    try:
        fk_query = text(f"""
            SELECT
                tc.table_name AS source_table,
                kcu.column_name AS source_column,
                ccu.table_name AS target_table,
                ccu.column_name AS target_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'adempiere'
              AND tc.table_name IN ({tables_list})
              AND ccu.table_name IN ({tables_list})
            ORDER BY tc.table_name, kcu.column_name
        """)
        result = session.execute(fk_query)
        relationships = []
        for row in result:
            relationships.append({
                "source_table": row[0],
                "source_column": row[1],
                "target_table": row[2],
                "target_column": row[3],
            })
        return relationships

    except Exception as e:
        logger.warning("Error descubriendo relaciones: %s", e)
        errors.append(f"relationships: {e}")
        return []


def _profile_column_values(session, table: str, column: str, limit: int = 50) -> list:
    """Obtiene valores distintos de una columna (hasta limit)."""
    try:
        query = text(f"""
            SELECT {column}, COUNT(*) as cnt
            FROM adempiere.{table}
            WHERE {column} IS NOT NULL
            GROUP BY {column}
            ORDER BY cnt DESC
            LIMIT :limit
        """)
        result = session.execute(query, {"limit": limit})
        return [{"value": str(row[0]), "count": row[1]} for row in result]
    except Exception as e:
        logger.debug("Error profiling %s.%s: %s", table, column, e)
        return []


def _profile_date_range(session, table: str, date_column: str) -> dict | None:
    """Obtiene el rango de fechas de una columna."""
    try:
        query = text(f"""
            SELECT
                MIN({date_column}) AS min_date,
                MAX({date_column}) AS max_date,
                COUNT(DISTINCT DATE_TRUNC('month', {date_column})) AS months_count
            FROM adempiere.{table}
            WHERE {date_column} IS NOT NULL
        """)
        result = session.execute(query)
        row = result.fetchone()
        if row and row[0]:
            return {
                "min_date": str(row[0]),
                "max_date": str(row[1]),
                "months_with_data": row[2],
            }
    except Exception as e:
        logger.debug("Error profiling date range %s.%s: %s", table, date_column, e)
    return None


def profile_data(session, schema: dict[str, dict]) -> dict[str, dict]:
    """Perfila datos de las tablas: valores distintos, rangos de fechas, etc."""
    profiles: dict[str, dict] = {}

    for table_name, table_info in schema.items():
        table_profile: dict[str, Any] = {"columns": {}}

        if table_name in PROFILE_COLUMNS:
            for col in PROFILE_COLUMNS[table_name]:
                if col in table_info["column_names"]:
                    values = _profile_column_values(session, table_name, col)
                    if values:
                        table_profile["columns"][col] = values

        if table_name in DATE_COLUMNS:
            date_col = DATE_COLUMNS[table_name]
            if date_col in table_info["column_names"]:
                date_range = _profile_date_range(session, table_name, date_col)
                if date_range:
                    table_profile["date_range"] = date_range

        if table_profile["columns"] or "date_range" in table_profile:
            profiles[table_name] = table_profile

    return profiles


def sample_data(session, schema: dict[str, dict], sample_size: int = 5) -> dict[str, list]:
    """Obtiene filas de ejemplo de cada tabla (las más recientes si hay fecha)."""
    samples: dict[str, list] = {}

    for table_name in schema:
        try:
            order_clause = ""
            if table_name in DATE_COLUMNS:
                date_col = DATE_COLUMNS[table_name]
                if date_col in schema[table_name]["column_names"]:
                    order_clause = f"ORDER BY {date_col} DESC NULLS LAST"

            col_names = schema[table_name]["column_names"][:10]
            cols_sql = ", ".join(col_names)

            query = text(
                f"SELECT {cols_sql} FROM adempiere.{table_name} "
                f"{order_clause} LIMIT :limit"
            )
            result = session.execute(query, {"limit": sample_size})
            rows = []
            for row in result:
                row_dict = {}
                for i, col in enumerate(col_names):
                    val = row[i]
                    if val is not None:
                        row_dict[col] = str(val)
                    else:
                        row_dict[col] = None
                rows.append(row_dict)

            if rows:
                samples[table_name] = rows

        except Exception as e:
            logger.debug("Error muestreando %s: %s", table_name, e)

    return samples

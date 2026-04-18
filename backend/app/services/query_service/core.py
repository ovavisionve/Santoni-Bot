"""Core query service: routing, helpers, schema."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.database import SessionLocal, IdempiereSession
from app.config import get_settings

logger = logging.getLogger("santonibot.query_service")

"""
Query service for AI agents - routes queries to the correct data source.

- APP_ENV=development → demo tables (internal PostgreSQL, fake data for QA)
- APP_ENV=production  → iDempiere tables (192.168.1.73, real data)

Agents import from this module and are unaware of the data source.
"""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import text

from app.database import SessionLocal, IdempiereSession
from app.config import get_settings

logger = logging.getLogger("santonibot.query_service")


def _is_production() -> bool:
    """Check if we should use iDempiere (production) or demo tables."""
    env = get_settings().app_env
    is_prod = env == "production"
    logger.info("_is_production: APP_ENV=%s → %s", env, is_prod)
    return is_prod


# ---------------------------------------------------------------------------
# Helpers (shared)
# ---------------------------------------------------------------------------

def _convert_value(val):
    """Convert non-JSON-serializable types to serializable ones."""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, date):
        return val.isoformat()
    return val


def _rows_to_dicts(rows, columns) -> list[dict]:
    """Convert SQLAlchemy result rows to a list of dicts with clean values."""
    return [
        {col: _convert_value(row[i]) for i, col in enumerate(columns)}
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Core query function (generic SQL execution)
# ---------------------------------------------------------------------------

def execute_demo_query(query: str, params: dict | None = None) -> list[dict]:
    """Execute a read-only SELECT query against the active data source.
    In development: queries demo_* tables in internal DB.
    In production: queries adempiere.* tables in iDempiere."""
    q = query.strip().rstrip(";")
    if not q.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    if _is_production():
        from app.services.idempiere_queries import execute_idempiere_query
        return execute_idempiere_query(query, params)

    db = SessionLocal()
    try:
        result = db.execute(text(q), params or {})
        columns = list(result.keys())
        rows = result.fetchall()
        return _rows_to_dicts(rows, columns)
    finally:
        db.close()


def get_table_schema(table_name: str) -> list[dict]:
    """Get column info for a table."""
    session_class = IdempiereSession if _is_production() else SessionLocal
    schema = "adempiere" if _is_production() else None

    db = session_class()
    try:
        conditions = "table_name = :table_name"
        params = {"table_name": table_name}
        if schema:
            conditions += " AND table_schema = :schema"
            params["schema"] = schema

        result = db.execute(
            text(
                f"SELECT column_name, data_type, is_nullable "
                f"FROM information_schema.columns "
                f"WHERE {conditions} "
                f"ORDER BY ordinal_position"
            ),
            params,
        )
        return [
            {
                "column": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
            }
            for row in result.fetchall()
        ]
    finally:
        db.close()


def get_available_tables() -> list[str]:
    """Return list of available table names."""
    if _is_production():
        db = IdempiereSession()
        try:
            result = db.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'adempiere' "
                    "ORDER BY table_name"
                )
            )
            return [row[0] for row in result.fetchall()]
        finally:
            db.close()

    db = SessionLocal()
    try:
        result = db.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name LIKE 'demo_%' "
                "ORDER BY table_name"
            )
        )
        return [row[0] for row in result.fetchall()]
    finally:
        db.close()



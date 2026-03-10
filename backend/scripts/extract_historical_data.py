#!/usr/bin/env python3
"""
Extractor de datos históricos de iDempiere → DB local de SantoniBot.

Copia TODOS los datos anteriores a la fecha de corte (por defecto 2026-03-01)
desde iDempiere (192.168.1.73) a la base de datos local de SantoniBot
en el schema 'adempiere', de forma que las queries SQL existentes funcionan
sin cambios (misma estructura, mismos nombres de tabla).

Prerequisitos:
  - Ejecutar migración Alembic 004 primero:
      cd /opt/santonibot/backend
      alembic upgrade head

Uso desde Docker:
  docker compose exec backend python scripts/extract_historical_data.py

Uso directo:
  cd backend
  python scripts/extract_historical_data.py [--cutoff 2026-03-01] [--batch-size 10000]

El script es idempotente: TRUNCA las tablas locales antes de insertar.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("extract_historical")

# ── Table definitions ───────────────────────────────────────────────────────
# Each entry: (table_name, date_column_for_filtering_or_None, is_dimension)
# - date_column: if set, only rows with date < cutoff are copied
# - is_dimension: if True, ALL rows are copied regardless of date

REFERENCE_TABLES = [
    "ad_org",
    "c_currency",
    "c_bpartner",
    "c_bp_group",
    "c_salesregion",
    "c_bpartner_location",
    "c_location",
    "c_region",
    "c_city",
    "c_doctype",
    "m_product",
    "m_product_category",
    "m_warehouse",
    "m_locator",
    "c_paymentterm",
    "c_bank",
    "c_bankaccount",
    "hr_department",
    "hr_job",
    "hr_concept",
    "hr_payroll",
    "hr_employee",
    "c_elementvalue",
    "c_element",
    "c_acctschema",
    "c_period",
]

# Transaction tables: (table_name, date_column, parent_table, parent_fk)
# parent_table/parent_fk: for child tables, filter by parent's date
TRANSACTION_TABLES = [
    ("c_invoice", "dateinvoiced", None, None),
    ("c_invoiceline", None, "c_invoice", "c_invoice_id"),
    ("c_payment", "datetrx", None, None),
    ("c_allocationline", None, None, None),  # copied fully, small table
    ("c_order", "dateordered", None, None),
    ("c_orderline", None, "c_order", "c_order_id"),
    ("m_inout", "movementdate", None, None),
    ("m_inoutline", None, "m_inout", "m_inout_id"),
    ("fact_acct", "dateacct", None, None),
    ("hr_process", "dateacct", None, None),
    ("hr_movement", None, "hr_process", "hr_process_id"),
    ("m_storageonhand", None, None, None),  # snapshot, copy fully
]


def get_idempiere_engine():
    """Create engine for iDempiere (source)."""
    host = os.environ.get("IDEMPIERE_DB_HOST", "192.168.1.73")
    port = os.environ.get("IDEMPIERE_DB_PORT", "5432")
    dbname = os.environ.get("IDEMPIERE_DB_NAME", "idempiere_produccion")
    user = os.environ.get("IDEMPIERE_DB_USER", "ova")
    password = os.environ.get("IDEMPIERE_DB_PASSWORD", "")

    if not password:
        for env_path in [
            os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
            os.path.join(os.path.dirname(__file__), "..", ".env"),
        ]:
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("IDEMPIERE_DB_PASSWORD="):
                            password = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
                if password:
                    break

    url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    logger.info("iDempiere: %s:%s/%s (user: %s)", host, port, dbname, user)
    return create_engine(url, pool_pre_ping=True)


def get_local_engine():
    """Create engine for local SantoniBot DB (destination)."""
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    dbname = os.environ.get("POSTGRES_DB", "santonibot")
    user = os.environ.get("POSTGRES_USER", "santonibot")
    password = os.environ.get("POSTGRES_PASSWORD", "changeme")

    if not password or password == "changeme":
        for env_path in [
            os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
            os.path.join(os.path.dirname(__file__), "..", ".env"),
        ]:
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("POSTGRES_PASSWORD="):
                            password = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
                if password and password != "changeme":
                    break

    url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    logger.info("Local DB: %s:%s/%s (user: %s)", host, port, dbname, user)
    return create_engine(url, pool_pre_ping=True)


def get_local_table_columns(local_engine, table_name: str) -> list[str]:
    """Get column names from the local adempiere.table_name."""
    with local_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'adempiere' AND table_name = :t "
            "ORDER BY ordinal_position"
        ), {"t": table_name})
        return [r[0] for r in result.fetchall()]


def get_source_columns(idempiere_engine, table_name: str) -> list[str]:
    """Get column names from iDempiere's adempiere.table_name."""
    with idempiere_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'adempiere' AND table_name = :t "
            "ORDER BY ordinal_position"
        ), {"t": table_name})
        return [r[0] for r in result.fetchall()]


def copy_reference_table(
    idempiere_engine, local_engine, table_name: str, batch_size: int
) -> int:
    """Copy all rows from a reference/dimension table."""
    local_cols = get_local_table_columns(local_engine, table_name)
    source_cols = get_source_columns(idempiere_engine, table_name)

    # Only copy columns that exist in BOTH source and destination
    cols = [c for c in local_cols if c in source_cols]
    if not cols:
        logger.warning("  No common columns for %s, skipping", table_name)
        return 0

    cols_sql = ", ".join(cols)
    placeholders = ", ".join(f":{c}" for c in cols)

    total = 0
    with idempiere_engine.connect() as src_conn:
        result = src_conn.execute(text(
            f"SELECT {cols_sql} FROM adempiere.{table_name}"
        ))
        rows = result.fetchall()
        col_names = list(result.keys())

    if not rows:
        logger.info("  %s: 0 rows (empty source)", table_name)
        return 0

    # Truncate local table first
    with local_engine.begin() as dst_conn:
        dst_conn.execute(text(f"TRUNCATE adempiere.{table_name} CASCADE"))

        # Insert in batches
        batch = []
        for row in rows:
            record = {cols[i]: row[i] for i in range(len(cols))}
            batch.append(record)
            if len(batch) >= batch_size:
                dst_conn.execute(
                    text(f"INSERT INTO adempiere.{table_name} ({cols_sql}) VALUES ({placeholders})"),
                    batch,
                )
                total += len(batch)
                batch = []
        if batch:
            dst_conn.execute(
                text(f"INSERT INTO adempiere.{table_name} ({cols_sql}) VALUES ({placeholders})"),
                batch,
            )
            total += len(batch)

    return total


def copy_transaction_table(
    idempiere_engine,
    local_engine,
    table_name: str,
    date_column: str | None,
    parent_table: str | None,
    parent_fk: str | None,
    cutoff: str,
    batch_size: int,
) -> int:
    """Copy rows from a transaction table, filtered by date or parent."""
    local_cols = get_local_table_columns(local_engine, table_name)
    source_cols = get_source_columns(idempiere_engine, table_name)

    cols = [c for c in local_cols if c in source_cols]
    if not cols:
        logger.warning("  No common columns for %s, skipping", table_name)
        return 0

    cols_sql = ", ".join(cols)
    placeholders = ", ".join(f":{c}" for c in cols)

    # Build WHERE clause
    where_clause = ""
    params: dict = {}
    if date_column:
        where_clause = f"WHERE {date_column} < :cutoff"
        params["cutoff"] = cutoff
    elif parent_table and parent_fk:
        # Get parent IDs that are before cutoff
        parent_date_col = None
        for t_name, d_col, _, _ in TRANSACTION_TABLES:
            if t_name == parent_table:
                parent_date_col = d_col
                break
        if parent_date_col:
            where_clause = (
                f"WHERE {parent_fk} IN ("
                f"SELECT {parent_fk} FROM adempiere.{parent_table} "
                f"WHERE {parent_date_col} < :cutoff)"
            )
            params["cutoff"] = cutoff
    # else: copy all rows (small tables like c_allocationline, m_storageonhand)

    total = 0
    offset = 0

    # Truncate local table first
    with local_engine.begin() as dst_conn:
        dst_conn.execute(text(f"TRUNCATE adempiere.{table_name} CASCADE"))

    # Read and insert in batches to handle large tables (fact_acct: 7.7M rows)
    while True:
        with idempiere_engine.connect() as src_conn:
            q = f"SELECT {cols_sql} FROM adempiere.{table_name} {where_clause} LIMIT :batch OFFSET :off"
            params["batch"] = batch_size
            params["off"] = offset
            result = src_conn.execute(text(q), params)
            rows = result.fetchall()

        if not rows:
            break

        batch_data = []
        for row in rows:
            record = {cols[i]: row[i] for i in range(len(cols))}
            batch_data.append(record)

        with local_engine.begin() as dst_conn:
            dst_conn.execute(
                text(f"INSERT INTO adempiere.{table_name} ({cols_sql}) VALUES ({placeholders})"),
                batch_data,
            )

        total += len(rows)
        offset += batch_size

        if total % (batch_size * 10) == 0 and total > 0:
            logger.info("    %s: %d rows copied so far...", table_name, total)

        if len(rows) < batch_size:
            break

    return total


def main():
    parser = argparse.ArgumentParser(description="Extractor de datos históricos de iDempiere")
    parser.add_argument(
        "--cutoff",
        default="2026-03-01",
        help="Fecha de corte (YYYY-MM-DD). Solo datos ANTES de esta fecha. Default: 2026-03-01",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Tamaño del batch para INSERT. Default: 5000",
    )
    parser.add_argument(
        "--tables",
        nargs="*",
        default=None,
        help="Tablas específicas a extraer. Default: todas",
    )
    parser.add_argument(
        "--skip-fact-acct",
        action="store_true",
        help="Omitir fact_acct (7.7M registros, muy lento). Útil para pruebas rápidas.",
    )
    args = parser.parse_args()

    cutoff = args.cutoff
    batch_size = args.batch_size

    logger.info("=" * 60)
    logger.info("EXTRACCIÓN DE DATOS HISTÓRICOS DE iDEMPIERE")
    logger.info("Fecha de corte: %s (datos ANTES de esta fecha)", cutoff)
    logger.info("Batch size: %d", batch_size)
    logger.info("=" * 60)

    start_time = time.time()

    # Connect to both databases
    idempiere_engine = get_idempiere_engine()
    local_engine = get_local_engine()

    # Test connections
    try:
        with idempiere_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✓ Conexión a iDempiere OK")
    except Exception as e:
        logger.error("✗ Error conectando a iDempiere: %s", e)
        sys.exit(1)

    try:
        with local_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            # Check schema exists
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'adempiere'"
            ))
            if not result.fetchone():
                logger.error(
                    "✗ Schema 'adempiere' no existe en la DB local. "
                    "Ejecuta: alembic upgrade head"
                )
                sys.exit(1)
        logger.info("✓ Conexión a DB local OK (schema adempiere existe)")
    except Exception as e:
        logger.error("✗ Error conectando a DB local: %s", e)
        sys.exit(1)

    total_rows = 0
    tables_extracted = []

    # ── Step 1: Reference tables ────────────────────────────────────────

    logger.info("\n── TABLAS DE REFERENCIA (copia completa) ──")
    for table in REFERENCE_TABLES:
        if args.tables and table not in args.tables:
            continue
        try:
            t0 = time.time()
            count = copy_reference_table(idempiere_engine, local_engine, table, batch_size)
            elapsed = time.time() - t0
            logger.info("  ✓ %s: %s rows (%.1fs)", table, f"{count:,}", elapsed)
            total_rows += count
            tables_extracted.append(table)
        except Exception as e:
            logger.error("  ✗ %s: ERROR - %s", table, e)

    # ── Step 2: Transaction tables ──────────────────────────────────────

    logger.info("\n── TABLAS TRANSACCIONALES (datos < %s) ──", cutoff)
    for table, date_col, parent, parent_fk in TRANSACTION_TABLES:
        if args.tables and table not in args.tables:
            continue
        if args.skip_fact_acct and table == "fact_acct":
            logger.info("  ⏭ fact_acct: OMITIDO (--skip-fact-acct)")
            continue
        try:
            t0 = time.time()
            count = copy_transaction_table(
                idempiere_engine, local_engine, table,
                date_col, parent, parent_fk, cutoff, batch_size,
            )
            elapsed = time.time() - t0
            logger.info("  ✓ %s: %s rows (%.1fs)", table, f"{count:,}", elapsed)
            total_rows += count
            tables_extracted.append(table)
        except Exception as e:
            logger.error("  ✗ %s: ERROR - %s", table, e)

    # ── Step 3: Record extraction metadata ──────────────────────────────

    duration = int(time.time() - start_time)
    try:
        with local_engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO adempiere._extraction_metadata
                (cutoff_date, tables_extracted, total_rows, duration_seconds, notes)
                VALUES (:cutoff, :tables, :rows, :duration, :notes)
            """), {
                "cutoff": cutoff,
                "tables": tables_extracted,
                "rows": total_rows,
                "duration": duration,
                "notes": f"Extracted at {datetime.now().isoformat()}",
            })
    except Exception as e:
        logger.warning("Could not save extraction metadata: %s", e)

    # ── Summary ─────────────────────────────────────────────────────────

    logger.info("\n" + "=" * 60)
    logger.info("EXTRACCIÓN COMPLETADA")
    logger.info("  Tablas: %d", len(tables_extracted))
    logger.info("  Rows totales: %s", f"{total_rows:,}")
    logger.info("  Duración: %dm %ds", duration // 60, duration % 60)
    logger.info("  Fecha de corte: %s", cutoff)
    logger.info("=" * 60)
    logger.info(
        "\nPróximo paso: Activar datos históricos en .env:\n"
        "  HISTORICAL_DATA_ENABLED=true\n"
        "  HISTORICAL_DATA_CUTOFF=%s\n"
        "Luego reiniciar: docker compose restart backend",
        cutoff,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Sincronización diaria de datos de iDempiere → DB local.

Se ejecuta a las 00:00 (via cron) y copia los datos del día ANTERIOR
desde iDempiere a la DB local (schema adempiere). Así el bot solo
necesita consultar iDempiere para datos del día ACTUAL.

Flujo:
  1. Calcula fecha de ayer (el día que acaba de terminar)
  2. Copia registros transaccionales de ayer a las tablas locales
  3. Actualiza tablas de referencia (nuevos productos, clientes, etc.)
  4. Actualiza snapshots (inventario, saldos bancarios)
  5. Registra metadata de la sincronización

Uso manual:
  docker compose exec backend python scripts/daily_sync.py
  docker compose exec backend python scripts/daily_sync.py --date 2026-03-09

Cron (dentro del contenedor backend):
  0 0 * * * python /app/scripts/daily_sync.py >> /app/logs/daily_sync.log 2>&1
"""

import argparse
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta
from urllib.parse import quote_plus

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("daily_sync")


# ── Tables to sync ──────────────────────────────────────────────────────

# Reference tables: always full refresh (detects new products, clients, etc.)
REFERENCE_TABLES = [
    "ad_org", "c_currency", "c_bpartner", "c_bp_group", "c_salesregion",
    "c_bpartner_location", "c_location", "c_region", "c_city", "c_doctype",
    "m_product", "m_product_category", "m_warehouse", "m_locator",
    "c_paymentterm", "c_bank", "c_bankaccount", "hr_department", "hr_job",
    "hr_concept", "hr_payroll", "hr_employee", "c_elementvalue", "c_element",
    "c_acctschema", "c_period",
]

# Transaction tables: only copy records from the target date
TRANSACTION_TABLES = [
    ("c_invoice", "dateinvoiced"),
    ("c_payment", "datetrx"),
    ("c_order", "dateordered"),
    ("m_inout", "movementdate"),
    ("fact_acct", "dateacct"),
    ("hr_process", "dateacct"),
]

# Child tables: copy based on parent IDs
CHILD_TABLES = [
    ("c_invoiceline", "c_invoice_id", "c_invoice"),
    ("c_orderline", "c_order_id", "c_order"),
    ("m_inoutline", "m_inout_id", "m_inout"),
    ("hr_movement", "hr_process_id", "hr_process"),
]

# Snapshot tables: always full refresh (current state)
SNAPSHOT_TABLES = [
    "m_storageonhand",
    "c_allocationline",
]


def get_engines():
    """Create engines for source (iDempiere) and destination (local)."""
    host = os.environ.get("IDEMPIERE_DB_HOST", "192.168.1.73")
    port = os.environ.get("IDEMPIERE_DB_PORT", "5432")
    dbname = os.environ.get("IDEMPIERE_DB_NAME", "idempiere_produccion")
    user = os.environ.get("IDEMPIERE_DB_USER", "ova")
    password = os.environ.get("IDEMPIERE_DB_PASSWORD", "")

    # Try reading from .env if not in environment
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

    idempiere_url = f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{dbname}"
    idempiere_engine = create_engine(idempiere_url, pool_pre_ping=True)

    lhost = os.environ.get("POSTGRES_HOST", "db")
    lport = os.environ.get("POSTGRES_PORT", "5432")
    ldb = os.environ.get("POSTGRES_DB", "santonibot")
    luser = os.environ.get("POSTGRES_USER", "santonibot")
    lpw = os.environ.get("POSTGRES_PASSWORD", "changeme")

    local_url = f"postgresql://{luser}:{quote_plus(lpw)}@{lhost}:{lport}/{ldb}"
    local_engine = create_engine(local_url, pool_pre_ping=True)

    return idempiere_engine, local_engine


def get_common_columns(idempiere_engine, local_engine, table_name: str) -> list[str]:
    """Get columns that exist in both source and destination."""
    with local_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'adempiere' AND table_name = :t"
        ), {"t": table_name})
        local_cols = {r[0] for r in result.fetchall()}

    with idempiere_engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'adempiere' AND table_name = :t"
        ), {"t": table_name})
        source_cols = {r[0] for r in result.fetchall()}

    return sorted(local_cols & source_cols)


def sync_reference_table(idempiere_engine, local_engine, table: str) -> int:
    """Full refresh of a reference table."""
    cols = get_common_columns(idempiere_engine, local_engine, table)
    if not cols:
        return 0

    cols_sql = ", ".join(cols)
    placeholders = ", ".join(f":{c}" for c in cols)

    with idempiere_engine.connect() as src:
        rows = src.execute(text(f"SELECT {cols_sql} FROM adempiere.{table}")).fetchall()

    if not rows:
        return 0

    with local_engine.begin() as dst:
        dst.execute(text(f"TRUNCATE adempiere.{table} CASCADE"))
        batch = []
        for row in rows:
            batch.append({cols[i]: row[i] for i in range(len(cols))})
            if len(batch) >= 5000:
                dst.execute(
                    text(f"INSERT INTO adempiere.{table} ({cols_sql}) VALUES ({placeholders})"),
                    batch,
                )
                batch = []
        if batch:
            dst.execute(
                text(f"INSERT INTO adempiere.{table} ({cols_sql}) VALUES ({placeholders})"),
                batch,
            )

    return len(rows)


def sync_transaction_day(idempiere_engine, local_engine, table: str,
                         date_col: str, target_date: str) -> int:
    """Copy transaction records for a specific day (INSERT, no duplicates)."""
    cols = get_common_columns(idempiere_engine, local_engine, table)
    if not cols:
        return 0

    cols_sql = ", ".join(cols)
    placeholders = ", ".join(f":{c}" for c in cols)
    next_day = (datetime.strptime(target_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    # First delete any existing records for this day (idempotent)
    with local_engine.begin() as dst:
        dst.execute(text(
            f"DELETE FROM adempiere.{table} WHERE {date_col} >= :d1 AND {date_col} < :d2"
        ), {"d1": target_date, "d2": next_day})

    # Copy from iDempiere
    with idempiere_engine.connect() as src:
        rows = src.execute(text(
            f"SELECT {cols_sql} FROM adempiere.{table} "
            f"WHERE {date_col} >= :d1 AND {date_col} < :d2"
        ), {"d1": target_date, "d2": next_day}).fetchall()

    if not rows:
        return 0

    with local_engine.begin() as dst:
        batch = [{cols[i]: row[i] for i in range(len(cols))} for row in rows]
        dst.execute(
            text(f"INSERT INTO adempiere.{table} ({cols_sql}) VALUES ({placeholders})"),
            batch,
        )

    return len(rows)


def sync_child_table(idempiere_engine, local_engine, child_table: str,
                     fk_col: str, parent_table: str, parent_date_col: str,
                     target_date: str) -> int:
    """Copy child records whose parent was created on target_date."""
    cols = get_common_columns(idempiere_engine, local_engine, child_table)
    if not cols:
        return 0

    cols_sql = ", ".join(cols)
    placeholders = ", ".join(f":{c}" for c in cols)
    next_day = (datetime.strptime(target_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    # Get parent IDs for target date
    with idempiere_engine.connect() as src:
        parent_ids = src.execute(text(
            f"SELECT {fk_col} FROM adempiere.{parent_table} "
            f"WHERE {parent_date_col} >= :d1 AND {parent_date_col} < :d2"
        ), {"d1": target_date, "d2": next_day}).fetchall()

    if not parent_ids:
        return 0

    ids = [r[0] for r in parent_ids]

    # Delete existing child rows for these parents (idempotent)
    with local_engine.begin() as dst:
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            dst.execute(text(
                f"DELETE FROM adempiere.{child_table} WHERE {fk_col} = ANY(:ids)"
            ), {"ids": chunk})

    # Copy child rows
    with idempiere_engine.connect() as src:
        all_rows = []
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            rows = src.execute(text(
                f"SELECT {cols_sql} FROM adempiere.{child_table} WHERE {fk_col} = ANY(:ids)"
            ), {"ids": chunk}).fetchall()
            all_rows.extend(rows)

    if not all_rows:
        return 0

    with local_engine.begin() as dst:
        batch = [{cols[i]: row[i] for i in range(len(cols))} for row in all_rows]
        for j in range(0, len(batch), 5000):
            dst.execute(
                text(f"INSERT INTO adempiere.{child_table} ({cols_sql}) VALUES ({placeholders})"),
                batch[j:j + 5000],
            )

    return len(all_rows)


def sync_snapshot_table(idempiere_engine, local_engine, table: str) -> int:
    """Full refresh of a snapshot table (current state)."""
    return sync_reference_table(idempiere_engine, local_engine, table)


def main():
    parser = argparse.ArgumentParser(description="Sincronización diaria iDempiere → local")
    parser.add_argument(
        "--date",
        default=None,
        help="Fecha a sincronizar (YYYY-MM-DD). Default: ayer.",
    )
    parser.add_argument(
        "--skip-reference",
        action="store_true",
        help="Omitir actualización de tablas de referencia (más rápido).",
    )
    parser.add_argument(
        "--skip-snapshots",
        action="store_true",
        help="Omitir actualización de snapshots (inventario, etc.).",
    )
    args = parser.parse_args()

    target_date = args.date or (date.today() - timedelta(days=1)).isoformat()

    logger.info("=" * 60)
    logger.info("SINCRONIZACION DIARIA iDEMPIERE → LOCAL")
    logger.info("Fecha objetivo: %s", target_date)
    logger.info("=" * 60)

    start = time.time()
    idempiere_engine, local_engine = get_engines()

    # Test connections
    try:
        with idempiere_engine.connect() as c:
            c.execute(text("SELECT 1"))
        logger.info("Conexion iDempiere OK")
    except Exception as e:
        logger.error("Error conectando a iDempiere: %s", e)
        sys.exit(1)

    try:
        with local_engine.connect() as c:
            c.execute(text("SELECT 1"))
        logger.info("Conexion local OK")
    except Exception as e:
        logger.error("Error conectando a DB local: %s", e)
        sys.exit(1)

    total_rows = 0

    # ── 1. Reference tables (new products, clients, etc.) ──
    if not args.skip_reference:
        logger.info("\n-- TABLAS DE REFERENCIA --")
        for table in REFERENCE_TABLES:
            try:
                count = sync_reference_table(idempiere_engine, local_engine, table)
                logger.info("  %s: %s rows", table, f"{count:,}")
                total_rows += count
            except Exception as e:
                logger.error("  %s: ERROR - %s", table, e)

    # ── 2. Transaction tables (only target date) ──
    logger.info("\n-- TRANSACCIONES DEL %s --", target_date)

    # Map parent tables to their date columns for child sync
    parent_date_map = {t: dc for t, dc in TRANSACTION_TABLES}

    for table, date_col in TRANSACTION_TABLES:
        try:
            count = sync_transaction_day(
                idempiere_engine, local_engine, table, date_col, target_date
            )
            logger.info("  %s: %s rows", table, f"{count:,}")
            total_rows += count
        except Exception as e:
            logger.error("  %s: ERROR - %s", table, e)

    # ── 3. Child tables ──
    logger.info("\n-- TABLAS HIJAS --")
    for child_table, fk_col, parent_table in CHILD_TABLES:
        parent_date_col = parent_date_map.get(parent_table)
        if not parent_date_col:
            continue
        try:
            count = sync_child_table(
                idempiere_engine, local_engine, child_table,
                fk_col, parent_table, parent_date_col, target_date
            )
            logger.info("  %s: %s rows", child_table, f"{count:,}")
            total_rows += count
        except Exception as e:
            logger.error("  %s: ERROR - %s", child_table, e)

    # ── 4. Snapshots (current inventory, allocations) ──
    if not args.skip_snapshots:
        logger.info("\n-- SNAPSHOTS --")
        for table in SNAPSHOT_TABLES:
            try:
                count = sync_snapshot_table(idempiere_engine, local_engine, table)
                logger.info("  %s: %s rows", table, f"{count:,}")
                total_rows += count
            except Exception as e:
                logger.error("  %s: ERROR - %s", table, e)

    # ── 5. Metadata ──
    duration = int(time.time() - start)
    try:
        with local_engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO adempiere._extraction_metadata
                (cutoff_date, tables_extracted, total_rows, duration_seconds, notes)
                VALUES (:cutoff, :tables, :rows, :duration, :notes)
            """), {
                "cutoff": target_date,
                "tables": [t for t, _ in TRANSACTION_TABLES] + [t for t, _, _ in CHILD_TABLES],
                "rows": total_rows,
                "duration": duration,
                "notes": f"Daily sync for {target_date} at {datetime.now().isoformat()}",
            })
    except Exception as e:
        logger.warning("No se pudo guardar metadata: %s", e)

    logger.info("\n" + "=" * 60)
    logger.info("SINCRONIZACION COMPLETADA")
    logger.info("  Fecha: %s", target_date)
    logger.info("  Rows totales: %s", f"{total_rows:,}")
    logger.info("  Duracion: %dm %ds", duration // 60, duration % 60)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

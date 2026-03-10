#!/usr/bin/env python3
"""
Extractor de datos históricos de iDempiere a la DB local de SantoniBot.

Copia datos desde iDempiere (192.168.1.73) al schema 'adempiere' en la DB local,
para que las consultas de fechas anteriores al corte no dependan de iDempiere.

Prerequisito: ejecutar la migración 004_historical primero:
  docker compose exec backend alembic upgrade head

Uso:
  docker compose exec backend python scripts/extract_historical_data.py

  # Con fecha de corte personalizada
  docker compose exec backend python scripts/extract_historical_data.py --cutoff 2026-03-01

  # Solo tablas de referencia (sin datos transaccionales)
  docker compose exec backend python scripts/extract_historical_data.py --ref-only

  # Solo una tabla específica
  docker compose exec backend python scripts/extract_historical_data.py --tables c_invoice c_invoiceline
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from urllib.parse import quote_plus

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("ERROR: sqlalchemy no está instalado. Ejecuta: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Table definitions ────────────────────────────────────────────────────────

# Reference tables: copied fully (no date filter)
REFERENCE_TABLES = [
    {
        "name": "ad_org",
        "columns": "ad_org_id, value, name, isactive, issummary",
    },
    {
        "name": "c_currency",
        "columns": "c_currency_id, iso_code, cursymbol, description",
    },
    {
        "name": "c_bpartner",
        "columns": (
            "c_bpartner_id, ad_org_id, value, name, isactive, iscustomer, "
            "isvendor, isemployee, ismayorista, isclap, ispublico, "
            "codigoventas, codigoproductor, codigocompras, c_bp_group_id, salesrep_id"
        ),
    },
    {
        "name": "c_bp_group",
        "columns": "c_bp_group_id, name, isactive",
    },
    {
        "name": "c_salesregion",
        "columns": "c_salesregion_id, name, isactive",
    },
    {
        "name": "c_bpartner_location",
        "columns": "c_bpartner_location_id, c_bpartner_id, c_salesregion_id, c_location_id, isactive",
    },
    {
        "name": "c_location",
        "columns": "c_location_id, c_city_id, c_region_id, address1, city",
    },
    {
        "name": "c_region",
        "columns": "c_region_id, name",
    },
    {
        "name": "c_city",
        "columns": "c_city_id, name, c_region_id",
    },
    {
        "name": "c_doctype",
        "columns": "c_doctype_id, name, docbasetype, isactive, description",
    },
    {
        "name": "m_product",
        "columns": (
            "m_product_id, ad_org_id, value, name, m_product_category_id, "
            "isactive, producttype, issold, ispurchased"
        ),
    },
    {
        "name": "m_product_category",
        "columns": "m_product_category_id, name, value, isactive",
    },
    {
        "name": "m_warehouse",
        "columns": "m_warehouse_id, ad_org_id, name, isactive",
    },
    {
        "name": "m_locator",
        "columns": "m_locator_id, m_warehouse_id, value, isactive",
    },
    {
        "name": "c_paymentterm",
        "columns": "c_paymentterm_id, name, netdays, isactive",
    },
    {
        "name": "c_bank",
        "columns": "c_bank_id, name, isactive",
    },
    {
        "name": "c_bankaccount",
        "columns": (
            "c_bankaccount_id, c_bank_id, ad_org_id, accountno, "
            "c_currency_id, currentbalance, bankaccounttype, isactive"
        ),
    },
    # HR reference
    {
        "name": "hr_department",
        "columns": "hr_department_id, name, isactive",
    },
    {
        "name": "hr_job",
        "columns": "hr_job_id, name, isactive",
    },
    {
        "name": "hr_concept",
        "columns": "hr_concept_id, value, name, type, columntype, isactive",
    },
    {
        "name": "hr_payroll",
        "columns": "hr_payroll_id, name, isactive",
    },
    {
        "name": "hr_employee",
        "columns": (
            "hr_employee_id, c_bpartner_id, ad_org_id, hr_department_id, "
            "hr_job_id, startdate, enddate, isactive"
        ),
    },
    # Accounting reference
    {
        "name": "c_elementvalue",
        "columns": "c_elementvalue_id, value, name, accounttype, issummary, isactive, c_element_id",
    },
    {
        "name": "c_element",
        "columns": "c_element_id, name",
    },
    {
        "name": "c_acctschema",
        "columns": "c_acctschema_id, name",
    },
    {
        "name": "c_period",
        "columns": "c_period_id, name, startdate, enddate, periodno",
    },
]

# Transaction tables: filtered by date < cutoff
TRANSACTION_TABLES = [
    {
        "name": "c_invoice",
        "columns": (
            "c_invoice_id, ad_org_id, c_bpartner_id, c_currency_id, "
            "c_doctypetarget_id, c_paymentterm_id, salesrep_id, documentno, "
            "dateinvoiced, grandtotal, totallines, withholdingamt, issotrx, "
            "ispaid, docstatus, isactive, lve_controlnumber"
        ),
        "date_column": "dateinvoiced",
    },
    {
        "name": "c_invoiceline",
        "columns": "c_invoiceline_id, c_invoice_id, m_product_id, qtyinvoiced, priceactual, linenetamt, line",
        "date_column": None,  # Joined via c_invoice
        "parent_filter": (
            "c_invoice_id IN (SELECT c_invoice_id FROM adempiere.c_invoice "
            "WHERE dateinvoiced < :cutoff)"
        ),
    },
    {
        "name": "c_payment",
        "columns": (
            "c_payment_id, ad_org_id, c_bpartner_id, c_currency_id, "
            "c_bankaccount_id, documentno, datetrx, payamt, isreceipt, "
            "tendertype, docstatus, isactive"
        ),
        "date_column": "datetrx",
    },
    {
        "name": "c_allocationline",
        "columns": (
            "c_allocationline_id, c_allocationhdr_id, c_invoice_id, "
            "c_payment_id, amount, discountamt, writeoffamt"
        ),
        "date_column": None,
        "parent_filter": (
            "c_invoice_id IN (SELECT c_invoice_id FROM adempiere.c_invoice "
            "WHERE dateinvoiced < :cutoff)"
        ),
    },
    {
        "name": "c_order",
        "columns": (
            "c_order_id, ad_org_id, c_bpartner_id, c_currency_id, c_doctype_id, "
            "c_paymentterm_id, documentno, dateordered, grandtotal, issotrx, "
            "isdelivered, docstatus, isactive, driver, plateno, grossweight, "
            "tareweight, netweight, classification, tipofrijol, guidemac, "
            "guideproducer, guidesada"
        ),
        "date_column": "dateordered",
    },
    {
        "name": "c_orderline",
        "columns": "c_orderline_id, c_order_id, m_product_id, qtyordered, priceactual, linenetamt, line",
        "date_column": None,
        "parent_filter": (
            "c_order_id IN (SELECT c_order_id FROM adempiere.c_order "
            "WHERE dateordered < :cutoff)"
        ),
    },
    {
        "name": "m_inout",
        "columns": (
            "m_inout_id, ad_org_id, c_bpartner_id, c_doctype_id, documentno, "
            "movementdate, movementtype, docstatus, isactive"
        ),
        "date_column": "movementdate",
    },
    {
        "name": "m_inoutline",
        "columns": "m_inoutline_id, m_inout_id, m_product_id, m_locator_id, movementqty, line",
        "date_column": None,
        "parent_filter": (
            "m_inout_id IN (SELECT m_inout_id FROM adempiere.m_inout "
            "WHERE movementdate < :cutoff)"
        ),
    },
    {
        "name": "fact_acct",
        "columns": (
            "fact_acct_id, ad_org_id, account_id, c_acctschema_id, c_currency_id, "
            "c_period_id, dateacct, amtsourcedr, amtsourcecr, amtacctdr, amtacctcr, "
            "postingtype, description"
        ),
        "date_column": "dateacct",
    },
    {
        "name": "hr_process",
        "columns": (
            "hr_process_id, ad_org_id, hr_payroll_id, c_period_id, "
            "dateacct, documentno, docstatus, isactive"
        ),
        "date_column": "dateacct",
    },
    {
        "name": "hr_movement",
        "columns": "hr_movement_id, hr_process_id, c_bpartner_id, hr_concept_id, amount, qty",
        "date_column": None,
        "parent_filter": (
            "hr_process_id IN (SELECT hr_process_id FROM adempiere.hr_process "
            "WHERE dateacct < :cutoff)"
        ),
    },
]

# Snapshot tables: current state (always full copy)
SNAPSHOT_TABLES = [
    {
        "name": "m_storageonhand",
        "columns": "m_product_id, m_locator_id, m_attributesetinstance_id, qtyonhand, datelastinventory",
    },
]

BATCH_SIZE = 5000


def get_engines(args):
    """Create SQLAlchemy engines for iDempiere and local DB."""
    # iDempiere connection
    ide_host = os.environ.get("IDEMPIERE_DB_HOST", "192.168.1.73")
    ide_port = os.environ.get("IDEMPIERE_DB_PORT", "5432")
    ide_db = os.environ.get("IDEMPIERE_DB_NAME", "idempiere_produccion")
    ide_user = os.environ.get("IDEMPIERE_DB_USER", "ova")
    ide_pass = os.environ.get("IDEMPIERE_DB_PASSWORD", "")

    # Try loading from .env if password is empty
    if not ide_pass:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("IDEMPIERE_DB_PASSWORD="):
                        ide_pass = line.split("=", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("POSTGRES_HOST="):
                        os.environ.setdefault("POSTGRES_HOST", line.split("=", 1)[1].strip())
                    elif line.startswith("POSTGRES_PORT="):
                        os.environ.setdefault("POSTGRES_PORT", line.split("=", 1)[1].strip())
                    elif line.startswith("POSTGRES_DB="):
                        os.environ.setdefault("POSTGRES_DB", line.split("=", 1)[1].strip())
                    elif line.startswith("POSTGRES_USER="):
                        os.environ.setdefault("POSTGRES_USER", line.split("=", 1)[1].strip())
                    elif line.startswith("POSTGRES_PASSWORD="):
                        os.environ.setdefault("POSTGRES_PASSWORD", line.split("=", 1)[1].strip())

    ide_url = f"postgresql://{ide_user}:{quote_plus(ide_pass)}@{ide_host}:{ide_port}/{ide_db}"
    logger.info("iDempiere: %s:%s/%s (user: %s)", ide_host, ide_port, ide_db, ide_user)

    # Local DB connection
    loc_host = os.environ.get("POSTGRES_HOST", "db")
    loc_port = os.environ.get("POSTGRES_PORT", "5432")
    loc_db = os.environ.get("POSTGRES_DB", "santonibot")
    loc_user = os.environ.get("POSTGRES_USER", "santonibot")
    loc_pass = os.environ.get("POSTGRES_PASSWORD", "changeme")

    loc_url = f"postgresql://{loc_user}:{quote_plus(loc_pass)}@{loc_host}:{loc_port}/{loc_db}"
    logger.info("Local DB: %s:%s/%s (user: %s)", loc_host, loc_port, loc_db, loc_user)

    ide_engine = create_engine(ide_url, pool_pre_ping=True)
    loc_engine = create_engine(loc_url, pool_pre_ping=True)

    return ide_engine, loc_engine


def test_connections(ide_engine, loc_engine):
    """Test both database connections."""
    try:
        with ide_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexion a iDempiere OK")
    except Exception as e:
        logger.error("Error conectando a iDempiere: %s", e)
        return False

    try:
        with loc_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexion a DB local OK")
    except Exception as e:
        logger.error("Error conectando a DB local: %s", e)
        return False

    # Verify adempiere schema exists in local DB
    try:
        with loc_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'adempiere'"
            ))
            if not result.fetchone():
                logger.error(
                    "Schema 'adempiere' no existe en la DB local. "
                    "Ejecuta primero: alembic upgrade head"
                )
                return False
    except Exception as e:
        logger.error("Error verificando schema adempiere: %s", e)
        return False

    return True


def check_source_column_exists(ide_engine, table_name, column_name):
    """Check if a column exists in the source iDempiere table."""
    with ide_engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'adempiere'
              AND table_name = :table
              AND column_name = :col
        """), {"table": table_name, "col": column_name})
        return result.fetchone() is not None


def filter_columns(ide_engine, table_name, columns_str):
    """Filter column list to only include columns that exist in the source table."""
    columns = [c.strip() for c in columns_str.split(",")]
    existing = []
    missing = []
    for col in columns:
        if check_source_column_exists(ide_engine, table_name, col):
            existing.append(col)
        else:
            missing.append(col)
    if missing:
        logger.warning(
            "Tabla %s: columnas no encontradas en iDempiere (omitidas): %s",
            table_name, ", ".join(missing)
        )
    return ", ".join(existing), existing


def extract_table(ide_engine, loc_engine, table_def, cutoff, is_transaction=False):
    """Extract a single table from iDempiere to local DB."""
    table_name = table_def["name"]
    columns_str = table_def["columns"]

    # Filter columns to only those that exist in source
    columns_str, columns_list = filter_columns(ide_engine, table_name, columns_str)
    if not columns_list:
        logger.warning("Tabla %s: ninguna columna encontrada en iDempiere, saltando", table_name)
        return 0

    # Build SELECT query
    if is_transaction:
        date_col = table_def.get("date_column")
        parent_filter = table_def.get("parent_filter")
        if date_col:
            select_sql = (
                f"SELECT {columns_str} FROM adempiere.{table_name} "
                f"WHERE {date_col} < :cutoff"
            )
        elif parent_filter:
            select_sql = (
                f"SELECT {columns_str} FROM adempiere.{table_name} "
                f"WHERE {parent_filter}"
            )
        else:
            select_sql = f"SELECT {columns_str} FROM adempiere.{table_name}"
    else:
        select_sql = f"SELECT {columns_str} FROM adempiere.{table_name}"

    # Count rows to extract
    count_sql = select_sql.replace(f"SELECT {columns_str}", "SELECT COUNT(*)", 1)
    try:
        with ide_engine.connect() as conn:
            result = conn.execute(text(count_sql), {"cutoff": cutoff})
            total_rows = result.scalar()
    except Exception as e:
        logger.error("  Error contando filas de %s: %s", table_name, e)
        return 0

    if total_rows == 0:
        logger.info("  %s: 0 filas (nada que copiar)", table_name)
        return 0

    logger.info("  %s: %s filas a extraer...", table_name, f"{total_rows:,}")

    # Clear existing data in local table
    try:
        with loc_engine.begin() as conn:
            conn.execute(text(f"DELETE FROM adempiere.{table_name}"))
    except Exception as e:
        logger.error("  Error limpiando tabla local %s: %s", table_name, e)
        return 0

    # Extract in batches using OFFSET/LIMIT
    placeholders = ", ".join([f":{c}" for c in columns_list])
    insert_sql = (
        f"INSERT INTO adempiere.{table_name} ({columns_str}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT DO NOTHING"
    )

    rows_inserted = 0
    offset = 0
    batch_select = select_sql + f" ORDER BY {columns_list[0]} LIMIT :batch_size OFFSET :offset"

    while offset < total_rows:
        try:
            with ide_engine.connect() as conn:
                result = conn.execute(
                    text(batch_select),
                    {"cutoff": cutoff, "batch_size": BATCH_SIZE, "offset": offset},
                )
                rows = result.fetchall()

            if not rows:
                break

            # Insert batch into local DB
            batch_data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns_list):
                    row_dict[col] = row[i]
                batch_data.append(row_dict)

            with loc_engine.begin() as conn:
                conn.execute(text(insert_sql), batch_data)

            rows_inserted += len(rows)
            offset += BATCH_SIZE

            if offset % (BATCH_SIZE * 5) == 0 and offset < total_rows:
                logger.info("    ... %s/%s filas", f"{rows_inserted:,}", f"{total_rows:,}")

        except Exception as e:
            logger.error("  Error en batch offset=%d de %s: %s", offset, table_name, e)
            break

    logger.info("  %s: %s filas insertadas", table_name, f"{rows_inserted:,}")
    return rows_inserted


def main():
    parser = argparse.ArgumentParser(
        description="Extractor de datos historicos de iDempiere"
    )
    parser.add_argument(
        "--cutoff",
        default=os.environ.get("HISTORICAL_DATA_CUTOFF", "2026-03-01"),
        help="Fecha de corte YYYY-MM-DD (default: 2026-03-01)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Tamaño del batch (default: 5000)",
    )
    parser.add_argument(
        "--ref-only",
        action="store_true",
        help="Solo copiar tablas de referencia (sin transacciones)",
    )
    parser.add_argument(
        "--tables",
        nargs="*",
        default=None,
        help="Tablas específicas a extraer (default: todas)",
    )
    args = parser.parse_args()

    global BATCH_SIZE
    BATCH_SIZE = args.batch_size

    cutoff = args.cutoff

    logger.info("=" * 60)
    logger.info("EXTRACCION DE DATOS HISTORICOS DE iDEMPIERE")
    logger.info("Fecha de corte: %s (datos ANTES de esta fecha)", cutoff)
    logger.info("Batch size: %d", BATCH_SIZE)
    logger.info("=" * 60)

    ide_engine, loc_engine = get_engines(args)

    if not test_connections(ide_engine, loc_engine):
        sys.exit(1)

    start_time = time.time()
    total_rows = 0
    tables_extracted = []
    filter_tables = set(args.tables) if args.tables else None

    # ── Reference tables ─────────────────────────────────────────────────
    logger.info("")
    logger.info("=== TABLAS DE REFERENCIA (copia completa) ===")
    for table_def in REFERENCE_TABLES:
        if filter_tables and table_def["name"] not in filter_tables:
            continue
        rows = extract_table(ide_engine, loc_engine, table_def, cutoff, is_transaction=False)
        total_rows += rows
        if rows > 0:
            tables_extracted.append(table_def["name"])

    # ── Transaction tables ───────────────────────────────────────────────
    if not args.ref_only:
        logger.info("")
        logger.info("=== TABLAS TRANSACCIONALES (datos < %s) ===", cutoff)
        for table_def in TRANSACTION_TABLES:
            if filter_tables and table_def["name"] not in filter_tables:
                continue
            rows = extract_table(ide_engine, loc_engine, table_def, cutoff, is_transaction=True)
            total_rows += rows
            if rows > 0:
                tables_extracted.append(table_def["name"])

        # ── Snapshot tables ──────────────────────────────────────────────
        logger.info("")
        logger.info("=== TABLAS SNAPSHOT (estado actual) ===")
        for table_def in SNAPSHOT_TABLES:
            if filter_tables and table_def["name"] not in filter_tables:
                continue
            rows = extract_table(ide_engine, loc_engine, table_def, cutoff, is_transaction=False)
            total_rows += rows
            if rows > 0:
                tables_extracted.append(table_def["name"])

    duration = int(time.time() - start_time)

    # ── Record extraction metadata ───────────────────────────────────────
    try:
        with loc_engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO adempiere._extraction_metadata
                    (cutoff_date, tables_extracted, total_rows, duration_seconds, notes)
                VALUES
                    (:cutoff, :tables, :rows, :duration, :notes)
            """), {
                "cutoff": cutoff,
                "tables": tables_extracted,
                "rows": total_rows,
                "duration": duration,
                "notes": f"Extracted by extract_historical_data.py at {datetime.now().isoformat()}",
            })
    except Exception as e:
        logger.warning("No se pudo guardar metadatos de extraccion: %s", e)

    # ── Summary ──────────────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("EXTRACCION COMPLETADA")
    logger.info("Tablas: %d", len(tables_extracted))
    logger.info("Filas totales: %s", f"{total_rows:,}")
    logger.info("Duracion: %d segundos", duration)
    logger.info("=" * 60)
    logger.info("")
    logger.info("Proximo paso: activar en .env:")
    logger.info("  HISTORICAL_DATA_ENABLED=true")
    logger.info("  HISTORICAL_DATA_CUTOFF=%s", cutoff)
    logger.info("")
    logger.info("Luego reiniciar: docker compose restart backend")


if __name__ == "__main__":
    main()

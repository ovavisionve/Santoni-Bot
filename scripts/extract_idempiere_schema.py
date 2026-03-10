#!/usr/bin/env python3
"""
Extractor de esquema iDempiere para cargar al LLM.

Conecta a iDempiere (192.168.1.73:5432) y extrae:
1. Todas las tablas del schema 'adempiere' usadas por los agentes
2. Columnas con tipos de datos, nullable, defaults
3. Foreign keys y relaciones
4. Row counts
5. Datos de ejemplo (primeros 5 rows de cada tabla)
6. Valores únicos de columnas clave (docstatus, issotrx, etc.)
7. Estadísticas de columnas numéricas

Uso:
  # Desde el servidor (192.168.1.26)
  cd /opt/santonibot/backend
  python3 ../scripts/extract_idempiere_schema.py

  # O con Docker
  docker compose exec backend python3 ../scripts/extract_idempiere_schema.py

  # Guardar a archivo específico
  python3 ../scripts/extract_idempiere_schema.py --output /tmp/schema.md

Output: Archivo markdown con todo el esquema listo para copiar al LLM.
"""

import argparse
import os
import sys
from datetime import datetime

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("ERROR: sqlalchemy no está instalado. Ejecuta: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)


# ── Tables used by each agent ──────────────────────────────────────────────
AGENT_TABLES = {
    "Ventas": [
        "c_invoice", "c_invoiceline", "c_payment", "c_bpartner",
        "c_bpartner_location", "c_location", "c_region",
        "c_currency", "ad_org", "c_doctype",
    ],
    "Finanzas": [
        "c_bankaccount", "c_bank", "c_payment", "c_invoice",
        "c_bpartner", "c_currency", "ad_org",
    ],
    "Contabilidad": [
        "fact_acct", "c_elementvalue", "c_element",
        "c_acctschema", "c_period", "ad_org",
    ],
    "RRHH": [
        "hr_employee", "hr_process", "hr_movement", "hr_concept",
        "hr_department", "hr_job", "c_bpartner", "ad_org",
    ],
    "Produccion": [
        "m_inout", "m_inoutline", "m_product", "m_product_category",
        "m_storageonhand", "m_locator", "m_warehouse",
        "c_doctype", "ad_org",
    ],
    "Compras_Insumos": [
        "c_invoice", "c_invoiceline", "c_order", "c_orderline",
        "c_bpartner", "m_product", "m_product_category",
        "m_storageonhand", "m_locator", "m_warehouse",
        "c_currency", "ad_org",
    ],
    "Compras_Productores": [
        "c_order", "c_orderline", "c_bpartner",
        "m_product", "c_currency", "ad_org",
    ],
}

# All unique tables
ALL_TABLES = sorted(set(t for tables in AGENT_TABLES.values() for t in tables))

# Columns to show distinct values for (useful for understanding data)
DISTINCT_VALUE_COLUMNS = {
    "c_invoice": ["docstatus", "issotrx", "isactive", "ispaid"],
    "c_order": ["docstatus", "issotrx", "isactive", "isdelivered"],
    "c_payment": ["docstatus", "isactive"],
    "c_bpartner": ["isvendor", "iscustomer", "isactive", "isemployee"],
    "m_inout": ["movementtype", "docstatus", "isactive"],
    "m_product": ["isactive", "producttype", "issold", "ispurchased"],
    "hr_employee": ["isactive"],
    "fact_acct": ["postingtype"],
    "c_elementvalue": ["accounttype", "isactive", "issummary"],
    "c_doctype": ["docbasetype", "isactive"],
    "ad_org": ["isactive", "issummary"],
}

# Columns to show sample values for (text columns that help understand data)
SAMPLE_TEXT_COLUMNS = {
    "c_bpartner": ["name"],
    "m_product": ["name", "value"],
    "m_product_category": ["name"],
    "m_warehouse": ["name"],
    "hr_concept": ["name", "value"],
    "hr_department": ["name"],
    "hr_job": ["name"],
    "c_elementvalue": ["value", "name", "accounttype"],
    "c_currency": ["iso_code", "cursymbol", "description"],
    "ad_org": ["name", "value"],
    "c_doctype": ["name", "docbasetype"],
    "c_bank": ["name"],
    "c_region": ["name"],
}


def get_engine():
    """Create engine from env vars or defaults."""
    host = os.environ.get("IDEMPIERE_DB_HOST", "192.168.1.73")
    port = os.environ.get("IDEMPIERE_DB_PORT", "5432")
    dbname = os.environ.get("IDEMPIERE_DB_NAME", "idempiere_produccion")
    user = os.environ.get("IDEMPIERE_DB_USER", "ova")
    password = os.environ.get("IDEMPIERE_DB_PASSWORD", "")

    # Try loading from .env if password is empty
    if not password:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("IDEMPIERE_DB_PASSWORD="):
                        password = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    from urllib.parse import quote_plus
    url = f"postgresql://{user}:{quote_plus(password)}@{host}:{port}/{dbname}"
    print(f"Conectando a: {host}:{port}/{dbname} como {user}...")
    return create_engine(url, pool_pre_ping=True)


def extract_table_info(engine, table_name: str) -> dict:
    """Extract complete info for one table."""
    schema = "adempiere"
    info = {"name": table_name, "exists": False}

    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = :schema AND table_name = :table
        """), {"schema": schema, "table": table_name})
        if not result.fetchone():
            return info
        info["exists"] = True

        # Row count
        try:
            row = conn.execute(text(
                f"SELECT COUNT(*) FROM adempiere.{table_name}"
            )).fetchone()
            info["row_count"] = row[0]
        except Exception as e:
            info["row_count"] = f"ERROR: {e}"

        # Columns
        cols_result = conn.execute(text("""
            SELECT column_name, data_type, character_maximum_length,
                   is_nullable, column_default, udt_name
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            ORDER BY ordinal_position
        """), {"schema": schema, "table": table_name})
        info["columns"] = []
        for r in cols_result:
            col = {
                "name": r[0],
                "type": r[1],
                "max_length": r[2],
                "nullable": r[3],
                "default": str(r[4])[:60] if r[4] else None,
                "udt": r[5],
            }
            info["columns"].append(col)

        # Foreign keys
        fk_result = conn.execute(text("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = :schema
              AND tc.table_name = :table
            ORDER BY kcu.column_name
        """), {"schema": schema, "table": table_name})
        info["foreign_keys"] = [
            {"column": r[0], "references": f"{r[1]}.{r[2]}"}
            for r in fk_result
        ]

        # Primary key
        pk_result = conn.execute(text("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = :schema
              AND tc.table_name = :table
            ORDER BY kcu.ordinal_position
        """), {"schema": schema, "table": table_name})
        info["primary_key"] = [r[0] for r in pk_result]

        # Distinct values for key columns
        if table_name in DISTINCT_VALUE_COLUMNS:
            info["distinct_values"] = {}
            for col in DISTINCT_VALUE_COLUMNS[table_name]:
                try:
                    dv_result = conn.execute(text(
                        f"SELECT DISTINCT {col}, COUNT(*) "
                        f"FROM adempiere.{table_name} "
                        f"GROUP BY {col} ORDER BY COUNT(*) DESC LIMIT 20"
                    ))
                    info["distinct_values"][col] = [
                        {"value": str(r[0]), "count": r[1]} for r in dv_result
                    ]
                except Exception:
                    pass

        # Sample text values (top 15)
        if table_name in SAMPLE_TEXT_COLUMNS:
            info["sample_values"] = {}
            for col in SAMPLE_TEXT_COLUMNS[table_name]:
                try:
                    sv_result = conn.execute(text(
                        f"SELECT DISTINCT {col} FROM adempiere.{table_name} "
                        f"WHERE {col} IS NOT NULL AND {col} != '' "
                        f"ORDER BY {col} LIMIT 15"
                    ))
                    info["sample_values"][col] = [str(r[0]) for r in sv_result]
                except Exception:
                    pass

        # Sample rows (5)
        try:
            col_names = [c["name"] for c in info["columns"][:20]]  # limit columns
            cols_sql = ", ".join(col_names)
            sample_result = conn.execute(text(
                f"SELECT {cols_sql} FROM adempiere.{table_name} LIMIT 5"
            ))
            info["sample_rows"] = {
                "columns": col_names,
                "rows": [
                    [str(v)[:80] if v is not None else "NULL" for v in row]
                    for row in sample_result
                ],
            }
        except Exception as e:
            info["sample_rows"] = {"error": str(e)}

        # Indexes
        try:
            idx_result = conn.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = :schema AND tablename = :table
                ORDER BY indexname
            """), {"schema": schema, "table": table_name})
            info["indexes"] = [
                {"name": r[0], "definition": r[1][:120]}
                for r in idx_result
            ]
        except Exception:
            info["indexes"] = []

    return info


def extract_currency_info(engine) -> str:
    """Extract all currency IDs and their codes - critical for multi-currency."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT c.c_currency_id, c.iso_code, c.cursymbol, c.description,
                   COUNT(DISTINCT i.c_invoice_id) AS invoices_count
            FROM adempiere.c_currency c
            LEFT JOIN adempiere.c_invoice i ON c.c_currency_id = i.c_currency_id
            GROUP BY c.c_currency_id, c.iso_code, c.cursymbol, c.description
            ORDER BY invoices_count DESC NULLS LAST
            LIMIT 20
        """))
        lines = ["## Monedas (c_currency) con facturas asociadas\n"]
        lines.append("| ID | ISO | Símbolo | Descripción | # Facturas |")
        lines.append("|-----|-----|---------|-------------|------------|")
        for r in result:
            lines.append(f"| {r[0]} | {r[1]} | {r[2] or ''} | {r[3] or ''} | {r[4]} |")
        return "\n".join(lines)


def extract_org_info(engine) -> str:
    """Extract organizations and their IDs."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT o.ad_org_id, o.value, o.name, o.isactive,
                   COUNT(DISTINCT i.c_invoice_id) AS invoices
            FROM adempiere.ad_org o
            LEFT JOIN adempiere.c_invoice i ON o.ad_org_id = i.ad_org_id
            GROUP BY o.ad_org_id, o.value, o.name, o.isactive
            ORDER BY invoices DESC NULLS LAST
        """))
        lines = ["## Organizaciones (ad_org)\n"]
        lines.append("| ID | Value | Nombre | Activo | # Facturas |")
        lines.append("|-----|-------|--------|--------|------------|")
        for r in result:
            lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")
        return "\n".join(lines)


def extract_doctype_info(engine) -> str:
    """Extract document types."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT c_doctype_id, name, docbasetype, isactive,
                   description
            FROM adempiere.c_doctype
            WHERE isactive = 'Y'
            ORDER BY docbasetype, name
        """))
        lines = ["## Tipos de Documento (c_doctype) activos\n"]
        lines.append("| ID | Nombre | DocBaseType | Descripción |")
        lines.append("|-----|--------|-------------|-------------|")
        for r in result:
            desc = (r[4] or "")[:60]
            lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {desc} |")
        return "\n".join(lines)


def extract_product_categories(engine) -> str:
    """Extract product categories with counts."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT pc.m_product_category_id, pc.name, pc.value,
                   COUNT(p.m_product_id) AS products
            FROM adempiere.m_product_category pc
            LEFT JOIN adempiere.m_product p ON pc.m_product_category_id = p.m_product_category_id
            GROUP BY pc.m_product_category_id, pc.name, pc.value
            ORDER BY products DESC
            LIMIT 30
        """))
        lines = ["## Categorías de Productos (m_product_category)\n"]
        lines.append("| ID | Value | Nombre | # Productos |")
        lines.append("|-----|-------|--------|-------------|")
        for r in result:
            lines.append(f"| {r[0]} | {r[1] or ''} | {r[2] or ''} | {r[3]} |")
        return "\n".join(lines)


def extract_hr_concepts(engine) -> str:
    """Extract HR concepts (payroll types)."""
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                SELECT hc.hr_concept_id, hc.value, hc.name, hc.isactive,
                       COUNT(hm.hr_movement_id) AS movements
                FROM adempiere.hr_concept hc
                LEFT JOIN adempiere.hr_movement hm ON hc.hr_concept_id = hm.hr_concept_id
                GROUP BY hc.hr_concept_id, hc.value, hc.name, hc.isactive
                ORDER BY movements DESC
                LIMIT 40
            """))
            lines = ["## Conceptos de Nómina (hr_concept) - Top 40\n"]
            lines.append("| ID | Value | Nombre | Activo | # Movimientos |")
            lines.append("|-----|-------|--------|--------|---------------|")
            for r in result:
                lines.append(f"| {r[0]} | {r[1] or ''} | {r[2] or ''} | {r[3]} | {r[4]} |")
            return "\n".join(lines)
        except Exception as e:
            return f"## Conceptos de Nómina\nError: {e}"


def extract_account_types(engine) -> str:
    """Extract chart of accounts structure."""
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                SELECT ev.value, ev.name, ev.accounttype, ev.issummary,
                       ev.isactive
                FROM adempiere.c_elementvalue ev
                WHERE ev.issummary = 'Y' AND ev.isactive = 'Y'
                ORDER BY ev.value
                LIMIT 50
            """))
            lines = ["## Plan de Cuentas - Cuentas Padre (c_elementvalue, issummary='Y')\n"]
            lines.append("| Código | Nombre | Tipo | Activo |")
            lines.append("|--------|--------|------|--------|")
            for r in result:
                tipo_map = {"A": "Activo", "L": "Pasivo", "O": "Patrimonio",
                           "R": "Ingreso", "E": "Gasto"}
                tipo = tipo_map.get(r[2], r[2])
                lines.append(f"| {r[0]} | {r[1]} | {tipo} | {r[4]} |")
            return "\n".join(lines)
        except Exception as e:
            return f"## Plan de Cuentas\nError: {e}"


def extract_warehouses(engine) -> str:
    """Extract warehouses and stock summary."""
    with engine.connect() as conn:
        try:
            result = conn.execute(text("""
                SELECT w.m_warehouse_id, w.name, w.isactive,
                       o.name AS org_name,
                       COUNT(DISTINCT s.m_product_id) AS products_in_stock,
                       COALESCE(SUM(s.qtyonhand), 0) AS total_qty
                FROM adempiere.m_warehouse w
                JOIN adempiere.ad_org o ON w.ad_org_id = o.ad_org_id
                LEFT JOIN adempiere.m_locator l ON w.m_warehouse_id = l.m_warehouse_id
                LEFT JOIN adempiere.m_storageonhand s ON l.m_locator_id = s.m_locator_id
                GROUP BY w.m_warehouse_id, w.name, w.isactive, o.name
                ORDER BY total_qty DESC
            """))
            lines = ["## Almacenes (m_warehouse) con stock\n"]
            lines.append("| ID | Nombre | Org | Activo | Productos | Qty Total |")
            lines.append("|-----|--------|-----|--------|-----------|-----------|")
            for r in result:
                lines.append(
                    f"| {r[0]} | {r[1]} | {r[3]} | {r[2]} | {r[4]} | {r[5]:,.0f} |"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"## Almacenes\nError: {e}"


def format_table_md(info: dict) -> str:
    """Format table info as markdown."""
    if not info["exists"]:
        return f"### {info['name']}\n**NO EXISTE** en el schema adempiere\n"

    lines = [f"### {info['name']}"]
    lines.append(f"**Rows:** {info['row_count']:,}" if isinstance(info['row_count'], int) else f"**Rows:** {info['row_count']}")

    # Primary key
    if info.get("primary_key"):
        lines.append(f"**PK:** {', '.join(info['primary_key'])}")

    # Columns table
    lines.append("\n| Columna | Tipo | Nullable | Default |")
    lines.append("|---------|------|----------|---------|")
    for col in info["columns"]:
        tipo = col["udt"]
        if col["max_length"]:
            tipo += f"({col['max_length']})"
        default = col["default"] or ""
        lines.append(f"| {col['name']} | {tipo} | {col['nullable']} | {default} |")

    # Foreign keys
    if info.get("foreign_keys"):
        lines.append("\n**Foreign Keys:**")
        for fk in info["foreign_keys"]:
            lines.append(f"- `{fk['column']}` → `{fk['references']}`")

    # Distinct values
    if info.get("distinct_values"):
        lines.append("\n**Valores distintos de columnas clave:**")
        for col, values in info["distinct_values"].items():
            vals_str = ", ".join(f"`{v['value']}`({v['count']:,})" for v in values)
            lines.append(f"- **{col}**: {vals_str}")

    # Sample text values
    if info.get("sample_values"):
        lines.append("\n**Valores de ejemplo:**")
        for col, values in info["sample_values"].items():
            vals = ", ".join(f'"{v}"' for v in values[:10])
            lines.append(f"- **{col}**: {vals}")

    # Sample rows
    if info.get("sample_rows") and "columns" in info["sample_rows"]:
        sr = info["sample_rows"]
        if sr["rows"]:
            lines.append("\n**Muestra (5 rows):**")
            lines.append("| " + " | ".join(sr["columns"]) + " |")
            lines.append("|" + "|".join(["---"] * len(sr["columns"])) + "|")
            for row in sr["rows"]:
                lines.append("| " + " | ".join(str(v)[:30] for v in row) + " |")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Extractor de esquema iDempiere")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Archivo de salida (default: docs/idempiere_schema.md)",
    )
    parser.add_argument(
        "--tables",
        nargs="*",
        default=None,
        help="Tablas específicas a extraer (default: todas las de los agentes)",
    )
    args = parser.parse_args()

    output_path = args.output or os.path.join(
        os.path.dirname(__file__), "..", "docs", "idempiere_schema.md"
    )

    tables = args.tables or ALL_TABLES

    engine = get_engine()

    # Test connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Conexión exitosa a iDempiere!\n")
    except Exception as e:
        print(f"ERROR conectando a iDempiere: {e}")
        sys.exit(1)

    sections = []
    sections.append(f"# Esquema iDempiere - Alimentos Santoni C.A.")
    sections.append(f"**Extraído:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sections.append(f"**Base de datos:** idempiere_produccion @ 192.168.1.73")
    sections.append(f"**Schema:** adempiere")
    sections.append(f"**Tablas extraídas:** {len(tables)}")
    sections.append("")

    # ── Global context ──
    print("Extrayendo contexto global...")
    sections.append("---\n# CONTEXTO GLOBAL\n")

    print("  → Organizaciones...")
    sections.append(extract_org_info(engine))
    sections.append("")

    print("  → Monedas...")
    sections.append(extract_currency_info(engine))
    sections.append("")

    print("  → Tipos de documento...")
    sections.append(extract_doctype_info(engine))
    sections.append("")

    print("  → Categorías de productos...")
    sections.append(extract_product_categories(engine))
    sections.append("")

    print("  → Almacenes...")
    sections.append(extract_warehouses(engine))
    sections.append("")

    print("  → Plan de cuentas...")
    sections.append(extract_account_types(engine))
    sections.append("")

    print("  → Conceptos de nómina...")
    sections.append(extract_hr_concepts(engine))
    sections.append("")

    # ── Table details ──
    sections.append("---\n# DETALLE DE TABLAS\n")

    for i, table in enumerate(tables, 1):
        print(f"  [{i}/{len(tables)}] {table}...")
        info = extract_table_info(engine, table)
        sections.append(format_table_md(info))

    # ── Agent-table mapping ──
    sections.append("---\n# MAPEO AGENTE → TABLAS\n")
    for agent, agent_tables in AGENT_TABLES.items():
        sections.append(f"### {agent}")
        sections.append(", ".join(f"`{t}`" for t in agent_tables))
        sections.append("")

    # ── Useful JOINs ──
    sections.append("---\n# JOINS COMUNES\n")
    sections.append("```sql")
    sections.append("-- Facturas con proveedor/cliente")
    sections.append("SELECT i.*, bp.name AS partner_name")
    sections.append("FROM adempiere.c_invoice i")
    sections.append("JOIN adempiere.c_bpartner bp ON i.c_bpartner_id = bp.c_bpartner_id;")
    sections.append("")
    sections.append("-- Líneas de factura con producto")
    sections.append("SELECT il.*, p.name AS product_name, p.value AS product_code")
    sections.append("FROM adempiere.c_invoiceline il")
    sections.append("JOIN adempiere.m_product p ON il.m_product_id = p.m_product_id;")
    sections.append("")
    sections.append("-- Stock actual por producto y almacén")
    sections.append("SELECT p.value, p.name, w.name AS warehouse, SUM(s.qtyonhand) AS qty")
    sections.append("FROM adempiere.m_storageonhand s")
    sections.append("JOIN adempiere.m_locator l ON s.m_locator_id = l.m_locator_id")
    sections.append("JOIN adempiere.m_warehouse w ON l.m_warehouse_id = w.m_warehouse_id")
    sections.append("JOIN adempiere.m_product p ON s.m_product_id = p.m_product_id")
    sections.append("GROUP BY p.value, p.name, w.name;")
    sections.append("")
    sections.append("-- Empleados con cargo y departamento")
    sections.append("SELECT bp.name, j.name AS cargo, d.name AS departamento, e.isactive")
    sections.append("FROM adempiere.hr_employee e")
    sections.append("JOIN adempiere.c_bpartner bp ON e.c_bpartner_id = bp.c_bpartner_id")
    sections.append("LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id")
    sections.append("LEFT JOIN adempiere.hr_department d ON e.hr_department_id = d.hr_department_id;")
    sections.append("")
    sections.append("-- Movimientos de inventario (producción)")
    sections.append("SELECT io.documentno, io.movementdate, io.movementtype,")
    sections.append("       iol.m_product_id, p.name, iol.movementqty")
    sections.append("FROM adempiere.m_inout io")
    sections.append("JOIN adempiere.m_inoutline iol ON io.m_inout_id = iol.m_inout_id")
    sections.append("JOIN adempiere.m_product p ON iol.m_product_id = p.m_product_id;")
    sections.append("")
    sections.append("-- Asientos contables")
    sections.append("SELECT fa.dateacct, ev.value AS cuenta, ev.name,")
    sections.append("       fa.amtsourcedr, fa.amtsourcecr, fa.description")
    sections.append("FROM adempiere.fact_acct fa")
    sections.append("JOIN adempiere.c_elementvalue ev ON fa.account_id = ev.c_elementvalue_id;")
    sections.append("```\n")

    # Write output
    full_text = "\n".join(sections)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    print(f"\n{'='*60}")
    print(f"ESQUEMA EXTRAÍDO EXITOSAMENTE")
    print(f"Archivo: {os.path.abspath(output_path)}")
    print(f"Tamaño: {len(full_text):,} caracteres")
    print(f"Tablas: {len(tables)}")
    print(f"{'='*60}")
    print(f"\nPróximo paso: Copia el contenido de {output_path}")
    print(f"y pégalo en el system prompt del LLM o en CLAUDE.md")


if __name__ == "__main__":
    main()

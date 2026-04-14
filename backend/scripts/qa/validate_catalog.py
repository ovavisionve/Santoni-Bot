#!/usr/bin/env python3
"""
Validador del catálogo VIEWS_CATALOG contra el schema real de iDempiere.

Toma el texto del catálogo en sql_direct.py y:
  1. Extrae todas las tablas mencionadas con prefijo `adempiere.`
  2. Extrae todas las columnas mencionadas tipo `table.column`
  3. Extrae todas las columnas sueltas de los ejemplos SQL
  4. Verifica contra information_schema de iDempiere que existan

Reporta:
  - Tablas del catálogo que NO existen en iDempiere
  - Columnas del catálogo que NO existen en sus tablas
  - Tablas del _ALLOWED_TABLES que no están en iDempiere

Esto es el tipo de bug que nos pasó con `hr_process.hrdate` (inexistente).
Corriendo este script antes de deploy se detectan ese tipo de bugs sin
tener que esperar a que un usuario los encuentre.

Uso:
    docker compose exec backend python scripts/qa/validate_catalog.py

    # Salida JSON
    docker compose exec backend python scripts/qa/validate_catalog.py --json
"""
import argparse
import re
import sys
from pathlib import Path

# Permite correr desde cualquier directorio.
# Script vive en backend/scripts/qa/ → parent.parent.parent = backend root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text  # noqa: E402
from app.database import IdempiereSession  # noqa: E402
from app.services.sql_direct import VIEWS_CATALOG, _ALLOWED_TABLES  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Extracción de tablas y columnas del catálogo
# ─────────────────────────────────────────────────────────────────────

# Palabras SQL que a veces se detectan como tablas pero no lo son
SQL_KEYWORDS = {
    "adempiere", "as", "select", "from", "where", "join", "left", "right",
    "inner", "outer", "group", "by", "order", "having", "limit", "on",
    "and", "or", "not", "in", "is", "null", "like", "ilike", "case",
    "when", "then", "else", "end", "union", "all", "with", "distinct",
    "count", "sum", "avg", "min", "max", "coalesce", "extract", "year",
    "month", "day", "current_date", "interval", "lateral", "true", "false",
    "between", "cast",
}


def extract_tables_from_catalog(catalog: str) -> set[str]:
    """Extrae todas las tablas mencionadas con 'adempiere.TABLE' del catálogo."""
    tables = set()
    for m in re.finditer(r'adempiere\.(\w+)', catalog, re.IGNORECASE):
        tbl = m.group(1).lower()
        if tbl not in SQL_KEYWORDS:
            tables.add(tbl)
    return tables


def extract_columns_from_catalog(catalog: str) -> dict[str, set[str]]:
    """Extrae columnas mencionadas como 'alias.columna' en los ejemplos SQL.

    Retorna dict {tabla_alias: {columnas}} — pero como los aliases suelen ser
    i/m/p/c/etc, no podemos mapearlos a tabla concreta sin parsear el SQL.
    En su lugar, extrae por referencia explícita tipo 'c_invoice.issotrx' o
    dentro de documentación.

    Para validación más robusta, consumimos también los aliases del SQL de
    los ejemplos y los resolvemos con el nombre de la tabla.
    """
    cols_by_table: dict[str, set[str]] = {}

    # 1. Referencias explícitas tipo "tabla.columna" en los comentarios/docs
    #    Ej: "hr_process.hrdate", "c_invoice.totallines"
    for m in re.finditer(r'(\b[a-z_]+\b)\.([a-z_][a-z_0-9]*)', catalog, re.IGNORECASE):
        tbl = m.group(1).lower()
        col = m.group(2).lower()
        if tbl in SQL_KEYWORDS or col in SQL_KEYWORDS:
            continue
        # Heurística: solo considerar si parece nombre de tabla iDempiere
        # (tiene guión bajo o empieza con prefijo conocido c_, m_, hr_, ad_, lve_, pp_)
        if "_" in tbl or tbl.startswith(("c_", "m_", "hr_", "ad_", "lve_", "pp_")):
            cols_by_table.setdefault(tbl, set()).add(col)

    # 2. Extraer aliases de FROM/JOIN en los ejemplos SQL y resolver columnas
    #    Ej: "FROM adempiere.c_invoice i" → alias "i" = "c_invoice"
    alias_to_table: dict[str, str] = {}
    for m in re.finditer(
        r'(?:FROM|JOIN)\s+adempiere\.(\w+)(?:\s+AS)?\s+(\w+)',
        catalog, re.IGNORECASE,
    ):
        tbl = m.group(1).lower()
        alias = m.group(2).lower()
        if alias in SQL_KEYWORDS or alias == tbl:
            continue
        alias_to_table[alias] = tbl

    # 3. Por cada uso de "alias.columna" en el SQL, resolver a tabla real
    for m in re.finditer(r'(\b\w+\b)\.(\w+)', catalog):
        alias = m.group(1).lower()
        col = m.group(2).lower()
        if alias in alias_to_table and col not in SQL_KEYWORDS:
            tbl = alias_to_table[alias]
            cols_by_table.setdefault(tbl, set()).add(col)

    return cols_by_table


# ─────────────────────────────────────────────────────────────────────
# Consultas contra iDempiere
# ─────────────────────────────────────────────────────────────────────

def get_existing_tables() -> set[str]:
    """Trae todas las tablas/views del schema adempiere en iDempiere."""
    db = IdempiereSession()
    try:
        rows = db.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'adempiere'
            UNION
            SELECT table_name FROM information_schema.views
            WHERE table_schema = 'adempiere'
        """)).fetchall()
        return {r[0].lower() for r in rows}
    finally:
        db.close()


def get_existing_columns(table: str) -> set[str]:
    """Trae columnas reales de una tabla en iDempiere."""
    db = IdempiereSession()
    try:
        rows = db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'adempiere' AND table_name = :tbl
        """), {"tbl": table.lower()}).fetchall()
        return {r[0].lower() for r in rows}
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────
# Validación
# ─────────────────────────────────────────────────────────────────────

def validate() -> dict:
    report = {
        "tablas_catalogo": 0,
        "tablas_whitelist": 0,
        "tablas_inexistentes_en_idempiere": [],
        "tablas_en_whitelist_sin_uso": [],
        "columnas_inexistentes": [],  # {tabla, columna}
        "resumen": "",
    }

    # 1. Recolectar del catálogo
    catalog_tables = extract_tables_from_catalog(VIEWS_CATALOG)
    catalog_columns = extract_columns_from_catalog(VIEWS_CATALOG)
    whitelist_tables = {t.lower() for t in _ALLOWED_TABLES}

    report["tablas_catalogo"] = len(catalog_tables)
    report["tablas_whitelist"] = len(whitelist_tables)

    # 2. Consultar iDempiere
    print("🔍 Consultando schema de iDempiere...", flush=True)
    existing = get_existing_tables()
    print(f"   → {len(existing)} tablas/views encontradas en schema 'adempiere'")

    # 3. Validar tablas
    print("\n🔎 Validando tablas del whitelist + catálogo...", flush=True)
    all_referenced = catalog_tables | whitelist_tables
    for tbl in sorted(all_referenced):
        if tbl not in existing:
            report["tablas_inexistentes_en_idempiere"].append(tbl)

    # 4. Validar columnas de cada tabla que EXISTE
    print("\n🔎 Validando columnas referenciadas en el catálogo...", flush=True)
    for tbl in sorted(catalog_columns.keys()):
        if tbl not in existing:
            # Ya se reportó como tabla inexistente
            continue
        real_cols = get_existing_columns(tbl)
        for col in catalog_columns[tbl]:
            if col not in real_cols:
                report["columnas_inexistentes"].append({"tabla": tbl, "columna": col})

    # 5. Resumen
    issues = (
        len(report["tablas_inexistentes_en_idempiere"])
        + len(report["columnas_inexistentes"])
    )
    if issues == 0:
        report["resumen"] = f"✅ Catálogo COHERENTE con iDempiere (0 problemas)."
    else:
        report["resumen"] = (
            f"❌ {issues} problemas detectados — "
            f"{len(report['tablas_inexistentes_en_idempiere'])} tablas inexistentes, "
            f"{len(report['columnas_inexistentes'])} columnas inexistentes."
        )

    return report


def format_report(report: dict) -> str:
    lines = []
    lines.append("=" * 78)
    lines.append("🔎 VALIDACIÓN DE CATÁLOGO SQL DIRECTO vs iDempiere")
    lines.append("=" * 78)
    lines.append(f"Tablas en el catálogo: {report['tablas_catalogo']}")
    lines.append(f"Tablas en _ALLOWED_TABLES: {report['tablas_whitelist']}")
    lines.append("")
    lines.append(report["resumen"])
    lines.append("")

    if report["tablas_inexistentes_en_idempiere"]:
        lines.append("─" * 78)
        lines.append("❌ TABLAS QUE NO EXISTEN EN iDEMPIERE")
        lines.append("─" * 78)
        lines.append("Estas tablas están en el catálogo/whitelist pero NO existen:")
        for t in report["tablas_inexistentes_en_idempiere"]:
            lines.append(f"  - adempiere.{t}")
        lines.append("\n🔧 Acción: quitar del whitelist y/o actualizar el catálogo")
        lines.append("   con el nombre correcto de la tabla.")
        lines.append("")

    if report["columnas_inexistentes"]:
        lines.append("─" * 78)
        lines.append("❌ COLUMNAS QUE NO EXISTEN")
        lines.append("─" * 78)
        lines.append("El catálogo menciona estas columnas pero NO existen en las tablas:")
        by_table: dict[str, list[str]] = {}
        for item in report["columnas_inexistentes"]:
            by_table.setdefault(item["tabla"], []).append(item["columna"])
        for tbl in sorted(by_table):
            lines.append(f"  adempiere.{tbl}:")
            for col in sorted(by_table[tbl]):
                lines.append(f"    - {col}")
        lines.append("\n🔧 Acción: corregir el catálogo con los nombres reales de")
        lines.append("   columna (consultar con information_schema.columns).")
        lines.append("   Los bugs como 'hr_process.hrdate' se detectan acá.")
        lines.append("")

    issues = (
        len(report["tablas_inexistentes_en_idempiere"])
        + len(report["columnas_inexistentes"])
    )
    if issues == 0:
        lines.append("─" * 78)
        lines.append("✅ TODO EN ORDEN")
        lines.append("─" * 78)
        lines.append("Todas las tablas y columnas mencionadas en el catálogo existen")
        lines.append("en iDempiere. El bot no debería tener errores de 'columna inexistente'")
        lines.append("ni 'relation does not exist' por el catálogo actual.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Salida JSON")
    args = parser.parse_args()

    report = validate()

    if args.json:
        import json
        print(json.dumps(report, indent=2, default=str))
    else:
        print(format_report(report))

    # Exit code 1 si hay problemas (útil para CI)
    issues = (
        len(report["tablas_inexistentes_en_idempiere"])
        + len(report["columnas_inexistentes"])
    )
    sys.exit(1 if issues > 0 else 0)


if __name__ == "__main__":
    main()

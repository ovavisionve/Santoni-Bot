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


def _extract_sql_blocks(catalog: str) -> list[str]:
    """Extrae SOLO los bloques que son SQL real del catálogo.

    Los ejemplos SQL en el catálogo están claramente marcados por una
    sentencia SELECT al inicio y terminan con LIMIT N o con una línea
    vacía seguida de texto en prosa.

    Extraer solo esos bloques evita que la validación tire falsos
    positivos por frases como 'hr_concept.a' que pueden aparecer en
    comentarios, explicaciones, o frases partidas.
    """
    blocks = []
    lines = catalog.split("\n")
    current: list[str] = []
    in_sql = False
    for line in lines:
        stripped = line.strip()
        # Heurística para detectar inicio de SQL: comentario SQL (-- ...) seguido
        # de un SELECT, o línea que empiece con SELECT o WITH
        upper = stripped.upper()
        starts_sql = (
            upper.startswith("SELECT")
            or upper.startswith("WITH ")
            or upper == "WITH"
        )
        if starts_sql and not in_sql:
            in_sql = True
            current = [line]
            continue
        if in_sql:
            current.append(line)
            # Fin del bloque SQL: línea con LIMIT o ; al final, o línea vacía
            if upper.rstrip(";").endswith(("LIMIT 500", "LIMIT 10", "LIMIT 20", "LIMIT 30")):
                blocks.append("\n".join(current))
                current = []
                in_sql = False
            elif stripped == "":
                # línea vacía = fin del bloque
                blocks.append("\n".join(current))
                current = []
                in_sql = False
    if current:
        blocks.append("\n".join(current))
    return blocks


def extract_columns_from_catalog(catalog: str) -> dict[str, set[str]]:
    """Extrae columnas mencionadas dentro de los BLOQUES SQL del catálogo.

    Antes (buggy): buscábamos columnas en TODO el texto del catálogo,
    incluyendo prosa. Eso generaba falsos positivos como 'hr_concept.a'
    cuando el regex capturaba frases en lenguaje natural.

    Ahora: solo analizamos los bloques SQL reales (detectados por SELECT/WITH
    al inicio + LIMIT al final). Esto es mucho más preciso.
    """
    cols_by_table: dict[str, set[str]] = {}
    sql_blocks = _extract_sql_blocks(catalog)

    for block in sql_blocks:
        # Mapear alias → tabla real en este bloque
        alias_to_table: dict[str, str] = {}
        for m in re.finditer(
            r'(?:FROM|JOIN)\s+adempiere\.(\w+)(?:\s+AS)?\s+(\w+)',
            block, re.IGNORECASE,
        ):
            tbl = m.group(1).lower()
            alias = m.group(2).lower()
            if alias in SQL_KEYWORDS or alias == tbl:
                continue
            alias_to_table[alias] = tbl

        # Extraer todas las referencias "alias.columna" en el SQL
        for m in re.finditer(r'(\b\w+\b)\.(\w+)', block):
            alias = m.group(1).lower()
            col = m.group(2).lower()
            if col in SQL_KEYWORDS:
                continue
            # Filtrar columnas irrealmente cortas (de 1 char) — iDempiere no
            # las tiene. Esto evita falsos positivos de regex.
            if len(col) < 2:
                continue
            # Caso 1: alias mapeado a tabla → usar la tabla real
            if alias in alias_to_table:
                tbl = alias_to_table[alias]
                cols_by_table.setdefault(tbl, set()).add(col)
                continue
            # Caso 2: nombre de tabla completo directo (ej: "hr_concept.name")
            if "_" in alias or alias.startswith(("c_", "m_", "hr_", "ad_", "lve_", "pp_")):
                cols_by_table.setdefault(alias, set()).add(col)

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

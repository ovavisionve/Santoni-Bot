#!/usr/bin/env python3
"""
Validador de EJEMPLOS_SQL del catálogo contra iDempiere real.

Los ejemplos de queries en `sql_direct/catalog/ejemplos.py` son la fuente
de verdad que Claude imita. Si uno de ellos tiene una columna inexistente,
una sintaxis PostgreSQL inválida, o un JOIN que falla, Claude va a copiar
ese patrón → bugs en producción.

Este script:
  1. Extrae cada bloque SQL de EJEMPLOS_SQL (separados por comentarios SQL)
  2. Lo ejecuta con `EXPLAIN` contra iDempiere (NO ejecuta, solo valida plan)
  3. Si EXPLAIN falla → reporta el error con el SQL problemático

Razón de usar EXPLAIN en vez de ejecución real:
  - Más rápido (solo planner, no scan)
  - No trae filas al cliente (sin carga de datos)
  - Detecta TODOS los errores de sintaxis + schema que nos importan

Complementa a `validate_catalog.py` (que valida nombres de tablas/columnas)
con una capa más profunda: que el SQL efectivamente sea parseable y
planificable por PostgreSQL.

Uso:
    docker compose exec backend python scripts/qa/validate_catalog_examples.py
    docker compose exec backend python scripts/qa/validate_catalog_examples.py --json
    docker compose exec backend python scripts/qa/validate_catalog_examples.py --only sueldo
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Script en backend/scripts/qa/ → parent.parent.parent = backend root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402
from app.database import IdempiereSession  # noqa: E402
from app.services.sql_direct.catalog.ejemplos import EJEMPLOS_SQL  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Extracción de bloques SQL de EJEMPLOS_SQL
# ─────────────────────────────────────────────────────────────────────

def extract_sql_blocks(catalog_text: str) -> list[dict]:
    """Extrae bloques SQL y su título (primer comentario `-- ...`).

    Cada bloque en ejemplos.py tiene forma:
        -- Título descriptivo del ejemplo
        -- Notas adicionales sobre el patrón
        SELECT ... FROM adempiere....
        ...
        LIMIT 500

    Separador entre bloques: línea en blanco seguida de otro `-- Título`.
    """
    blocks: list[dict] = []
    lines = catalog_text.split("\n")

    current_title: str | None = None
    current_comments: list[str] = []
    current_sql: list[str] = []
    in_sql = False

    def flush():
        if current_sql:
            blocks.append({
                "title": current_title or "(sin título)",
                "comments": "\n".join(current_comments),
                "sql": "\n".join(current_sql).strip(),
            })

    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()
        starts_sql = (
            upper.startswith("SELECT")
            or upper.startswith("WITH ")
            or upper == "WITH"
        )

        if stripped.startswith("-- ") and not in_sql:
            if not current_title:
                current_title = stripped[3:]
            else:
                current_comments.append(stripped[3:])
            continue

        if starts_sql and not in_sql:
            in_sql = True
            current_sql = [line]
            continue

        if in_sql:
            if stripped == "" and current_sql:
                flush()
                current_title = None
                current_comments = []
                current_sql = []
                in_sql = False
                continue
            current_sql.append(line)

    flush()
    return [b for b in blocks if b["sql"]]


# ─────────────────────────────────────────────────────────────────────
# Validación vía EXPLAIN
# ─────────────────────────────────────────────────────────────────────

def validate_with_explain(sql: str) -> tuple[bool, str | None]:
    """Corre EXPLAIN sobre el SQL. Devuelve (ok, error_msg).

    Usa transacción que se rollback inmediatamente. EXPLAIN no ejecuta
    el query, solo valida que el planner pueda parsear + resolver schema.
    """
    db = IdempiereSession()
    try:
        # Wrap en EXPLAIN (sin ANALYZE — no queremos ejecutar)
        # Quitar LIMIT inline si ya está; EXPLAIN acepta el SELECT completo.
        stmt = f"EXPLAIN {sql.rstrip(';')}"
        db.execute(text(stmt))
        return True, None
    except SQLAlchemyError as exc:
        # Extraer solo el mensaje interno, sin el traceback SQLAlchemy
        msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
        return False, msg.strip()
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        try:
            db.rollback()
        except Exception:
            pass
        db.close()


# ─────────────────────────────────────────────────────────────────────
# Orquestación + reporte
# ─────────────────────────────────────────────────────────────────────

def validate_all(only: str | None = None) -> dict:
    blocks = extract_sql_blocks(EJEMPLOS_SQL)
    if only:
        blocks = [b for b in blocks if only.lower() in b["title"].lower()]

    report = {
        "total": len(blocks),
        "ok": 0,
        "failed": 0,
        "results": [],
    }

    for i, block in enumerate(blocks, 1):
        print(f"[{i}/{len(blocks)}] {block['title'][:70]}... ", end="", flush=True)
        ok, err = validate_with_explain(block["sql"])
        report["results"].append({
            "title": block["title"],
            "ok": ok,
            "error": err,
            "sql_preview": block["sql"][:300],
        })
        if ok:
            report["ok"] += 1
            print("✅")
        else:
            report["failed"] += 1
            print("❌")
            print(f"    → {err}")

    report["pct_ok"] = int(100 * report["ok"] / report["total"]) if report["total"] else 0
    return report


def format_text_report(report: dict) -> str:
    lines = [
        "",
        "=" * 78,
        "VALIDACIÓN DE EJEMPLOS_SQL vs iDempiere (via EXPLAIN)",
        "=" * 78,
        f"Total bloques:   {report['total']}",
        f"OK:              {report['ok']}  ({report['pct_ok']}%)",
        f"FAILED:          {report['failed']}",
        "=" * 78,
    ]
    if report["failed"]:
        lines += ["", "BLOQUES QUE FALLARON:", "-" * 78]
        for r in report["results"]:
            if not r["ok"]:
                lines.append(f"❌ {r['title']}")
                lines.append(f"   Error: {r['error']}")
                lines.append(f"   SQL preview:")
                for ln in r["sql_preview"].split("\n")[:6]:
                    lines.append(f"     {ln}")
                lines.append("")
        lines.append(
            "🔧 Acción: corregir el ejemplo en "
            "`backend/app/services/sql_direct/catalog/ejemplos.py`. "
            "Si Claude imita este patrón y el patrón está roto, "
            "genera SQL roto → fallback silencioso al agente clásico."
        )
    else:
        lines += [
            "",
            "✅ TODOS LOS EJEMPLOS_SQL son válidos contra iDempiere.",
            "",
            "Esto significa que Claude tiene un set de patrones confiables",
            "para imitar. Los ejemplos cubren RRHH, ventas, CxC aging,",
            "ausentismo multi-mes, clasificación ProForma/FacturaLegal, etc.",
        ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Filtra por substring en el título del ejemplo",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Salida JSON en vez de texto",
    )
    args = parser.parse_args()

    report = validate_all(only=args.only)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(format_text_report(report))

    sys.exit(1 if report["failed"] > 0 else 0)


if __name__ == "__main__":
    main()

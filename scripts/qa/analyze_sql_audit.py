#!/usr/bin/env python3
"""
Análisis automatizado del audit log de SQL Directo.

Lee la tabla `sql_audit` de la DB local y detecta patrones de fallas
que sugieren fixes al catálogo o al prompt de Claude. Genera un
reporte legible con sugerencias priorizadas.

Uso:
    # Desde el host (fuera del contenedor)
    docker compose exec backend python scripts/qa/analyze_sql_audit.py

    # Por período específico
    docker compose exec backend python scripts/qa/analyze_sql_audit.py --days 7

    # Formato JSON para procesar programáticamente
    docker compose exec backend python scripts/qa/analyze_sql_audit.py --json

Lo que detecta:
    1. Errores frecuentes agrupados por causa raíz (columna inexistente,
       tabla bloqueada, tipo incompatible, etc.)
    2. Queries con rows_returned bajo para preguntas agregadas
    3. Queries donde auto-retry tuvo que rescatar al LLM
    4. Queries lentas (elapsed_ms > 10000)
    5. format_failed frecuentes (Claude falla formateando)
    6. Sugerencias concretas de fix por cada patrón
"""
import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Permite correr desde cualquier directorio
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "backend"))

from sqlalchemy import text  # noqa: E402
from app.database import SessionLocal  # noqa: E402


# ─────────────────────────────────────────────────────────────────────
# Detectores de patrones (extensibles)
# ─────────────────────────────────────────────────────────────────────

# Cada detector recibe el texto de error y devuelve (patrón, sugerencia) si
# matchea, o None si no aplica. Agregar nuevos detectores acá.

def _detect_column_not_exist(error: str) -> tuple[str, str] | None:
    """Detecta columnas inexistentes y sugiere el nombre correcto si PostgreSQL lo sugirió."""
    m = re.search(
        r'column\s+([\w."]+)\s+does not exist',
        error, re.IGNORECASE,
    )
    if not m:
        return None
    col = m.group(1)
    hint = re.search(r'HINT:\s*Perhaps you meant[^"]*"([^"]+)"', error)
    if hint:
        return (
            f"columna_inexistente:{col}",
            f"🔧 Columna `{col}` no existe. PostgreSQL sugiere `{hint.group(1)}`. "
            f"Agregar al catálogo y/o a REGLA #6 la columna correcta."
        )
    return (
        f"columna_inexistente:{col}",
        f"🔧 Columna `{col}` no existe. Verificar schema real con "
        f"information_schema.columns y actualizar el catálogo."
    )


def _detect_table_not_whitelisted(error: str) -> tuple[str, str] | None:
    m = re.search(
        r"Tabla no permitida:\s*([\w_]+)",
        error,
    )
    if not m:
        return None
    tbl = m.group(1)
    return (
        f"tabla_no_whitelist:{tbl}",
        f"🔧 Tabla `{tbl}` no está en _ALLOWED_TABLES. Si es legítima "
        f"(existe en iDempiere), agregala al whitelist de sql_direct.py. "
        f"Si no existe, actualizar catálogo para que Claude no la genere."
    )


def _detect_table_not_exist(error: str) -> tuple[str, str] | None:
    m = re.search(
        r'relation\s+"([\w.]+)"\s+does not exist',
        error, re.IGNORECASE,
    )
    if not m:
        return None
    tbl = m.group(1)
    return (
        f"tabla_inexistente:{tbl}",
        f"🔧 Tabla `{tbl}` no existe en iDempiere de Santoni. "
        f"Actualizar el catálogo indicando cuál es la tabla correcta "
        f"o agregar regla para que Claude no la genere."
    )


def _detect_type_mismatch(error: str) -> tuple[str, str] | None:
    m = re.search(
        r'(operator does not exist|invalid input syntax|cannot cast)',
        error, re.IGNORECASE,
    )
    if not m:
        return None
    return (
        "type_mismatch",
        "🔧 Error de tipo de datos. Revisar el SQL generado para ver si "
        "está comparando tipos incompatibles o haciendo cast inválido."
    )


def _detect_ambiguous_column(error: str) -> tuple[str, str] | None:
    m = re.search(
        r'column reference\s+"([\w.]+)"\s+is ambiguous',
        error, re.IGNORECASE,
    )
    if not m:
        return None
    col = m.group(1)
    return (
        f"columna_ambigua:{col}",
        f"🔧 Columna `{col}` aparece en múltiples tablas del JOIN y no tiene "
        f"alias. Agregar al catálogo nota: 'siempre calificar nombre con alias "
        f"de tabla' (ej: i.dateinvoiced en vez de dateinvoiced)."
    )


_DETECTORS = [
    _detect_column_not_exist,
    _detect_table_not_whitelisted,
    _detect_table_not_exist,
    _detect_type_mismatch,
    _detect_ambiguous_column,
]


def classify_error(error: str) -> tuple[str, str]:
    """Clasifica un error_detail en un patrón conocido + sugerencia.

    Returns (pattern_key, suggestion). Si no matchea ninguno, devuelve
    ('desconocido', 'Error no clasificado — revisar manualmente').
    """
    if not error:
        return ("sin_error", "Sin error registrado.")
    for detector in _DETECTORS:
        result = detector(error)
        if result:
            return result
    return ("desconocido", f"Error no clasificado — revisar manualmente: {error[:150]}")


# ─────────────────────────────────────────────────────────────────────
# Análisis
# ─────────────────────────────────────────────────────────────────────

def analyze(days: int = 7, limit: int = 1000, as_json: bool = False) -> dict:
    """Corre el análisis sobre las últimas `days` días del audit log."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT id, message, status, rows_returned, elapsed_ms,
                       format_failed, sql_generated, sql_final, error_detail,
                       created_at
                FROM sql_audit
                WHERE created_at >= :since
                ORDER BY id DESC
                LIMIT :limit
            """),
            {"since": since, "limit": limit},
        ).fetchall()
    finally:
        db.close()

    total = len(rows)
    if total == 0:
        return {
            "periodo_dias": days,
            "total_queries": 0,
            "mensaje": "No hay queries en el período. El audit log está vacío.",
        }

    # Contadores
    by_status: Counter = Counter()
    error_patterns: Counter = Counter()
    pattern_suggestions: dict = {}
    pattern_examples: defaultdict = defaultdict(list)  # pattern → [queries que lo dispararon]
    retries_success: int = 0
    slow_queries: list = []
    format_failures: int = 0
    empty_results: list = []
    rows_returned_low_for_aggregate: list = []

    # Patrones que indican pregunta "agregada" (espera desglose/total)
    AGGREGATE_KEYWORDS = (
        "resumen", "total", "reporte", "dame el", "cuánto", "cuanto",
        "cuántos", "cuantos", "cuántas", "cuantas",
        "\u00e1ndice", "indice", "promedio", "top ",
    )

    for r in rows:
        status = r.status or "unknown"
        by_status[status] += 1

        # Clasificar errores
        if status in ("validation_failed", "execute_error") or status.startswith("validation_failed_") or status.startswith("execute_error_"):
            if r.error_detail:
                pattern, suggestion = classify_error(r.error_detail)
                error_patterns[pattern] += 1
                pattern_suggestions[pattern] = suggestion
                if len(pattern_examples[pattern]) < 3:
                    pattern_examples[pattern].append({
                        "audit_id": r.id,
                        "message": r.message[:80] if r.message else "",
                        "error_detail": (r.error_detail or "")[:200],
                    })

        # Éxito después de retry (el auto-retry rescató)
        if status.startswith("success_after_retry"):
            retries_success += 1

        # Format failures
        if r.format_failed:
            format_failures += 1

        # Queries lentas (> 10s)
        if r.elapsed_ms and r.elapsed_ms > 10000:
            slow_queries.append({
                "audit_id": r.id,
                "message": (r.message or "")[:80],
                "elapsed_ms": r.elapsed_ms,
            })

        # Empty results para preguntas agregadas (posible bug)
        if status == "empty_result" and r.message:
            msg_lower = r.message.lower()
            if any(k in msg_lower for k in AGGREGATE_KEYWORDS):
                empty_results.append({
                    "audit_id": r.id,
                    "message": r.message[:80],
                })

        # Rows bajo para pregunta agregada (posible SQL restrictivo)
        if (
            status == "success"
            and r.rows_returned in (1, 2)
            and r.message
            and any(k in r.message.lower() for k in ("resumen", "desglose", "por tipo", "por categoria"))
        ):
            rows_returned_low_for_aggregate.append({
                "audit_id": r.id,
                "message": r.message[:80],
                "rows_returned": r.rows_returned,
            })

    # Construir reporte
    report = {
        "periodo_dias": days,
        "total_queries": total,
        "por_status": dict(by_status.most_common()),
        "errores_patron": [
            {
                "patron": pattern,
                "ocurrencias": count,
                "sugerencia": pattern_suggestions[pattern],
                "ejemplos": pattern_examples[pattern],
            }
            for pattern, count in error_patterns.most_common()
        ],
        "auto_retry_rescates": retries_success,
        "format_failures": format_failures,
        "queries_lentas_10s": slow_queries[:10],
        "empty_results_sospechosos": empty_results[:10],
        "rows_bajo_para_agregado": rows_returned_low_for_aggregate[:10],
    }

    # Calcular tasa de éxito (success + success_after_retryN)
    success_count = sum(v for k, v in by_status.items() if k.startswith("success"))
    report["tasa_exito"] = round(100 * success_count / total, 2) if total else 0

    return report


def format_report(report: dict) -> str:
    """Formatea el reporte como texto legible."""
    if report.get("total_queries", 0) == 0:
        return f"\n📊 Audit log vacío en los últimos {report['periodo_dias']} días.\n"

    lines = []
    lines.append("=" * 78)
    lines.append(f"📊 ANÁLISIS DEL AUDIT LOG — últimos {report['periodo_dias']} días")
    lines.append("=" * 78)
    lines.append(f"Total queries analizadas: {report['total_queries']}")
    lines.append(f"Tasa de éxito: {report['tasa_exito']}%")
    lines.append(f"Auto-retry rescates: {report['auto_retry_rescates']}")
    lines.append(f"Format failures: {report['format_failures']}")
    lines.append("")

    lines.append("─" * 78)
    lines.append("DISTRIBUCIÓN POR STATUS")
    lines.append("─" * 78)
    for status, count in report["por_status"].items():
        pct = 100 * count / report["total_queries"]
        lines.append(f"  {status:<35} {count:>6}  ({pct:>5.1f}%)")
    lines.append("")

    if report["errores_patron"]:
        lines.append("─" * 78)
        lines.append("ERRORES AGRUPADOS POR PATRÓN — PRIORIZADOS")
        lines.append("─" * 78)
        for idx, item in enumerate(report["errores_patron"], 1):
            lines.append(f"\n[{idx}] {item['patron']}  ({item['ocurrencias']} veces)")
            lines.append(f"    {item['sugerencia']}")
            if item["ejemplos"]:
                lines.append("    Ejemplos:")
                for ex in item["ejemplos"]:
                    lines.append(f"      - ID {ex['audit_id']}: {ex['message']}")
                    lines.append(f"        Error: {ex['error_detail'][:120]}")
        lines.append("")

    if report["queries_lentas_10s"]:
        lines.append("─" * 78)
        lines.append("QUERIES LENTAS (> 10 segundos)")
        lines.append("─" * 78)
        for q in report["queries_lentas_10s"]:
            lines.append(f"  ID {q['audit_id']} — {q['elapsed_ms']}ms — {q['message']}")
        lines.append("")

    if report["empty_results_sospechosos"]:
        lines.append("─" * 78)
        lines.append("EMPTY RESULTS EN PREGUNTAS AGREGADAS (posible bug)")
        lines.append("─" * 78)
        for q in report["empty_results_sospechosos"]:
            lines.append(f"  ID {q['audit_id']}: {q['message']}")
        lines.append("")

    if report["rows_bajo_para_agregado"]:
        lines.append("─" * 78)
        lines.append("ROWS BAJO PARA PREGUNTA AGREGADA (posible SQL restrictivo)")
        lines.append("─" * 78)
        for q in report["rows_bajo_para_agregado"]:
            lines.append(f"  ID {q['audit_id']} — {q['rows_returned']} rows — {q['message']}")
        lines.append("")

    lines.append("─" * 78)
    lines.append("SIGUIENTE PASO")
    lines.append("─" * 78)
    if report["errores_patron"]:
        lines.append("1. Revisar el patrón #1 de errores (el más frecuente)")
        lines.append("2. Aplicar la sugerencia al catálogo o al prompt")
        lines.append("3. Deploy + re-análisis para validar reducción")
    else:
        lines.append("✅ No hay errores recurrentes. El bot está saludable.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="Días hacia atrás (default 7)")
    parser.add_argument("--limit", type=int, default=1000, help="Máx queries a analizar")
    parser.add_argument("--json", action="store_true", help="Salida en JSON")
    args = parser.parse_args()

    report = analyze(days=args.days, limit=args.limit, as_json=args.json)

    if args.json:
        import json
        print(json.dumps(report, indent=2, default=str))
    else:
        print(format_report(report))


if __name__ == "__main__":
    main()

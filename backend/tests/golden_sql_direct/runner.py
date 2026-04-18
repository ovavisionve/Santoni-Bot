"""Runner del golden suite de SQL Directo.

Ejecuta cada caso de prueba invocando directamente a
`process_with_sql_direct()` y valida la respuesta.

Validaciones aplicadas:
  - Si expect_sql=True: el dict devuelto debe tener metadata.sql_generated
    y las tablas `must_contain_tables` deben aparecer en el SQL.
  - Si expect_sql=False + expect_clarification=True: la respuesta debe
    tener classification='sql_direct_clarification' y el texto debe
    contener las clarification_keywords (matcheo case-insensitive).
  - min_rows: filas devueltas >= min_rows (cuando aplica).
  - forbidden_tables: NO aparecen en el SQL generado.
  - must_contain_keywords: aparecen en el SQL (GROUP BY, UNION ALL, etc).

Reporta PASS/WARN/FAIL por caso con motivos específicos.
"""

import asyncio
import re
import time
from typing import Any

from tests.golden_sql_direct import ALL_CASES


# ─────────────────────────────────────────────────────────────────────
# Utilidades de verificación
# ─────────────────────────────────────────────────────────────────────


def _extract_tables_from_sql(sql: str) -> set[str]:
    """Extrae nombres de tabla 'adempiere.xxx' del SQL."""
    return {
        m.group(1).lower()
        for m in re.finditer(r"adempiere\.(\w+)", sql, re.IGNORECASE)
    }


def _check_keywords(sql: str, keywords: list[str]) -> list[str]:
    """Devuelve lista de keywords faltantes (case-insensitive)."""
    up = sql.upper()
    return [kw for kw in keywords if kw.upper() not in up]


def _check_clarification_text(response: str, keywords: list[str]) -> list[str]:
    """Devuelve lista de keywords faltantes en el texto de clarificación."""
    low = response.lower()
    return [kw for kw in keywords if kw.lower() not in low]


# ─────────────────────────────────────────────────────────────────────
# Lógica de evaluación por caso
# ─────────────────────────────────────────────────────────────────────


def _eval_sql_case(case: dict, result: dict | None) -> tuple[str, list[str]]:
    """Evalúa un caso que espera SQL generado. Devuelve (status, motivos)."""
    motivos: list[str] = []

    if result is None:
        return "FAIL", ["process_with_sql_direct devolvió None (fallback activado)"]

    meta = result.get("metadata", {})
    sql = meta.get("sql_generated", "")
    if not sql:
        return "FAIL", ["Respuesta sin metadata.sql_generated"]

    tables_used = _extract_tables_from_sql(sql)

    for tbl in case.get("must_contain_tables", []):
        if tbl.lower() not in tables_used:
            motivos.append(f"No usa tabla requerida: adempiere.{tbl}")

    for tbl in case.get("forbidden_tables", []):
        if tbl.lower() in tables_used:
            motivos.append(f"Usa tabla prohibida: adempiere.{tbl}")

    missing = _check_keywords(sql, case.get("must_contain_keywords", []))
    for kw in missing:
        motivos.append(f"Falta keyword en SQL: {kw}")

    rows = meta.get("rows_returned", 0)
    min_rows = case.get("min_rows", 0)
    if rows < min_rows:
        motivos.append(f"rows_returned={rows} < min_rows={min_rows}")

    if motivos:
        return ("WARN" if rows >= min_rows else "FAIL"), motivos
    return "PASS", []


def _eval_clarification_case(case: dict, result: dict | None) -> tuple[str, list[str]]:
    """Evalúa un caso que espera clarificación (REGLA #9)."""
    if result is None:
        return "FAIL", [
            "Esperaba clarificación (REGLA #9) pero process devolvió None "
            "(cayó a fallback)"
        ]

    meta = result.get("metadata", {})
    classification = meta.get("classification", "")
    if classification != "sql_direct_clarification":
        return "FAIL", [
            f"Esperaba classification='sql_direct_clarification', "
            f"obtuve '{classification}'"
        ]

    text = result.get("response", "")
    missing = _check_clarification_text(text, case.get("clarification_keywords", []))
    if missing:
        return "FAIL", [
            f"Texto de clarificación no menciona: {', '.join(missing)}"
        ]
    return "PASS", []


def _eval_decline_case(case: dict, result: dict | None) -> tuple[str, list[str]]:
    """Caso que espera NO_SQL sin clarificación (declinar silencioso).

    Hoy no tenemos casos así en el suite — todos los expect_sql=False
    también esperan clarificación. Queda por si se agregan a futuro.
    """
    if result is None:
        return "PASS", []
    return "FAIL", ["Esperaba decline (None) pero hubo respuesta"]


async def _run_one(case: dict) -> dict[str, Any]:
    """Corre un caso. Devuelve dict con status, motivos, elapsed."""
    from app.services.sql_direct import process_with_sql_direct

    t0 = time.time()
    try:
        result = await process_with_sql_direct(
            message=case["pregunta"],
            history=case.get("history") or [],
            org_ids=None,
        )
    except Exception as exc:
        return {
            "id": case["id"],
            "status": "FAIL",
            "motivos": [f"Excepción: {type(exc).__name__}: {exc}"],
            "elapsed_s": time.time() - t0,
        }

    if case.get("expect_sql"):
        status, motivos = _eval_sql_case(case, result)
    elif case.get("expect_clarification"):
        status, motivos = _eval_clarification_case(case, result)
    else:
        status, motivos = _eval_decline_case(case, result)

    return {
        "id": case["id"],
        "status": status,
        "motivos": motivos,
        "elapsed_s": time.time() - t0,
    }


# ─────────────────────────────────────────────────────────────────────
# Orquestador
# ─────────────────────────────────────────────────────────────────────


async def run_all(
    cases: list[dict] | None = None,
    only: str | None = None,
    delay: float = 0.0,
) -> list[dict]:
    """Corre todos los casos (o un subset filtrado por --only)."""
    target = cases if cases is not None else ALL_CASES
    if only:
        target = [c for c in target if only.lower() in c["id"].lower()]

    results = []
    for i, case in enumerate(target, 1):
        print(f"[{i}/{len(target)}] {case['id']} ... ", end="", flush=True)
        res = await _run_one(case)
        results.append(res)
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(res["status"], "?")
        print(f"{icon} {res['status']} ({res['elapsed_s']:.1f}s)")
        if res["motivos"]:
            for m in res["motivos"]:
                print(f"    → {m}")
        if delay > 0 and i < len(target):
            await asyncio.sleep(delay)
    return results


def format_summary(results: list[dict]) -> str:
    """Genera resumen final PASS/WARN/FAIL + tasa de éxito."""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "WARN")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    lines = [
        "",
        "=" * 70,
        "RESUMEN GOLDEN SUITE SQL DIRECTO",
        "=" * 70,
        f"Total:  {total}",
        f"PASS:   {passed} ({100 * passed // total if total else 0}%)",
        f"WARN:   {warned}",
        f"FAIL:   {failed}",
        "=" * 70,
    ]
    if failed:
        lines.append("")
        lines.append("Casos FAIL:")
        for r in results:
            if r["status"] == "FAIL":
                lines.append(f"  ❌ {r['id']}")
                for m in r["motivos"]:
                    lines.append(f"     → {m}")
    return "\n".join(lines)

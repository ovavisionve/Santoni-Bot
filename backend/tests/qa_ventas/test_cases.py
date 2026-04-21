"""
Casos de test para el agente Ventas.

Cada caso define:
  - name: etiqueta descriptiva
  - question: pregunta exacta a enviar al bot
  - fetch_expected(): ejecuta SQL de verificación y retorna el dict de valores
  - build_checks(expected, bot_numbers, bot_text): construye la lista de
    CheckResult basada en los valores esperados vs la respuesta del bot.

El runner importa CASES y las corre en secuencia.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from .comparator import CheckResult, check_amount, check_count, check_name_present
from .sql_queries import (
    collection_month,
    overdue_receivables_totals,
    top_clients_year,
    total_sales_month,
    total_sales_year,
)


@dataclass
class TestCase:
    name: str
    question: str
    fetch_expected: Callable[[], dict[str, Any]]
    build_checks: Callable[[dict[str, Any], list[float], str], list[CheckResult]]


# ── Caso 1: ventas del mes actual ────────────────────────────────────────
def _c1_checks(expected, bot_numbers, bot_text) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for moneda, data in expected["by_currency"].items():
        if moneda == "OTRO":
            continue
        checks.append(
            check_amount(f"Total ventas {moneda}", data["total"], bot_numbers, rel_tol=0.06)
        )
        checks.append(
            check_count(f"Facturas {moneda}", data["facturas"], bot_numbers)
        )
    return checks


def _c1_expected():
    now = datetime.now()
    mes, anio = now.month, now.year
    return {**total_sales_month(mes=mes, anio=anio), "mes": mes, "anio": anio}


CASE_1 = TestCase(
    name="Ventas del mes actual (VES + USD)",
    question="Resumen de ventas del mes actual",
    fetch_expected=_c1_expected,
    build_checks=_c1_checks,
)


# ── Caso 2: ventas año 2025 completo ─────────────────────────────────────
def _c2_checks(expected, bot_numbers, bot_text) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for moneda, data in expected["by_currency"].items():
        if moneda == "OTRO":
            continue
        checks.append(
            check_amount(f"Ventas 2025 {moneda}", data["total"], bot_numbers, rel_tol=0.06)
        )
    return checks


CASE_2 = TestCase(
    name="Ventas año 2025 (VES + USD)",
    question="Resumen de ventas del año 2025",
    fetch_expected=lambda: total_sales_year(anio=2025),
    build_checks=_c2_checks,
)


# ── Caso 3: top 5 clientes del año 2025 ──────────────────────────────────
def _c3_checks(expected, bot_numbers, bot_text) -> list[CheckResult]:
    checks: list[CheckResult] = []
    # Verificar que los 3 primeros clientes aparezcan en la respuesta por nombre
    for i, client in enumerate(expected["clients"][:3], 1):
        # Usar solo las primeras 3 palabras del nombre para evitar falsos negativos
        short_name = " ".join(client["cliente"].split()[:3])
        checks.append(
            check_name_present(f"Top {i}: {short_name}", short_name, bot_text)
        )
    return checks


CASE_3 = TestCase(
    name="Top 5 clientes del año 2025",
    question="Dame el top 5 de clientes por ventas del año 2025",
    fetch_expected=lambda: top_clients_year(anio=2025, limit=5),
    build_checks=_c3_checks,
)


# ── Caso 4: cobranza del mes actual ──────────────────────────────────────
def _c4_checks(expected, bot_numbers, bot_text) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for moneda, data in expected["by_currency"].items():
        if moneda == "OTRO":
            continue
        checks.append(
            check_amount(f"Cobrado {moneda}", data["total"], bot_numbers, rel_tol=0.01)
        )
    return checks


def _c4_expected():
    now = datetime.now()
    return collection_month(mes=now.month, anio=now.year)


CASE_4 = TestCase(
    name="Cobranza del mes actual",
    question="Cobranza del mes actual",
    fetch_expected=_c4_expected,
    build_checks=_c4_checks,
)


# ── Caso 5: CxC vencidas ─────────────────────────────────────────────────
def _c5_checks(expected, bot_numbers, bot_text) -> list[CheckResult]:
    checks: list[CheckResult] = []
    # Verificar que los 3 primeros morosos del SQL aparezcan en la respuesta
    for i, client in enumerate(expected.get("top_clients", [])[:3], 1):
        short_name = " ".join(client["cliente"].split()[:3])
        checks.append(
            check_name_present(f"Moroso {i}: {short_name}", short_name, bot_text)
        )
    return checks


def _c5_expected():
    from .sql_queries import top_overdue_clients
    return top_overdue_clients(limit=5)


CASE_5 = TestCase(
    name="Cuentas por cobrar vencidas (top morosos)",
    question="¿Cuáles son las cuentas por cobrar vencidas?",
    fetch_expected=_c5_expected,
    build_checks=_c5_checks,
)


# ── Caso 6: ventas de INPROA SANTONI año 2025 ────────────────────────────
def _c6_checks(expected, bot_numbers, bot_text) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for moneda, data in expected["by_currency"].items():
        if moneda == "OTRO":
            continue
        # 10% tolerancia: cuando se filtra por org_name ILIKE '%INPROA%'
        # el bot puede matchear más/menos registros dependiendo de cómo
        # el LLM pasa el nombre (INPROA vs INPROA SANTONI vs exact).
        checks.append(
            check_amount(f"INPROA 2025 {moneda}", data["total"], bot_numbers, rel_tol=0.10)
        )
    return checks


CASE_6 = TestCase(
    name="Ventas INPROA SANTONI año 2025",
    question="Ventas de INPROA SANTONI en el año 2025",
    fetch_expected=lambda: total_sales_year(anio=2025, org_name="INPROA"),
    build_checks=_c6_checks,
)


# Lista ordenada de todos los casos — la usa el runner
CASES: list[TestCase] = [CASE_1, CASE_2, CASE_3, CASE_4, CASE_5, CASE_6]

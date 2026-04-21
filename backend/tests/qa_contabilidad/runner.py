#!/usr/bin/env python3
"""
Runner de QA para el agente Contabilidad — compara bot vs iDempiere.

Uso:
    docker compose exec backend python -m tests.qa_contabilidad.runner \
        --base-url http://localhost:8000 \
        --username admin --password 'SantoniAdmin2026!'
"""

import argparse
import os
import sys
import time
from datetime import datetime

from tests.qa_ventas.bot_client import BotClient, extract_numbers
from tests.qa_ventas.comparator import (
    CheckResult, CompareReport,
    check_amount, check_count, check_name_present,
)
from tests.qa_ventas.error_classifier import classify_error, ErrorVerdict

from .sql_queries import (
    accounting_summary_year,
    account_detail,
    top_accounts_by_movement,
)


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


# ── Test Cases ───────────────────────────────────────────────────────────

def case_summary_2025():
    """Caso 1: resumen contable del año 2025 — hay movimientos."""
    expected = accounting_summary_year(anio=2025)
    total_movs = sum(t["movimientos"] for t in expected["by_type"])
    type_names = [t["tipo_nombre"] for t in expected["by_type"][:3]]
    return expected, "Resumen contable del año 2025", [
        lambda nums, text: check_count("Total movimientos", total_movs, nums)
        if total_movs < 1_000_000
        else check_amount("Total movimientos", total_movs, nums, rel_tol=0.10),
    ] + [
        (lambda name: lambda nums, text: check_name_present(
            f"Tipo: {name}", name.lower(), text
        ))(n)
        for n in type_names
    ]


def case_summary_2026():
    """Caso 2: balance general 2026 — verificar tipos de cuenta en respuesta."""
    expected = accounting_summary_year(anio=2026)
    return expected, "Balance general del año 2026", [
        lambda nums, text: check_name_present("Tipo: Activo", "activo", text),
        lambda nums, text: check_name_present("Tipo: Pasivo", "pasivo", text),
        lambda nums, text: check_name_present("Tipo: Patrimonio", "patrimonio", text),
    ]


def case_account_detail():
    """Caso 3: detalle de una cuenta contable específica (1.01 = efectivo)."""
    expected = account_detail(account_code="1.01", anio=2025)
    if expected["accounts"]:
        first = expected["accounts"][0]
        return expected, f"Detalle de la cuenta {first['codigo']} del año 2025", [
            lambda nums, text: check_name_present(
                f"Cuenta: {first['cuenta'][:25]}",
                first["cuenta"].split()[0],
                text,
            ),
        ]
    return expected, "Detalle de la cuenta 1.01 del año 2025", [
        lambda nums, text: CheckResult("Cuenta 1.01", "datos", False, None, "SQL no devolvió datos"),
    ]


def case_top_accounts():
    """Caso 4: top 5 cuentas con más movimientos."""
    expected = top_accounts_by_movement(anio=2025, limit=5)
    return expected, "¿Cuáles son las cuentas contables con más movimientos en 2025?", [
        (lambda acc: lambda nums, text: check_name_present(
            f"Cuenta {acc['codigo']}",
            acc["codigo"],
            text,
        ))(a)
        for a in expected["accounts"][:3]
    ]


CASES = [
    ("Resumen contable 2025", case_summary_2025),
    ("Balance general 2026", case_summary_2026),
    ("Detalle cuenta 1.01", case_account_detail),
    ("Top cuentas por movimiento", case_top_accounts),
]


# ── Runner ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QA Contabilidad vs iDempiere")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--username", default=None)
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    username = args.username or os.getenv("TEST_USERNAME", "admin")
    password = args.password or os.getenv("TEST_PASSWORD", "")
    if not password:
        print(f"{Colors.RED}Falta --password{Colors.RESET}")
        sys.exit(1)

    print(f"\n{Colors.BOLD}{'=' * 70}")
    print(f"  QA Contabilidad vs iDempiere")
    print(f"  Base URL: {args.base_url}")
    print(f"{'=' * 70}{Colors.RESET}\n")

    client = BotClient(args.base_url, username, password)
    try:
        client.login()
        print(f"  {Colors.GREEN}Login OK{Colors.RESET}")
    except Exception as exc:
        print(f"  {Colors.RED}Login failed: {exc}{Colors.RESET}")
        sys.exit(1)

    total_passed = 0
    total_checks_passed = 0
    total_checks = 0

    for i, (name, case_fn) in enumerate(CASES, 1):
        try:
            expected, question, check_fns = case_fn()

            start = time.time()
            response = client.ask(question, agent_name="contabilidad")
            elapsed = time.time() - start
            bot_text = response.get("message", "")
            agent_used = response.get("agent_used")
            numbers = extract_numbers(bot_text)

            checks = [fn(numbers, bot_text) for fn in check_fns]
            report = CompareReport(test_name=name, checks=checks, bot_response=bot_text)

            verdict = classify_error(
                expected=expected,
                bot_response_text=bot_text,
                bot_agent_used=agent_used,
                bot_numbers=numbers,
                checks=checks,
                expected_agent="contabilidad",
            )

            icon = f"{Colors.GREEN}✅{Colors.RESET}" if report.passed else f"{Colors.RED}❌{Colors.RESET}"
            pct = int(report.pass_rate * 100)
            print(f"\n[{i}/{len(CASES)}] {icon} {Colors.BOLD}{name}{Colors.RESET} — {pct}% ({elapsed:.1f}s)")
            print(f"   Q: {question}")

            for check in checks:
                status = f"{Colors.GREEN}OK{Colors.RESET}" if check.passed else f"{Colors.RED}FAIL{Colors.RESET}"
                exp = check.expected
                got = check.closest_found if check.closest_found is not None else "—"
                print(f"      {status}  {check.label}: esperado={exp}, encontrado={got}  [{check.note}]")

            if not report.passed:
                print(f"   {Colors.RED}[{verdict.category}]{Colors.RESET} {verdict.explanation}")
                if verdict.suggested_fix:
                    print(f"   {Colors.CYAN}→ Fix:{Colors.RESET} {verdict.suggested_fix}")
                preview = bot_text[:300].replace("\n", " ")
                print(f"   {Colors.YELLOW}Bot dijo:{Colors.RESET} {preview}...")

            if report.passed:
                total_passed += 1
            total_checks_passed += sum(1 for c in checks if c.passed)
            total_checks += len(checks)

        except Exception as exc:
            print(f"\n[{i}/{len(CASES)}] {Colors.RED}ERROR{Colors.RESET} {name}: {exc}")

    print(f"\n{Colors.BOLD}{'=' * 70}")
    print(f"  RESUMEN CONTABILIDAD")
    print(f"  Casos:  {total_passed}/{len(CASES)} pasados")
    print(f"  Checks: {total_checks_passed}/{total_checks} pasados "
          f"({100*total_checks_passed//max(total_checks,1)}%)")
    print(f"{'=' * 70}{Colors.RESET}\n")

    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"/tmp/qa_contabilidad_{ts}.md"
        with open(report_path, "w") as f:
            f.write(f"# QA Contabilidad vs iDempiere — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"Casos: {total_passed}/{len(CASES)} | Checks: {total_checks_passed}/{total_checks}\n")
        print(f"  Reporte: {report_path}")
    except Exception:
        pass

    sys.exit(0 if total_passed == len(CASES) else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Runner de QA para el agente RRHH — compara bot vs iDempiere.

Uso:
    docker compose exec backend python -m tests.qa_rrhh.runner \
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
    employee_count_total,
    employee_count_by_org,
    birthday_list_month,
    payroll_month,
)


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


# ── Test Cases ───────────────────────────────────────────────────────────

def case_employee_total():
    """Caso 1: total de empleados activos."""
    expected = employee_count_total()
    return expected, "¿Cuántos empleados activos hay?", [
        lambda nums, text: check_count("Total empleados", expected["total"], nums),
    ]


def case_employee_by_org():
    """Caso 2: empleados por organización — top 3 orgs por nombre."""
    expected = employee_count_by_org()
    top3 = expected["by_org"][:3]
    return expected, "Empleados por departamento y organización", [
        lambda nums, text: check_name_present(
            f"Org: {org['organizacion'][:20]}",
            org["organizacion"].split()[0],
            text,
        )
        for org in top3
    ]


def case_birthdays():
    """Caso 3: cumpleañeros del mes actual."""
    now = datetime.now()
    expected = birthday_list_month(mes=now.month)
    return expected, f"Cumpleañeros de este mes", [
        lambda nums, text: check_count("Total cumpleañeros", expected["total"], nums),
    ] + [
        (lambda name: lambda nums, text: check_name_present(
            f"Nombre: {name[:20]}",
            " ".join(name.split()[:2]),
            text,
        ))(n)
        for n in expected["names"][:3]
    ]


def case_payroll():
    """Caso 4: nómina del mes anterior."""
    now = datetime.now()
    if now.month == 1:
        mes, anio = 12, now.year - 1
    else:
        mes, anio = now.month - 1, now.year
    expected = payroll_month(mes=mes, anio=anio)
    return expected, f"Resumen de nómina de {['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'][mes]} {anio}", [
        lambda nums, text: check_amount(
            "Devengado", expected["total_devengado"], nums, rel_tol=0.06
        ),
    ]


CASES = [
    ("Empleados activos total", case_employee_total),
    ("Empleados por organización", case_employee_by_org),
    ("Cumpleañeros del mes", case_birthdays),
    ("Nómina mes anterior", case_payroll),
]


# ── Runner ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QA RRHH vs iDempiere")
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
    print(f"  QA RRHH vs iDempiere")
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
            response = client.ask(question, agent_name="rrhh")
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
                expected_agent="rrhh",
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

    # Resumen
    print(f"\n{Colors.BOLD}{'=' * 70}")
    print(f"  RESUMEN RRHH")
    print(f"  Casos:  {total_passed}/{len(CASES)} pasados")
    print(f"  Checks: {total_checks_passed}/{total_checks} pasados "
          f"({100*total_checks_passed//max(total_checks,1)}%)")
    print(f"{'=' * 70}{Colors.RESET}\n")

    # Guardar reporte
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"/tmp/qa_rrhh_{ts}.md"
        with open(report_path, "w") as f:
            f.write(f"# QA RRHH vs iDempiere — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(f"Casos: {total_passed}/{len(CASES)} | Checks: {total_checks_passed}/{total_checks}\n")
        print(f"  Reporte: {report_path}")
    except Exception:
        pass

    sys.exit(0 if total_passed == len(CASES) else 1)


if __name__ == "__main__":
    main()

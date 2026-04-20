#!/usr/bin/env python3
"""
Test script for SantoniBot agent queries.

Tests specific questions that have failed in production to verify they
return real data and don't hallucinate or say "no tengo acceso".

Usage:
    # Run against local backend (docker):
    docker compose exec backend python scripts/test_agent_queries.py

    # Run against production:
    docker compose exec backend python scripts/test_agent_queries.py --base-url http://localhost:8000

    # Run a specific agent only:
    docker compose exec backend python scripts/test_agent_queries.py --agent rrhh
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field

import requests

# ---------------------------------------------------------------------------
# Test cases: each is a question that MUST return data (not hallucinate)
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    agent: str
    question: str
    description: str
    expect_data_keywords: list[str] = field(default_factory=list)
    # Phrases that should NOT appear in the response
    forbidden_phrases: list[str] = field(default_factory=lambda: [
        "no tengo acceso",
        "no puedo acceder",
        "no dispongo",
        "no tengo acceso directo",
        "no cuento con acceso",
        "no tengo la capacidad",
        "no puedo consultar",
        "mis capacidades están limitadas",
    ])
    follow_up: str | None = None  # Optional follow-up question


TEST_CASES = [
    # ---- RRHH ----
    TestCase(
        agent="rrhh",
        question="¿Cuántos empleados hay por departamento?",
        description="Employee summary by department",
        expect_data_keywords=["empleado", "departamento"],
    ),
    TestCase(
        agent="rrhh",
        question="Cumpleañeros del mes de marzo",
        description="Birthday list for March",
        expect_data_keywords=["cumpleaño"],
    ),
    TestCase(
        agent="rrhh",
        question="Cumpleañeros de mayo",
        description="Birthday list for May (follow-up style)",
        expect_data_keywords=["cumpleaño", "mayo"],
    ),
    TestCase(
        agent="rrhh",
        question="Control de vacaciones de enero 2026",
        description="Vacation summary for Jan 2026",
        expect_data_keywords=["vacacion"],
    ),
    TestCase(
        agent="rrhh",
        question="Resumen de nómina de febrero 2026",
        description="Payroll summary for Feb 2026",
        expect_data_keywords=["nómina", "nomina"],
    ),
    TestCase(
        agent="rrhh",
        question="¿Cuántos obreros integrales hay?",
        description="Search employees by job title 'obrero integral'",
        expect_data_keywords=["obrero"],
    ),
    TestCase(
        agent="rrhh",
        question="Indicadores de ausentismo de febrero 2026",
        description="Attendance/absenteeism indicators",
        expect_data_keywords=["ausentismo", "ausencia"],
    ),

    # ---- FINANZAS ----
    TestCase(
        agent="finanzas",
        question="¿Cuál es el saldo de bancos hoy?",
        description="Current bank balances",
        expect_data_keywords=["banco", "saldo"],
    ),
    TestCase(
        agent="finanzas",
        question="¿Cuánto es la cuenta por pagar?",
        description="Accounts payable summary",
        expect_data_keywords=["pagar", "factura"],
    ),
    TestCase(
        agent="finanzas",
        question="Cuentas por cobrar vencidas",
        description="Overdue receivables",
        expect_data_keywords=["cobrar", "vencid"],
    ),

    # ---- VENTAS ----
    TestCase(
        agent="ventas",
        question="¿Cuáles son los top 20 clientes por ventas?",
        description="Top 20 clients by sales",
        expect_data_keywords=["cliente", "venta"],
    ),
    TestCase(
        agent="ventas",
        question="Resumen de ventas de febrero 2026",
        description="Sales summary for Feb 2026",
        expect_data_keywords=["venta", "febrero"],
    ),
    TestCase(
        agent="ventas",
        question="¿Cuánto se ha cobrado esta semana?",
        description="Collections this week",
        expect_data_keywords=["cobr"],
    ),

    # ---- COMPRAS PRODUCTORES ----
    TestCase(
        agent="compras_productores",
        question="¿Cuánto es la compra de arroz paddy este año?",
        description="Rice purchases this year",
        expect_data_keywords=["arroz", "compra"],
    ),
    TestCase(
        agent="compras_productores",
        question="Compras de maíz acondicionado de InproMaiz",
        description="Corn purchases for InproMaiz org (accent test)",
        expect_data_keywords=["maíz", "maiz", "compra"],
    ),
    TestCase(
        agent="compras_productores",
        question="Top productores por volumen",
        description="Top producers by volume",
        expect_data_keywords=["productor", "volumen"],
    ),

    # ---- COMPRAS INSUMOS ----
    TestCase(
        agent="compras_insumos",
        question="¿Cuánto se compró de insumos este mes?",
        description="Insumos purchases this month",
        expect_data_keywords=["compra", "insumo"],
    ),
    TestCase(
        agent="compras_insumos",
        question="Órdenes de compra pendientes",
        description="Pending purchase orders",
        expect_data_keywords=["orden", "pendiente"],
    ),

    # ---- CONTABILIDAD ----
    TestCase(
        agent="contabilidad",
        question="Muéstrame el balance general actualizado",
        description="General balance / accounting summary",
        expect_data_keywords=["balance", "cuenta"],
    ),

    # ---- PRODUCCION ----
    TestCase(
        agent="produccion",
        question="¿Cuál es la producción de hoy?",
        description="Today's production",
        expect_data_keywords=["producción", "produccion"],
    ),
    TestCase(
        agent="produccion",
        question="Inventario actual en almacén",
        description="Current inventory stock",
        expect_data_keywords=["inventario", "stock", "almacén", "almacen"],
    ),
]


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def login(base_url: str, username: str, password: str) -> str:
    """Login and return JWT token."""
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"]


def send_message(
    base_url: str, token: str, message: str, agent_name: str,
    conversation_id: int | None = None,
) -> dict:
    """Send a chat message and return the response."""
    resp = requests.post(
        f"{base_url}/api/chat/",
        json={
            "message": message,
            "conversation_id": conversation_id,
            "agent_name": agent_name,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def check_response(response_text: str, tc: TestCase) -> tuple[bool, list[str]]:
    """Check if response passes validation. Returns (passed, issues)."""
    issues = []
    text_lower = response_text.lower()

    # Check forbidden phrases
    for phrase in tc.forbidden_phrases:
        if phrase in text_lower:
            issues.append(f"FORBIDDEN: Contains '{phrase}'")

    # Check expected keywords (at least one must appear)
    if tc.expect_data_keywords:
        found = any(kw.lower() in text_lower for kw in tc.expect_data_keywords)
        if not found:
            issues.append(
                f"MISSING: None of expected keywords found: {tc.expect_data_keywords}"
            )

    # Check for signs of empty/no-data responses
    no_data_phrases = [
        "no se encontraron datos",
        "no hay datos disponibles",
        "no se pudo obtener",
        "error al consultar",
    ]
    for phrase in no_data_phrases:
        if phrase in text_lower:
            issues.append(f"NO_DATA: Response says '{phrase}'")

    passed = len(issues) == 0
    return passed, issues


def run_tests(
    base_url: str, token: str,
    agent_filter: str | None = None,
    verbose: bool = False,
):
    """Run all test cases and report results."""
    cases = TEST_CASES
    if agent_filter:
        cases = [tc for tc in cases if tc.agent == agent_filter]

    if not cases:
        print(f"{Colors.RED}No test cases found for agent: {agent_filter}{Colors.RESET}")
        return

    print(f"\n{Colors.BOLD}{'='*70}")
    print(f"  SantoniBot Agent Query Tests")
    print(f"  Base URL: {base_url}")
    print(f"  Test cases: {len(cases)}")
    print(f"{'='*70}{Colors.RESET}\n")

    passed = 0
    failed = 0
    errors = 0
    results = []

    for i, tc in enumerate(cases, 1):
        print(f"  [{i}/{len(cases)}] {Colors.CYAN}[{tc.agent}]{Colors.RESET} {tc.description}")
        print(f"         Q: {tc.question}")

        try:
            start = time.time()
            response = send_message(base_url, token, tc.question, tc.agent)
            elapsed = time.time() - start
            response_text = response.get("message", "")
            agent_used = response.get("agent_used", "?")

            ok, issues = check_response(response_text, tc)

            if ok:
                passed += 1
                status = f"{Colors.GREEN}PASS{Colors.RESET}"
            else:
                failed += 1
                status = f"{Colors.RED}FAIL{Colors.RESET}"

            print(f"         {status} ({elapsed:.1f}s, agent={agent_used})")

            if issues:
                for issue in issues:
                    print(f"         {Colors.RED}  ! {issue}{Colors.RESET}")

            if verbose or not ok:
                # Show first 200 chars of response
                preview = response_text[:200].replace("\n", " ")
                print(f"         Response: {preview}...")

            results.append({
                "agent": tc.agent,
                "question": tc.question,
                "description": tc.description,
                "passed": ok,
                "issues": issues,
                "elapsed": elapsed,
                "response_length": len(response_text),
            })

        except Exception as exc:
            errors += 1
            print(f"         {Colors.RED}ERROR: {exc}{Colors.RESET}")
            results.append({
                "agent": tc.agent,
                "question": tc.question,
                "description": tc.description,
                "passed": False,
                "issues": [f"EXCEPTION: {exc}"],
                "elapsed": 0,
                "response_length": 0,
            })

        print()

    # Summary
    total = passed + failed + errors
    print(f"\n{Colors.BOLD}{'='*70}")
    print(f"  RESULTS: {passed}/{total} passed")
    if failed:
        print(f"  {Colors.RED}  Failed: {failed}{Colors.RESET}")
    if errors:
        print(f"  {Colors.RED}  Errors: {errors}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

    # Save JSON results
    results_file = "test_agent_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  Results saved to {results_file}")

    # Return exit code
    return 0 if (failed == 0 and errors == 0) else 1


def main():
    parser = argparse.ArgumentParser(description="Test SantoniBot agent queries")
    parser.add_argument(
        "--base-url", default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument("--username", default=None, help="Login username")
    parser.add_argument("--password", default=None, help="Login password")
    parser.add_argument("--agent", default=None, help="Test only this agent")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show response previews for all tests")
    args = parser.parse_args()

    # Get credentials
    username = args.username or os.getenv("TEST_USERNAME", "admin")
    password = args.password or os.getenv("TEST_PASSWORD", "admin123")

    print(f"\n  Logging in as {username}...")
    try:
        token = login(args.base_url, username, password)
        print(f"  {Colors.GREEN}Login successful{Colors.RESET}")
    except Exception as exc:
        print(f"  {Colors.RED}Login failed: {exc}{Colors.RESET}")
        print(f"  Set TEST_USERNAME and TEST_PASSWORD env vars or use --username/--password")
        sys.exit(1)

    exit_code = run_tests(
        args.base_url, token,
        agent_filter=args.agent,
        verbose=args.verbose,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

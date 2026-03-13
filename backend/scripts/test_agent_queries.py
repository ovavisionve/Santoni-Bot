#!/usr/bin/env python3
"""
Test de preguntas contra los agentes del bot.
Ejecuta preguntas reales y verifica que las respuestas contengan datos esperados
y NO contengan frases prohibidas (alucinaciones).

Uso:
    docker compose exec backend python scripts/test_agent_queries.py --username admin --password 'TU_PASSWORD' -v
    docker compose exec backend python scripts/test_agent_queries.py --agent rrhh --username admin --password 'TU_PASSWORD' -v
"""

import argparse
import json
import os
import sys
import time
import requests

DEFAULT_BASE_URL = "http://localhost:8000"

# Frases que NUNCA deberían aparecer en una respuesta
FORBIDDEN_PHRASES = [
    "no tengo acceso",
    "no puedo acceder",
    "no dispongo",
    "no tengo acceso directo",
    "no puedo consultar",
    "no cuento con acceso",
]

# Casos de prueba: (agent_name, description, question, expected_keywords, allow_no_data)
TEST_CASES = [
    # RRHH
    ("rrhh", "Employee summary by department",
     "¿Cuántos empleados hay por departamento?",
     ["departamento", "empleado"], False),

    ("rrhh", "Birthday list for March",
     "Cumpleañeros del mes de marzo",
     ["marzo", "cumpleañ"], False),

    ("rrhh", "Birthday list for May (follow-up style)",
     "Cumpleañeros de mayo",
     ["mayo", "cumpleañ"], False),

    ("rrhh", "Vacation summary for Jan 2026",
     "Control de vacaciones de enero 2026",
     ["vacacion", "enero"], False),

    ("rrhh", "Payroll summary for Feb 2026",
     "Resumen de nómina de febrero 2026",
     ["nómina", "febrero", "nomina"], False),

    ("rrhh", "Search employees by job title 'obrero integral'",
     "¿Cuántos obreros integrales hay?",
     ["obrero", "integral"], False),

    ("rrhh", "Attendance/absenteeism indicators",
     "Indicadores de ausentismo de febrero 2026",
     ["ausentismo", "ausencia", "febrero"], False),

    # Finanzas
    ("finanzas", "Current bank balances",
     "¿Cuál es el saldo de bancos hoy?",
     ["banco", "saldo"], False),

    ("finanzas", "Accounts payable summary",
     "¿Cuánto es la cuenta por pagar?",
     ["pagar", "factura"], False),

    ("finanzas", "Overdue receivables",
     "Cuentas por cobrar vencidas",
     ["cobrar", "vencid"], False),

    # Ventas
    ("ventas", "Top 20 clients by sales",
     "¿Cuáles son los top 20 clientes por ventas?",
     ["cliente", "venta"], False),

    ("ventas", "Sales summary for Feb 2026",
     "Resumen de ventas de febrero 2026",
     ["venta", "febrero"], False),

    ("ventas", "Collections this week",
     "¿Cuánto se ha cobrado esta semana?",
     ["cobr"], False),

    # Compras Productores
    ("compras_productores", "Rice purchases this year",
     "¿Cuánto es la compra de arroz paddy este año?",
     ["arroz", "paddy"], False),

    ("compras_productores", "Corn purchases for InproMaiz org (accent test)",
     "Compras de maíz acondicionado de InproMaiz",
     ["maíz", "maiz", "inpromaiz"], False),

    ("compras_productores", "Top producers by volume",
     "Top productores por volumen",
     ["productor", "volumen", "kg"], False),

    # Compras Insumos
    ("compras_insumos", "Insumos purchases this month",
     "¿Cuánto se compró de insumos este mes?",
     ["compra", "insumo", "proveedor"], False),

    ("compras_insumos", "Pending purchase orders",
     "Órdenes de compra pendientes",
     ["orden", "pendiente"], False),

    # Contabilidad
    ("contabilidad", "General balance / accounting summary",
     "Muéstrame el balance general actualizado",
     ["balance", "activo", "pasivo"], False),

    # Producción
    ("produccion", "Today's production",
     "¿Cuál es la producción de hoy?",
     ["movimiento", "recepci", "despacho"], True),

    ("produccion", "Current inventory stock",
     "Inventario actual en almacén",
     ["inventario", "stock", "producto"], False),
]


def login(base_url: str, username: str, password: str) -> str:
    """Login and return JWT token."""
    resp = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["access_token"]


def send_query(base_url: str, token: str, message: str, agent_name: str | None = None) -> dict:
    """Send a chat query and return the response."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"message": message}
    if agent_name:
        body["agent_name"] = agent_name

    resp = requests.post(
        f"{base_url}/api/chat/",
        headers=headers,
        json=body,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def check_response(response_text: str, expected_keywords: list[str], allow_no_data: bool) -> tuple[bool, str]:
    """Check if response is valid. Returns (passed, reason)."""
    resp_lower = response_text.lower()

    # Check forbidden phrases
    for phrase in FORBIDDEN_PHRASES:
        if phrase in resp_lower:
            return False, f"FORBIDDEN: '{phrase}'"

    # Check for "no se encontraron datos" (allowed in some cases)
    if not allow_no_data and "no se encontraron datos" in resp_lower:
        return False, "NO_DATA: Response says 'no se encontraron datos'"

    # Check expected keywords (at least one must match)
    found = any(kw.lower() in resp_lower for kw in expected_keywords)
    if not found:
        return False, f"MISSING: None of expected keywords found: {expected_keywords}"

    return True, "OK"


def run_tests(
    base_url: str, token: str, agent_filter: str | None, verbose: bool,
) -> int:
    """Run all test cases. Returns exit code (0=all pass, 1=some fail)."""
    cases = TEST_CASES
    if agent_filter:
        cases = [c for c in cases if c[0] == agent_filter]

    if not cases:
        print(f"No test cases for agent '{agent_filter}'")
        return 1

    print("=" * 70)
    print(f"  SantoniBot Agent Query Tests")
    print(f"  Base URL: {base_url}")
    print(f"  Test cases: {len(cases)}")
    print("=" * 70)

    passed = 0
    failed = 0
    results = []

    for i, (agent, desc, question, keywords, allow_no_data) in enumerate(cases, 1):
        print(f"\n[{i}/{len(cases)}] [{agent}] {desc}")
        print(f"  Q: {question}")

        t0 = time.time()
        try:
            resp = send_query(base_url, token, question, agent_name=agent)
            elapsed = time.time() - t0
            response_text = resp.get("message", "")
            agent_used = resp.get("agent_used", "")

            ok, reason = check_response(response_text, keywords, allow_no_data)

            result = {
                "agent": agent,
                "description": desc,
                "question": question,
                "agent_used": agent_used,
                "passed": ok,
                "reason": reason,
                "elapsed_s": round(elapsed, 1),
                "response_preview": response_text[:200],
            }
            results.append(result)

            if ok:
                passed += 1
                print(f"  PASS ({elapsed:.1f}s, agent={agent_used})")
            else:
                failed += 1
                print(f"  FAIL ({elapsed:.1f}s, agent={agent_used})")
                print(f"  ! {reason}")

            if verbose:
                print(f"  Response: {response_text[:300]}...")

        except Exception as exc:
            elapsed = time.time() - t0
            failed += 1
            print(f"  ERROR ({elapsed:.1f}s): {exc}")
            results.append({
                "agent": agent,
                "description": desc,
                "question": question,
                "passed": False,
                "reason": f"ERROR: {exc}",
                "elapsed_s": round(elapsed, 1),
            })

    print(f"\n{'=' * 70}")
    print(f"  RESULTS: {passed}/{len(cases)} passed")
    if failed:
        print(f"  Failed: {failed}")
    print(f"{'=' * 70}")

    # Save results to JSON
    try:
        results_file = "/tmp/test_agent_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n  Results saved to {results_file}")
    except Exception:
        pass

    return 0 if failed == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Test SantoniBot agent queries")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--username", default=os.environ.get("TEST_USERNAME", "admin"))
    parser.add_argument("--password", default=os.environ.get("TEST_PASSWORD"))
    parser.add_argument("--agent", default=None, help="Filter by agent name")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if not args.password:
        print("ERROR: Se requiere --password o variable TEST_PASSWORD")
        sys.exit(1)

    print("Autenticando...")
    try:
        token = login(args.base_url, args.username, args.password)
    except Exception as exc:
        print(f"Error de login: {exc}")
        sys.exit(1)

    exit_code = run_tests(args.base_url, token, args.agent, args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

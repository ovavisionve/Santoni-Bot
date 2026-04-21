#!/usr/bin/env python3
"""
Runner masivo de QA — corre escenarios del training_dataset.json contra el bot.

Para cada escenario:
  1. Envía la pregunta al agente esperado
  2. Verifica que el bot respondió con datos (no error, no "no tengo acceso")
  3. Verifica que el agente correcto manejó la pregunta
  4. Clasifica el resultado en categorías macro

Uso:
    # Los 3 agentes prioritarios (ventas, rrhh, contabilidad):
    docker compose exec backend python -m tests.qa_mass.runner \
        --base-url http://localhost:8000 \
        --username admin --password 'SantoniAdmin2026!' \
        --agents ventas,rrhh,contabilidad

    # Todos los agentes:
    docker compose exec backend python -m tests.qa_mass.runner \
        --base-url http://localhost:8000 \
        --username admin --password 'SantoniAdmin2026!'

    # Limitar a N casos:
    docker compose exec backend python -m tests.qa_mass.runner \
        --base-url http://localhost:8000 \
        --username admin --password 'SantoniAdmin2026!' \
        --limit 50
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tests.qa_ventas.bot_client import BotClient


# ── Error phrases ────────────────────────────────────────────────────────

_CAUGHT_EXCEPTION_PHRASES = [
    "dificultades para acceder",
    "dificultades para conectarme",
    "dificultades para consultar",
    "problema de conexión",
    "error de conexión",
    "se produjo un error",
    "inténtalo de nuevo en unos minutos",
    "inténtalo de nuevo en unos momentos",
]

_ACCESS_DENIED_PHRASES = [
    "no tengo acceso",
    "no puedo acceder",
    "no dispongo",
    "no tengo la capacidad",
    "no cuento con acceso",
    "no puedo consultar",
]

_NO_DATA_PHRASES = [
    "no se encontraron datos",
    "no hay datos disponibles",
    "no se pudo obtener",
    "no hay registros",
]


@dataclass
class CaseResult:
    case_id: int
    question: str
    expected_agent: str
    agent_used: str
    category: str  # pass, agent_error, access_denied, no_data, short_response, agent_mismatch
    elapsed: float
    response_length: int
    note: str = ""


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def classify_response(
    bot_text: str,
    agent_used: str | None,
    expected_agent: str,
) -> tuple[str, str]:
    """Clasifica la respuesta. Retorna (category, note)."""
    text_lower = bot_text.lower()

    # 1. Agent caught exception
    for phrase in _CAUGHT_EXCEPTION_PHRASES:
        if phrase in text_lower:
            return "agent_error", f"Bot dijo: '{phrase}'"

    # 2. Access denied
    for phrase in _ACCESS_DENIED_PHRASES:
        if phrase in text_lower:
            return "access_denied", f"Bot dijo: '{phrase}'"

    # 3. No data
    for phrase in _NO_DATA_PHRASES:
        if phrase in text_lower:
            return "no_data", f"Bot dijo: '{phrase}'"

    # 4. Short response (probable error interno)
    if len(bot_text.strip()) < 50:
        return "short_response", f"Solo {len(bot_text)} chars"

    # 5. Agent mismatch
    if agent_used and agent_used != expected_agent and agent_used != "orchestrator":
        return "agent_mismatch", f"Esperaba '{expected_agent}', fue '{agent_used}'"

    # 6. Pass — response has content
    return "pass", ""


def load_cases(
    dataset_path: str,
    agents: list[str] | None = None,
    include_followups: bool = False,
    limit: int | None = None,
) -> list[dict]:
    """Carga casos del dataset filtrando por agente y tipo."""
    with open(dataset_path) as f:
        data = json.load(f)

    entries = data.get("entries", data if isinstance(data, list) else [])

    # Filter
    cases = []
    for e in entries:
        agent = e.get("agente_esperado")
        if not agent:
            continue
        if agents and agent not in agents:
            continue
        if not include_followups and e.get("es_followup"):
            continue
        cases.append(e)

    if limit:
        cases = cases[:limit]
    return cases


def run_mass_test(
    client: BotClient,
    cases: list[dict],
    verbose: bool = False,
) -> list[CaseResult]:
    """Corre todos los casos y retorna resultados."""
    results: list[CaseResult] = []
    total = len(cases)

    for i, case in enumerate(cases, 1):
        question = case["pregunta"]
        expected_agent = case["agente_esperado"]
        case_id = case.get("id", i)

        try:
            start = time.time()
            response = client.ask(question, agent_name=expected_agent)
            elapsed = time.time() - start

            bot_text = response.get("message", "")
            agent_used = response.get("agent_used", "")

            category, note = classify_response(bot_text, agent_used, expected_agent)

            result = CaseResult(
                case_id=case_id,
                question=question,
                expected_agent=expected_agent,
                agent_used=agent_used or "?",
                category=category,
                elapsed=elapsed,
                response_length=len(bot_text),
                note=note,
            )

        except Exception as exc:
            result = CaseResult(
                case_id=case_id,
                question=question,
                expected_agent=expected_agent,
                agent_used="ERROR",
                category="exception",
                elapsed=0,
                response_length=0,
                note=str(exc)[:200],
            )

        results.append(result)

        # Print progress
        icon = f"{Colors.GREEN}.{Colors.RESET}" if result.category == "pass" else f"{Colors.RED}X{Colors.RESET}"
        if verbose and result.category != "pass":
            print(f"\n  [{i}/{total}] {icon} #{case_id} [{expected_agent}] {question[:60]}")
            print(f"         {Colors.RED}[{result.category}]{Colors.RESET} {result.note}")
        else:
            print(icon, end="", flush=True)
            if i % 50 == 0:
                print(f" [{i}/{total}]")

    print()
    return results


def print_summary(results: list[CaseResult], agents_filter: list[str] | None):
    """Imprime resumen por agente y categoría."""
    total = len(results)
    passed = sum(1 for r in results if r.category == "pass")
    by_category = Counter(r.category for r in results)
    by_agent = Counter(r.expected_agent for r in results)

    print(f"\n{Colors.BOLD}{'=' * 70}")
    print(f"  QA MASIVO — RESUMEN")
    print(f"{'=' * 70}{Colors.RESET}")
    print(f"  Total: {passed}/{total} pasados ({100*passed//max(total,1)}%)")
    print(f"  Tiempo total: {sum(r.elapsed for r in results):.1f}s "
          f"(promedio: {sum(r.elapsed for r in results)/max(total,1):.1f}s/caso)")

    # By category
    print(f"\n  {Colors.BOLD}Por categoría:{Colors.RESET}")
    for cat, count in by_category.most_common():
        color = Colors.GREEN if cat == "pass" else Colors.RED
        pct = 100 * count // total
        bar = "█" * (pct // 2) + "░" * (50 - pct // 2)
        print(f"    {color}{cat:20s}{Colors.RESET} {count:4d} ({pct:3d}%) {bar}")

    # By agent
    print(f"\n  {Colors.BOLD}Por agente:{Colors.RESET}")
    for agent in sorted(by_agent.keys()):
        agent_results = [r for r in results if r.expected_agent == agent]
        agent_passed = sum(1 for r in agent_results if r.category == "pass")
        agent_total = len(agent_results)
        pct = 100 * agent_passed // max(agent_total, 1)
        color = Colors.GREEN if pct >= 80 else Colors.YELLOW if pct >= 60 else Colors.RED
        print(f"    {color}{agent:25s}{Colors.RESET} {agent_passed}/{agent_total} ({pct}%)")

    # List failures
    failures = [r for r in results if r.category != "pass"]
    if failures:
        print(f"\n  {Colors.BOLD}Fallos detallados ({len(failures)}):{Colors.RESET}")
        for r in failures:
            print(f"    {Colors.RED}#{r.case_id:3d}{Colors.RESET} [{r.expected_agent}] "
                  f"{Colors.DIM}{r.question[:55]}{Colors.RESET}")
            print(f"         [{r.category}] {r.note}")


def save_report(results: list[CaseResult], report_dir: str) -> str | None:
    """Guarda reporte markdown. Retorna path o None."""
    try:
        os.makedirs(report_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(report_dir, f"qa_mass_{ts}.md")

        total = len(results)
        passed = sum(1 for r in results if r.category == "pass")
        by_category = Counter(r.category for r in results)
        by_agent = Counter(r.expected_agent for r in results)

        lines = [
            f"# QA Masivo — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"**Total:** {passed}/{total} pasados ({100*passed//max(total,1)}%)",
            f"**Tiempo:** {sum(r.elapsed for r in results):.1f}s total",
            "",
            "## Por categoría",
            "",
            "| Categoría | Casos | % |",
            "|-----------|-------|---|",
        ]
        for cat, count in by_category.most_common():
            lines.append(f"| `{cat}` | {count} | {100*count//total}% |")

        lines.extend(["", "## Por agente", "", "| Agente | Pasados | Total | % |", "|--------|---------|-------|---|"])
        for agent in sorted(by_agent.keys()):
            ar = [r for r in results if r.expected_agent == agent]
            ap = sum(1 for r in ar if r.category == "pass")
            lines.append(f"| {agent} | {ap} | {len(ar)} | {100*ap//max(len(ar),1)}% |")

        failures = [r for r in results if r.category != "pass"]
        if failures:
            lines.extend(["", "## Fallos", "", "| # | Agente | Pregunta | Categoría | Nota |", "|---|--------|----------|-----------|------|"])
            for r in failures:
                q = r.question[:80].replace("|", "\\|")
                lines.append(f"| {r.case_id} | {r.expected_agent} | {q} | `{r.category}` | {r.note[:60]} |")

        with open(path, "w") as f:
            f.write("\n".join(lines))
        return path
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="QA Masivo desde training_dataset.json")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--username", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--agents", default=None,
                        help="Agentes a probar (comma-separated). Default: todos.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limitar a N casos")
    parser.add_argument("--include-followups", action="store_true",
                        help="Incluir follow-ups (requieren contexto de historial)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--dataset", default="/app/data/training_dataset.json")
    args = parser.parse_args()

    username = args.username or os.getenv("TEST_USERNAME", "admin")
    password = args.password or os.getenv("TEST_PASSWORD", "")
    if not password:
        print(f"{Colors.RED}Falta --password{Colors.RESET}")
        sys.exit(1)

    agents_filter = args.agents.split(",") if args.agents else None

    # Load cases
    cases = load_cases(
        args.dataset,
        agents=agents_filter,
        include_followups=args.include_followups,
        limit=args.limit,
    )

    if not cases:
        print(f"{Colors.RED}No se encontraron casos para los filtros dados.{Colors.RESET}")
        sys.exit(1)

    agent_str = ", ".join(agents_filter) if agents_filter else "todos"
    print(f"\n{Colors.BOLD}{'=' * 70}")
    print(f"  QA MASIVO — {len(cases)} escenarios")
    print(f"  Agentes: {agent_str}")
    print(f"  Base URL: {args.base_url}")
    print(f"{'=' * 70}{Colors.RESET}\n")

    # Login
    client = BotClient(args.base_url, username, password, timeout=120)
    try:
        client.login()
        print(f"  {Colors.GREEN}Login OK{Colors.RESET}\n")
    except Exception as exc:
        print(f"  {Colors.RED}Login failed: {exc}{Colors.RESET}")
        sys.exit(1)

    # Run
    results = run_mass_test(client, cases, verbose=args.verbose)

    # Summary
    print_summary(results, agents_filter)

    # Save report
    path = save_report(results, "/tmp")
    if path:
        print(f"\n  {Colors.CYAN}Reporte: {path}{Colors.RESET}")

    passed = sum(1 for r in results if r.category == "pass")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()

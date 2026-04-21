#!/usr/bin/env python3
"""
Runner de QA para el agente Ventas — compara bot vs iDempiere.

Uso:
    docker compose exec backend python -m tests.qa_ventas.runner \\
        --base-url http://localhost:8000 \\
        --username admin \\
        --password 'SantoniAdmin2026!'

Output:
  - Resumen por pantalla con ✅/❌ por caso y porcentaje total
  - Reporte markdown en /app/docs/qa_ventas_<timestamp>.md con detalle:
    pregunta, valores esperados (iDempiere), respuesta del bot, checks
    individuales con ± de diferencia para los fallos.
"""

import argparse
import os
import sys
import time
from datetime import datetime

from .bot_client import BotClient, extract_numbers
from .comparator import CompareReport
from .error_classifier import ErrorVerdict, classify_error
from .test_cases import CASES, TestCase


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def _fmt_val(v) -> str:
    """Formatea un valor numérico con separador de miles."""
    if isinstance(v, (int, float)):
        return f"{v:,.2f}"
    return str(v)


def run_case(
    client: BotClient, case: TestCase,
) -> tuple[CompareReport, dict, str, float, ErrorVerdict]:
    """Corre un caso. Retorna (report, expected, bot_text, elapsed, verdict)."""
    # 1. SQL esperado
    expected = case.fetch_expected()

    # 2. Pregunta al bot
    start = time.time()
    bot_response = client.ask(case.question, agent_name="ventas")
    elapsed = time.time() - start
    bot_text = bot_response.get("message", "")
    agent_used = bot_response.get("agent_used")

    # 3. Extraer números y chequear
    numbers = extract_numbers(bot_text)
    checks = case.build_checks(expected, numbers, bot_text)

    # 4. Clasificar el error macro
    verdict = classify_error(
        expected=expected,
        bot_response_text=bot_text,
        bot_agent_used=agent_used,
        bot_numbers=numbers,
        checks=checks,
        expected_agent="ventas",
    )

    report = CompareReport(test_name=case.name, checks=checks, bot_response=bot_text)
    return report, expected, bot_text, elapsed, verdict


def print_case_result(
    i: int, total: int, case: TestCase,
    report: CompareReport, elapsed: float, verdict: ErrorVerdict,
):
    """Imprime el resultado de un caso en stdout."""
    icon = f"{Colors.GREEN}✅{Colors.RESET}" if report.passed else f"{Colors.RED}❌{Colors.RESET}"
    pct = int(report.pass_rate * 100)
    print(f"\n[{i}/{total}] {icon} {Colors.BOLD}{case.name}{Colors.RESET} "
          f"— {pct}% ({elapsed:.1f}s)")
    print(f"   Q: {case.question}")
    for check in report.checks:
        status = f"{Colors.GREEN}OK{Colors.RESET}" if check.passed else f"{Colors.RED}FAIL{Colors.RESET}"
        exp = _fmt_val(check.expected)
        got = _fmt_val(check.closest_found) if check.closest_found is not None else "—"
        print(f"      {status}  {check.label}: esperado={exp}, más cercano={got}  [{check.note}]")

    # Veredicto macro del error
    if not report.passed:
        color = Colors.YELLOW if verdict.category == "pass" else Colors.RED
        print(f"   {color}[{verdict.category}]{Colors.RESET} {verdict.explanation}")
        if verdict.suggested_fix:
            print(f"   {Colors.CYAN}→ Fix sugerido:{Colors.RESET} {verdict.suggested_fix}")
        preview = report.bot_response[:300].replace("\n", " ")
        print(f"   {Colors.YELLOW}Bot dijo:{Colors.RESET} {preview}...")


def build_markdown(
    reports: list[tuple[TestCase, CompareReport, dict, str, float, ErrorVerdict]],
) -> str:
    """Genera el reporte markdown completo."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_cases = len(reports)
    passed_cases = sum(1 for _, r, _, _, _, _ in reports if r.passed)
    total_checks = sum(len(r.checks) for _, r, _, _, _, _ in reports)
    passed_checks = sum(sum(1 for c in r.checks if c.passed) for _, r, _, _, _, _ in reports)

    # Agrupar por categoría de error para el resumen
    by_category: dict[str, list[str]] = {}
    for case, _report, _expected, _bot_text, _elapsed, verdict in reports:
        by_category.setdefault(verdict.category, []).append(case.name)

    lines = [
        f"# QA Ventas vs iDempiere — {now}",
        "",
        f"**Casos:** {passed_cases}/{total_cases} pasados",
        f"**Checks individuales:** {passed_checks}/{total_checks} pasados ({100*passed_checks//max(total_checks,1)}%)",
        "",
        "## Resumen por categoría de error",
        "",
        "| Categoría | Casos afectados |",
        "|-----------|-----------------|",
    ]
    for category, cases in sorted(by_category.items()):
        cases_str = ", ".join(f"*{c}*" for c in cases)
        lines.append(f"| `{category}` | {cases_str} |")
    lines.extend(["", "---", ""])

    for case, report, expected, bot_text, elapsed, verdict in reports:
        status = "✅ PASS" if report.passed else "❌ FAIL"
        pct = int(report.pass_rate * 100)
        lines.extend([
            f"## {status} — {case.name} ({pct}%)",
            "",
            f"**Pregunta:** `{case.question}`",
            "",
            f"**Tiempo:** {elapsed:.1f}s",
            "",
            f"**Veredicto:** `{verdict.category}` — {verdict.explanation}",
            "",
        ])
        if verdict.suggested_fix:
            lines.extend([f"**Fix sugerido:** {verdict.suggested_fix}", ""])
        lines.extend([
            "### Valores esperados (iDempiere)",
            "",
            "```",
        ])
        # Dump expected values
        for key, val in expected.items():
            if key == "label":
                continue
            if isinstance(val, dict):
                lines.append(f"{key}:")
                for k2, v2 in val.items():
                    lines.append(f"  {k2}: {v2}")
            elif isinstance(val, list):
                lines.append(f"{key}:")
                for item in val[:10]:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {val}")
        lines.extend(["```", "", "### Checks", "", "| Label | Esperado | Encontrado | Estado | Nota |",
                      "|-------|----------|------------|--------|------|"])
        for check in report.checks:
            icon = "✅" if check.passed else "❌"
            exp = _fmt_val(check.expected)
            found = _fmt_val(check.closest_found) if check.closest_found is not None else "—"
            lines.append(f"| {check.label} | {exp} | {found} | {icon} | {check.note} |")

        # Respuesta del bot (primeros 500 chars)
        preview = bot_text[:1500].replace("\n", "\n> ")
        lines.extend([
            "",
            "### Respuesta del bot (primeros 1500 caracteres)",
            "",
            f"> {preview}",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="QA Ventas vs iDempiere")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--username", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--report-dir", default="/tmp",
                        help="Directorio donde guardar el reporte markdown (default /tmp)")
    parser.add_argument("--case", type=int, default=None,
                        help="Correr solo el caso N (1-indexed)")
    args = parser.parse_args()

    username = args.username or os.getenv("TEST_USERNAME", "admin")
    password = args.password or os.getenv("TEST_PASSWORD", "")

    if not password:
        print(f"{Colors.RED}Falta --password (o env var TEST_PASSWORD){Colors.RESET}")
        sys.exit(1)

    print(f"\n{Colors.BOLD}{'=' * 70}")
    print(f"  QA Ventas vs iDempiere")
    print(f"  Base URL: {args.base_url}")
    print(f"  User: {username}")
    print(f"{'=' * 70}{Colors.RESET}\n")

    client = BotClient(args.base_url, username, password)
    try:
        client.login()
        print(f"  {Colors.GREEN}Login OK{Colors.RESET}")
    except Exception as exc:
        print(f"  {Colors.RED}Login failed: {exc}{Colors.RESET}")
        sys.exit(1)

    cases = CASES
    if args.case is not None:
        if args.case < 1 or args.case > len(CASES):
            print(f"{Colors.RED}--case debe estar entre 1 y {len(CASES)}{Colors.RESET}")
            sys.exit(1)
        cases = [CASES[args.case - 1]]

    all_reports: list[tuple[TestCase, CompareReport, dict, str, float, ErrorVerdict]] = []
    for i, case in enumerate(cases, 1):
        try:
            report, expected, bot_text, elapsed, verdict = run_case(client, case)
            print_case_result(i, len(cases), case, report, elapsed, verdict)
            all_reports.append((case, report, expected, bot_text, elapsed, verdict))
        except Exception as exc:
            print(f"\n[{i}/{len(cases)}] {Colors.RED}ERROR{Colors.RESET} {case.name}: {exc}")

    # Resumen
    total_cases = len(all_reports)
    passed_cases = sum(1 for _, r, _, _, _, _ in all_reports if r.passed)
    total_checks = sum(len(r.checks) for _, r, _, _, _, _ in all_reports)
    passed_checks = sum(sum(1 for c in r.checks if c.passed) for _, r, _, _, _, _ in all_reports)

    # Agrupar por categoría
    by_category: dict[str, int] = {}
    for _, _, _, _, _, v in all_reports:
        by_category[v.category] = by_category.get(v.category, 0) + 1

    print(f"\n{Colors.BOLD}{'=' * 70}")
    print(f"  RESUMEN")
    print(f"  Casos:  {passed_cases}/{total_cases} pasados")
    print(f"  Checks: {passed_checks}/{total_checks} pasados "
          f"({100*passed_checks//max(total_checks,1)}%)")
    print(f"\n  {Colors.BOLD}Categorías de error:{Colors.RESET}")
    for category, count in sorted(by_category.items(), key=lambda x: -x[1]):
        color = Colors.GREEN if category == "pass" else Colors.YELLOW
        print(f"    {color}{category}{Colors.RESET}: {count} caso(s)")
    print(f"{'=' * 70}{Colors.RESET}\n")

    # Guardar reporte markdown
    if all_reports:
        try:
            os.makedirs(args.report_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(args.report_dir, f"qa_ventas_{ts}.md")
            md = build_markdown(all_reports)
            with open(report_path, "w") as f:
                f.write(md)
            print(f"  {Colors.CYAN}Reporte guardado:{Colors.RESET} {report_path}")
        except Exception as exc:
            print(f"  {Colors.YELLOW}No se pudo guardar el reporte: {exc}{Colors.RESET}")

    sys.exit(0 if passed_cases == total_cases else 1)


if __name__ == "__main__":
    main()

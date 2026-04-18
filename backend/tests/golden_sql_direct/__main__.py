"""Entry point del golden suite de SQL Directo.

Uso:
    docker compose exec backend python -m tests.golden_sql_direct
    docker compose exec backend python -m tests.golden_sql_direct --only org_ambigua
    docker compose exec backend python -m tests.golden_sql_direct --delay 2
    docker compose exec backend python -m tests.golden_sql_direct --only basic

Flags:
    --only <substring>   Correr solo casos cuyo id matchea el substring.
    --delay <segundos>   Pausa entre casos (evita rate-limit de Claude).
    --section {basic|complex|clarification|all}   Sección específica.
"""

import argparse
import asyncio
import sys

from tests.golden_sql_direct import (
    CASES_BASIC,
    CASES_CLARIFICATION,
    CASES_COMPLEX,
    ALL_CASES,
)
from tests.golden_sql_direct.runner import run_all, format_summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Filtra por substring del id del caso",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Segundos de pausa entre casos (default: 0)",
    )
    parser.add_argument(
        "--section",
        choices=["basic", "complex", "clarification", "all"],
        default="all",
        help="Sección de casos a correr (default: all)",
    )
    args = parser.parse_args()

    cases_map = {
        "basic": CASES_BASIC,
        "complex": CASES_COMPLEX,
        "clarification": CASES_CLARIFICATION,
        "all": ALL_CASES,
    }
    cases = cases_map[args.section]

    print(
        f"🎯 Golden Suite SQL Directo — sección={args.section}, "
        f"{len(cases)} casos, delay={args.delay}s"
    )
    print()

    results = asyncio.run(
        run_all(cases=cases, only=args.only, delay=args.delay)
    )
    print(format_summary(results))

    failed = sum(1 for r in results if r["status"] == "FAIL")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

"""SQL execution and result formatting for SQL Direct."""

import time
from datetime import datetime

from sqlalchemy import text

from app.database import IdempiereSession


def execute_sql(sql: str, timeout_seconds: int = 30) -> tuple[list[str], list[tuple], float]:
    """Execute a validated SQL query against iDempiere (read-only).

    Returns (column_names, rows, elapsed_ms).
    """
    db = IdempiereSession()
    try:
        start = time.perf_counter()
        db.execute(text(f"SET statement_timeout = '{timeout_seconds * 1000}'"))
        result = db.execute(text(sql))
        cols = list(result.keys()) if result.returns_rows else []
        rows = result.fetchall() if result.returns_rows else []
        elapsed_ms = (time.perf_counter() - start) * 1000
        return cols, rows, elapsed_ms
    finally:
        db.close()


def format_results_as_markdown(cols: list[str], rows: list[tuple], max_rows: int = 50) -> str:
    """Format SQL results as a markdown table for the LLM."""
    if not rows:
        return "La consulta no devolvió resultados."

    total = len(rows)
    display_rows = rows[:max_rows]

    lines = [
        f"| {' | '.join(cols)} |",
        f"| {' | '.join(['---'] * len(cols))} |",
    ]
    for row in display_rows:
        cells = []
        for val in row:
            if val is None:
                cells.append("")
            elif isinstance(val, float):
                cells.append(f"{val:,.2f}")
            elif isinstance(val, datetime):
                cells.append(val.strftime("%Y-%m-%d"))
            else:
                cells.append(str(val))
        lines.append(f"| {' | '.join(cells)} |")

    if total > max_rows:
        lines.append(f"\n*(Mostrando {max_rows} de {total} resultados)*")

    return "\n".join(lines)

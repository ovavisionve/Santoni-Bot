"""Markdown formatting helpers used by agents to present data to the LLM."""

MAX_TABLE_ROWS = 50


def format_table(data: list[dict], columns: list[str] | None = None) -> str:
    """Format a list of dicts as a markdown table string for LLM context."""
    if not data:
        return "La consulta no arrojó resultados para los filtros aplicados."

    cols = columns or list(data[0].keys())
    header = "| " + " | ".join(
        str(c).replace("_", " ").title() for c in cols
    ) + " |"
    separator = "| " + " | ".join("---" for _ in cols) + " |"

    rows = []
    for row in data[:MAX_TABLE_ROWS]:
        values = []
        for c in cols:
            v = row.get(c, "")
            if isinstance(v, float):
                values.append(f"{v:,.2f}")
            else:
                values.append(str(v) if v is not None else "-")
        rows.append("| " + " | ".join(values) + " |")

    table = "\n".join([header, separator] + rows)
    if len(data) > MAX_TABLE_ROWS:
        table += f"\n\n*(Mostrando {MAX_TABLE_ROWS} de {len(data)} registros)*"
    return table


def format_summary(data: dict, title: str = "") -> str:
    """Format a summary dict as readable text for LLM context."""
    lines: list[str] = []
    if title:
        lines.append(f"## {title}")

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"\n### {key.replace('_', ' ').title()}")
            for k, v in value.items():
                if isinstance(v, float):
                    lines.append(f"- {k.replace('_', ' ').title()}: {v:,.2f}")
                else:
                    lines.append(f"- {k.replace('_', ' ').title()}: {v}")
        elif isinstance(value, list):
            lines.append(f"\n### {key.replace('_', ' ').title()}")
            if value and isinstance(value[0], dict):
                lines.append(format_table(value))
            else:
                for item in value[:20]:
                    lines.append(f"- {item}")
        elif isinstance(value, float):
            lines.append(f"- {key.replace('_', ' ').title()}: {value:,.2f}")
        else:
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")

    return "\n".join(lines)

"""Pre-formatted tables / value formatters for the ventas agent.

Purpose: el LLM (DeepSeek v3 en particular) tiende a re-renderizar tablas
con muchas columnas similares y mezcla valores entre filas. Estas funciones
producen la tabla ya final para que el LLM solo la copie verbatim.
"""


def fmt_ves(value: float | int | None) -> str:
    """Format a number in Venezuelan style: 1.234.567,89"""
    if value is None:
        return "-"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    s = f"{n:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def format_vendedores_table(
    rows: list[dict],
    title: str,
    limit: int = 10,
) -> str:
    """Pre-formatea la tabla de vendedores con columnas fijas, formato
    venezolano y ranking ya calculado, ordenada por VENTA NETA DESC.
    """
    if not rows:
        return f"## {title}\n\nLa consulta no arrojó resultados para los filtros aplicados."

    sorted_rows = sorted(
        rows,
        key=lambda r: r.get("total", 0) or 0,
        reverse=True,
    )[:limit]

    lines = [
        f"## {title}",
        "",
        "⚠️ TABLA FINAL PRE-FORMATEADA — COPIA EXACTA EN LA RESPUESTA:",
        "- NO reordenes las filas (ya están ordenadas por venta neta descendente)",
        "- NO renombres las columnas",
        "- NO cambies los valores ni los formates de otra manera",
        "- NO omitas ni agregues filas",
        "",
        "| # | Vendedor | Facturas | Notas Crédito | Venta Bruta (Bs.) | Monto NC (Bs.) | Venta Neta (Bs.) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(sorted_rows, start=1):
        lines.append(
            "| {pos} | {vend} | {fact} | {nc} | {bruto} | {mnc} | {neto} |".format(
                pos=i,
                vend=r.get("vendedor", "-"),
                fact=r.get("facturas", 0) or 0,
                nc=r.get("notas_credito", 0) or 0,
                bruto=fmt_ves(r.get("total_bruto", 0)),
                mnc=fmt_ves(r.get("monto_nc", 0)),
                neto=fmt_ves(r.get("total", 0)),
            )
        )
    return "\n".join(lines)


def is_empty_result(data) -> bool:
    """Check if query result is empty (empty list or dict with all-zero totals)."""
    if isinstance(data, list):
        return len(data) == 0
    if isinstance(data, dict):
        totals = data.get("totales", {})
        if isinstance(totals, dict):
            return all(
                v == 0 or v == 0.0
                for v in totals.values()
                if isinstance(v, (int, float))
            )
    return False


AMBIGUOUS_ORG_CLARIFICATION = (
    "## ¿A qué organización te refieres?\n\n"
    "El grupo Santoni tiene varias organizaciones con **INPROA** en el "
    "nombre y cada una tiene datos distintos. Para darte el dato "
    "exacto, especifica cuál quieres:\n\n"
    "| Organización | Giro | Cómo pedirla |\n"
    "|---|---|---|\n"
    "| **INPROA SANTONI C.A.** | Procesadora de arroz | `INPROA SANTONI` |\n"
    "| **InproMaiz C.A.** | Procesadora de maíz | `InproMaiz` |\n"
    "| **AGROINPROA C.A.** | Empresa agrícola | `AGROINPROA` |\n\n"
    "**Tip:** puedes pedir varias a la vez, por ejemplo:\n"
    "- `Top 10 vendedores de febrero 2026 en INPROA SANTONI`\n"
    "- `Top 10 vendedores de febrero 2026 en INPROA SANTONI e InproMaiz`\n\n"
    "Si no especificas organización, consultaré todas las que tienes "
    "permitidas en tu usuario."
)

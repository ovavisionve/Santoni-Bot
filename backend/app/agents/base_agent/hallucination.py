"""Hallucination detection + canned replacement for SantoniBot agents."""

import re


HALLUCINATION_REPLACEMENT = (
    "La consulta a iDempiere no arrojó resultados para los filtros aplicados.\n\n"
    "**¿Qué puedes intentar?**\n"
    "- Prueba con un período diferente (ej: otro mes o año)\n"
    "- Reformula la pregunta con más detalle\n"
    "- Verifica que los datos del período consultado estén cargados en el sistema\n\n"
    "*Nota: La conexión a iDempiere está activa. Solo muestro datos reales — "
    "no genero datos estimados ni aproximados.*"
)


def detect_hallucination(response_text: str, has_data: bool) -> bool:
    """Detect if the LLM likely hallucinated data.

    Returns True if hallucination is detected:
    - When no data was provided (has_data=False): tables with numbers = hallucination
    - When data WAS provided (has_data=True): fake invoice/doc numbers = hallucination
    """
    fake_docs = re.search(
        r'(?:FAC|NC|OC|FC|FP)-\d{4,}', response_text,
    )
    if fake_docs:
        return True

    fake_lotes = re.search(
        r'(?:Lote|LOTE)\s+(?:MA|AR|PR|IN|MZ)-[A-Z]{2,}-\d{3,}', response_text,
    )
    if fake_lotes:
        return True

    if has_data:
        return False

    table_with_numbers = re.search(
        r'\|[^|]*\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?[^|]*\|', response_text,
    )
    if table_with_numbers:
        return True

    currency_in_table = re.search(
        r'\|[^|]*(?:Bs\.?|USD|\$)\s*\d+[^|]*\|', response_text,
    )
    if currency_in_table:
        return True

    table_any_number = re.search(
        r'\|\s*\d+[\d.,]*\s*\|', response_text,
    )
    if table_any_number:
        table_rows = re.findall(r'^\|.+\|$', response_text, re.MULTILINE)
        if len(table_rows) >= 4:
            return True

    return False

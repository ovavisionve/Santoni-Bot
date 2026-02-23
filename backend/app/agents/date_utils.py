"""
Utilidades compartidas de extracción de fechas para todos los agentes de SantoniBot.

Formatos soportados:
- Rango: "01/01/2026 al 31/01/2026" o "01-01-2026 al 31-01-2026"
- Mes y año: "enero 2026", "febrero", "marzo 2025"
- Solo año: "2026", "2025"
"""

import re
from datetime import datetime

# Mapa de meses en español → número
MESES_MAP = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# Mapa inverso: número → nombre
MESES_NOMBRES = {v: k.title() for k, v in MESES_MAP.items()}

# Regex: dd/mm/yyyy al dd/mm/yyyy (o con guiones)
_DATE_RANGE_RE = re.compile(
    r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s+al\s+(\d{1,2})[/-](\d{1,2})[/-](\d{4})'
)


def extract_date_range(message: str) -> tuple[str | None, str | None]:
    """Extract date range from 'dd/mm/yyyy al dd/mm/yyyy' pattern.

    Returns (date_from, date_to) in 'YYYY-MM-DD' format, or (None, None).
    """
    m = _DATE_RANGE_RE.search(message)
    if m:
        d1, m1, y1, d2, m2, y2 = m.groups()
        try:
            date_from = f"{y1}-{int(m1):02d}-{int(d1):02d}"
            date_to = f"{y2}-{int(m2):02d}-{int(d2):02d}"
            return date_from, date_to
        except (ValueError, IndexError):
            pass
    return None, None


def extract_month_year(message: str) -> tuple[int | None, int]:
    """Extract month name and year from message text.

    Returns (mes, anio). Mes can be None if no month found.
    Year defaults to current year if not specified.
    """
    msg = message.lower()
    anio = datetime.now().year
    year_match = re.search(r'20\d{2}', message)
    if year_match:
        anio = int(year_match.group())

    mes = None
    for nombre, num in MESES_MAP.items():
        if nombre in msg:
            mes = num
            break

    return mes, anio


def build_period_label(
    date_from: str | None = None,
    date_to: str | None = None,
    mes: int | None = None,
    anio: int | None = None,
) -> str:
    """Build a human-readable label for the period being queried."""
    if date_from and date_to:
        return f"{date_from} al {date_to}"
    if mes and anio:
        return f"{MESES_NOMBRES.get(mes, str(mes))} {anio}"
    if anio:
        return f"Anio {anio}"
    return "Todos los periodos"

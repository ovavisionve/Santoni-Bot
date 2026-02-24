"""
Utilidades compartidas de extracción de fechas y moneda para todos los agentes de SantoniBot.

Formatos de fecha soportados:
- Rango con separadores: "01/01/2026 al 31/01/2026", "01-01-2026 al 31-01-2026"
- Rango con año corto: "01/01/26 al 31/01/26", "1/1/26 al 31/1/26"
- Rango compacto (ddmmyyyy o ddmmyy): "01012026 al 31012026", "010126 al 310126"
- Rango mixto: "01/12/2025 al 311225" (una con separadores, otra compacta)
- Mes y año: "enero 2026", "febrero", "marzo 2025"
- Solo año: "2026", "2025"

Monedas detectadas:
- VES/Bolívares: "bolivares", "bs", "ves" → c_currency_id 205
- USD/Dólares: "dolares", "usd", "dol" → c_currency_id 100
"""

import calendar
import re
from datetime import datetime, timedelta

# Mapa de meses en español → número
MESES_MAP = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# Mapa inverso: número → nombre
MESES_NOMBRES = {v: k.title() for k, v in MESES_MAP.items()}

# Individual date patterns
_SEP_DATE_RE = re.compile(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})')
_COMPACT_DATE_RE = re.compile(r'\b(\d{6,8})\b')

# Currency detection patterns
_CURRENCY_VES_RE = re.compile(r'\b(bol[ií]vares?|bs\.?f?|ves)\b', re.IGNORECASE)
_CURRENCY_USD_RE = re.compile(r'\b(d[oó]lares?|usd|dol)\b', re.IGNORECASE)

# iDempiere c_currency_id values
# Santoni uses multiple currency entries for dollars (DOL, Dol, DoL, USA, dol, etc.)
# All must be included when filtering by "dólares"
CURRENCY_IDS: dict[str, list[int]] = {
    "VES": [205],
    "USD": [100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017],
}

# "al" keyword to split date ranges
_AL_RE = re.compile(r'\bal\b', re.IGNORECASE)


def _normalize_year(y: str) -> str:
    """Convert 2-digit year to 4-digit (assumes 2000s)."""
    if len(y) == 2:
        return f"20{y}"
    return y


def _parse_single_date(text: str) -> str | None:
    """Try to parse a single date from text. Returns 'YYYY-MM-DD' or None.

    Tries separated format (dd/mm/yyyy, dd/mm/yy) first, then compact (ddmmyyyy, ddmmyy).
    """
    # Try separated format: dd/mm/yyyy or dd/mm/yy
    m = _SEP_DATE_RE.search(text)
    if m:
        d, mo, y = m.groups()
        try:
            y = _normalize_year(y)
            yi, mi, di = int(y), int(mo), int(d)
            if 2000 <= yi <= 2099 and 1 <= mi <= 12 and 1 <= di <= 31:
                return f"{yi}-{mi:02d}-{di:02d}"
        except (ValueError, IndexError):
            pass

    # Try compact format: ddmmyyyy (8) or ddmmyy (6)
    m = _COMPACT_DATE_RE.search(text)
    if m:
        s = m.group(1)
        if len(s) == 8:
            d, mo, y = int(s[0:2]), int(s[2:4]), int(s[4:8])
        elif len(s) == 6:
            d, mo, y = int(s[0:2]), int(s[2:4]), int(f"20{s[4:6]}")
        else:
            return None
        if 1 <= mo <= 12 and 1 <= d <= 31 and 2000 <= y <= 2099:
            return f"{y}-{mo:02d}-{d:02d}"

    return None


def extract_date_range(message: str) -> tuple[str | None, str | None]:
    """Extract date range from message text.

    Supported patterns:
    - Explicit range: "01/01/2026 al 31/01/2026", "01012026 al 31012026"
    - Relative end: "desde noviembre 2025 a la fecha", "desde enero hasta hoy"

    Returns (date_from, date_to) in 'YYYY-MM-DD' format, or (None, None).
    """
    msg = message.lower()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # Pattern: "desde [month] [year] a la fecha / hasta hoy"
    has_today_end = any(p in msg for p in [
        "a la fecha", "hasta hoy", "hasta la fecha", "fecha de hoy",
    ])
    desde_match = re.search(r'desde\s+(\w+)(?:\s+(?:de\s+)?(\d{4}))?', msg)
    if desde_match and has_today_end:
        month_name = desde_match.group(1)
        if month_name in MESES_MAP:
            month_num = MESES_MAP[month_name]
            year = int(desde_match.group(2)) if desde_match.group(2) else now.year
            date_from = f"{year}-{month_num:02d}-01"
            return date_from, today

    # Pattern: multiple month names → date range
    # e.g. "septiembre, octubre y noviembre 2025" → 2025-09-01 al 2025-11-30
    found_months = [num for nombre, num in MESES_MAP.items() if nombre in msg]
    if len(found_months) >= 2:
        year_match = re.search(r'20\d{2}', message)
        year = int(year_match.group()) if year_match else now.year
        min_month = min(found_months)
        max_month = max(found_months)
        last_day = calendar.monthrange(year, max_month)[1]
        return f"{year}-{min_month:02d}-01", f"{year}-{max_month:02d}-{last_day:02d}"

    # Standard "al" pattern: "01/01/2026 al 31/01/2026"
    al_match = _AL_RE.search(message)
    if not al_match:
        return None, None

    before_al = message[:al_match.start()]
    after_al = message[al_match.end():]

    date_from = _parse_single_date(before_al)
    date_to = _parse_single_date(after_al)

    if date_from and date_to:
        return date_from, date_to

    # ── Single-date / relative-date patterns (no "al" separator) ──

    # Single explicit date: "el 24/02/2026", "20/02/2026" → same-day range
    single = _parse_single_date(message)
    if single:
        return single, single

    # "hoy" / "el dia de hoy" (not inside "desde ... hasta hoy" which was handled above)
    if re.search(r'\bhoy\b', msg) and "desde" not in msg:
        return today, today

    # "ayer"
    if re.search(r'\bayer\b', msg):
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        return yesterday, yesterday

    return None, None


def extract_month_year(message: str) -> tuple[int | None, int]:
    """Extract month name and year from message text.

    Handles:
    - Explicit months: "enero 2025", "marzo"
    - Relative references: "este mes", "mes actual", "mes pasado", "mes anterior"

    Returns (mes, anio). Mes can be None if no month found.
    Year defaults to current year if not specified.
    """
    msg = message.lower()
    now = datetime.now()
    anio = now.year
    year_match = re.search(r'20\d{2}', message)
    if year_match:
        anio = int(year_match.group())

    mes = None

    # Relative month references (before explicit month names)
    if any(p in msg for p in ["este mes", "mes actual", "mes en curso"]):
        mes = now.month
        anio = now.year  # override year even if another year was mentioned
        return mes, anio
    if any(p in msg for p in ["mes pasado", "mes anterior"]):
        if now.month == 1:
            mes = 12
            anio = now.year - 1
        else:
            mes = now.month - 1
            anio = now.year
        return mes, anio

    # Explicit month names
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
        return f"Año {anio}"
    return "Todos los periodos"


def detect_currency(message: str) -> list[int] | None:
    """Detect currency from user message.

    Returns list of iDempiere c_currency_id values, or None if not specified.
    Multiple IDs are needed because Santoni uses several currency entries
    for dollars (DOL, Dol, DoL, USA, dol, USD, etc.).
    """
    if _CURRENCY_VES_RE.search(message):
        return CURRENCY_IDS["VES"]
    if _CURRENCY_USD_RE.search(message):
        return CURRENCY_IDS["USD"]
    return None

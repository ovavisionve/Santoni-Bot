"""
Agente de Contabilidad - Alimentos Santoni
Especializado en: balance general, estado de resultados, libros contables,
impuestos, activos fijos, consultas de cuentas específicas.
"""

import re
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.query_service import build_accounting_summary, build_account_detail


# Regex for account codes like 2.01.01.10, 1.01.02, etc.
_ACCOUNT_CODE_RE = re.compile(r'\b(\d\.\d{2}(?:\.\d{2}){1,3})\b')

# Regex for date ranges in dd/mm/yyyy format
_DATE_RANGE_RE = re.compile(
    r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s+al\s+(\d{1,2})[/-](\d{1,2})[/-](\d{4})'
)

_MESES_MAP = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _extract_date_range(message: str) -> tuple[str | None, str | None]:
    """Extract date range from 'dd/mm/yyyy al dd/mm/yyyy' pattern.
    Returns (date_from, date_to) in 'YYYY-MM-DD' format, or (None, None)."""
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


def _extract_month_year(message: str) -> tuple[int | None, int]:
    """Extract month name and year from message text."""
    msg = message.lower()
    anio = datetime.now().year
    year_match = re.search(r'20\d{2}', message)
    if year_match:
        anio = int(year_match.group())

    mes = None
    for nombre, num in _MESES_MAP.items():
        if nombre in msg:
            mes = num
            break

    return mes, anio


class ContabilidadAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "contabilidad"

    @property
    def display_name(self) -> str:
        return "Contabilidad"

    @property
    def department(self) -> str:
        return "contabilidad"

    @property
    def description(self) -> str:
        return (
            "Consultas contables: balance general, estado de resultados, "
            "libro diario/mayor, impuestos, activos fijos, cuentas específicas"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Contabilidad de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es la contabilidad empresarial y reportes financieros formales.

CAPACIDADES:
- Consultar saldos y movimientos de cuentas específicas por código (ej: 2.01.01.10)
- Balance general y análisis de estructura patrimonial
- Estado de resultados
- Libro diario y libro mayor
- Balanza de comprobación
- Comparativas entre períodos contables

REGLAS:
- Responde siempre en español, de forma profesional y técnica
- Usa terminología contable venezolana estándar
- Indica el período contable de referencia
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si los datos dicen 0 movimientos, informa que no hay movimientos.
- Si recibes un error indicando que la cuenta no fue encontrada, informa al usuario.

IMPORTANTE SOBRE PERÍODOS:
- Los datos que recibes corresponden al año actual por defecto, a menos que el usuario especifique otro año
- SIEMPRE indica claramente el período contable de los datos que estás presentando
- Usa formato venezolano: punto=miles, coma=decimal (ej: 1.234.567,89)
- Si el usuario especificó un rango de fechas, los datos ya vienen filtrados para ese rango exacto"""

    def get_sql_context(self) -> str:
        return """
Datos contables provienen de fact_acct (hechos contables) y c_elementvalue (plan de cuentas) en iDempiere.
Se pueden consultar cuentas específicas por código (ej: 2.01.01.10) con rango de fechas.
"""

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None) -> str | None:
        sections = []

        # Check if user is asking about a specific account code
        account_match = _ACCOUNT_CODE_RE.search(message)

        if account_match:
            account_code = account_match.group(1)

            # Try to extract date range first (dd/mm/yyyy al dd/mm/yyyy)
            date_from, date_to = _extract_date_range(message)

            if date_from and date_to:
                # Specific date range query
                detail = build_account_detail(
                    account_code=account_code,
                    date_from=date_from,
                    date_to=date_to,
                    org_ids=org_ids,
                )
            else:
                # Fall back to month/year extraction
                mes, anio = _extract_month_year(message)
                detail = build_account_detail(
                    account_code=account_code,
                    mes=mes,
                    anio=anio,
                    org_ids=org_ids,
                )

            if "error" in detail:
                sections.append(f"**ERROR:** {detail['error']}")
            else:
                sections.append(self._format_summary(detail, f"Cuenta {account_code}"))
        else:
            # General accounting summary (no specific account)
            mes, anio = _extract_month_year(message)
            label = f"Año {anio}" if anio else "Todos los años"
            if mes:
                mes_nombres = {v: k.title() for k, v in _MESES_MAP.items()}
                label = f"{mes_nombres.get(mes, '')} {anio}"
            summary = build_accounting_summary(mes=mes, anio=anio, org_ids=org_ids)
            sections.append(self._format_summary(summary, f"Resumen Contable - {label}"))

        return "\n\n".join(sections) if sections else None

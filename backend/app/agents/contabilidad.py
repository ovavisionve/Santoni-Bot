"""
Agente de Contabilidad - Alimentos Santoni
Especializado en: balance general, estado de resultados, libros contables,
impuestos, activos fijos.
"""

import re
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.query_service import build_accounting_summary


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
            "libro diario/mayor, impuestos, activos fijos"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Contabilidad de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es la contabilidad empresarial y reportes financieros formales.

CAPACIDADES:
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

IMPORTANTE SOBRE PERÍODOS:
- Los datos que recibes corresponden al año actual por defecto, a menos que el usuario especifique otro año
- SIEMPRE indica claramente el período contable de los datos que estás presentando
- Si el usuario hace una pregunta amplia sin especificar período, presenta los datos del año actual y al final sugiere: "Si necesitas datos de otro período contable, indícame el año o mes que deseas consultar."
- Si el usuario menciona un año específico, los datos ya vendrán filtrados para ese año"""

    def get_sql_context(self) -> str:
        return """
Datos contables provienen de fact_acct (hechos contables) y c_elementvalue (plan de cuentas) en iDempiere.
"""

    def fetch_data(self, message: str, org_ids: list[int] | None = None) -> str | None:
        msg = message.lower()
        sections = []

        anio = datetime.now().year
        year_match = re.search(r'20\d{2}', message)
        if year_match:
            anio = int(year_match.group())

        mes = None
        meses_map = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
            "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
            "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
        }
        for nombre, num in meses_map.items():
            if nombre in msg:
                mes = num
                break

        label = f"Año {anio}" if anio else "Todos los años"
        summary = build_accounting_summary(mes=mes, anio=anio, org_ids=org_ids)
        sections.append(self._format_summary(summary, f"Resumen Contable - {label}"))

        return "\n\n".join(sections) if sections else None

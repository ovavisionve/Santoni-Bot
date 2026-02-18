"""
Agente de Finanzas - Alimentos Santoni
Especializado en: flujo de caja, cuentas por cobrar/pagar, bancos,
presupuestos, indicadores financieros, rentabilidad.
"""

import re
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.query_service import (
    build_financial_summary,
    build_overdue_receivables,
)


class FinanzasAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "finanzas"

    @property
    def display_name(self) -> str:
        return "Finanzas"

    @property
    def department(self) -> str:
        return "finanzas"

    @property
    def description(self) -> str:
        return (
            "Consultas financieras: flujo de caja, cuentas por cobrar/pagar, "
            "bancos, presupuestos, indicadores financieros"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Finanzas de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es el análisis financiero empresarial.

CAPACIDADES:
- Flujo de caja y posición de tesorería
- Cuentas por cobrar y cuentas por pagar
- Estado de cuentas bancarias
- Indicadores financieros
- Alertas de morosidad y vencimientos

REGLAS:
- Responde siempre en español, de forma profesional y clara
- Usa formato de moneda (Bs. o $) y separadores de miles
- Indica el período o fecha de los datos
- Los datos que recibes son REALES de la base de datos de Santoni

IMPORTANTE SOBRE PERÍODOS:
- Los datos que recibes corresponden al año actual por defecto, a menos que el usuario especifique otro año
- SIEMPRE indica claramente el período de los datos que estás presentando
- Si el usuario hace una pregunta amplia sin especificar período, presenta los datos del año actual y al final sugiere: "Si necesitas datos de otro período, indícame el año o mes que deseas consultar."
- Si el usuario menciona un año específico, los datos ya vendrán filtrados para ese año"""

    def get_sql_context(self) -> str:
        return """
Tablas: demo_cuentas_bancarias, demo_movimientos_bancarios, demo_cuentas_por_pagar
"""

    def fetch_data(self, message: str) -> str | None:
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
        summary = build_financial_summary(mes=mes, anio=anio)
        sections.append(self._format_summary(summary, f"Resumen Financiero - {label}"))

        if any(w in msg for w in ["cobrar", "morosidad", "vencid", "atras"]):
            data = build_overdue_receivables()
            sections.append("## Cuentas por Cobrar Vencidas")
            sections.append(self._format_table(data))

        return "\n\n".join(sections) if sections else None

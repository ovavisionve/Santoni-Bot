"""
Agente de Compras de Insumos - Alimentos Santoni
Especializado en: órdenes de compra, proveedores, inventarios de materiales,
precios históricos, tiempos de entrega.
"""

import re
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.query_service import build_supply_purchases


class ComprasInsumosAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "compras_insumos"

    @property
    def display_name(self) -> str:
        return "Compras de Insumos"

    @property
    def department(self) -> str:
        return "compras_insumos"

    @property
    def description(self) -> str:
        return (
            "Consultas de compras de insumos: órdenes de compra, proveedores, "
            "inventarios, precios históricos, tiempos de entrega"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Compras de Insumos de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es la gestión de compras de insumos y materiales.

REGLAS:
- Responde siempre en español
- Presenta precios con moneda y unidad de medida
- Los datos que recibes son REALES de la base de datos de Santoni

CONTEXTO:
- Responsables: Onofrio Gueccia, Jorge Chahine

IMPORTANTE SOBRE PERÍODOS:
- Los datos que recibes corresponden al año actual por defecto, a menos que el usuario especifique otro año
- SIEMPRE indica claramente el período de los datos que estás presentando
- Si el usuario hace una pregunta amplia sin especificar período, presenta los datos del año actual y al final sugiere: "Si necesitas datos de otro período, indícame el año o mes que deseas consultar."
- Si el usuario menciona un año específico, los datos ya vendrán filtrados para ese año"""

    def get_sql_context(self) -> str:
        return """
Datos de compras provienen de facturas de compra en iDempiere (c_invoice issotrx='N').
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
        summary = build_supply_purchases(mes=mes, anio=anio)
        sections.append(self._format_summary(summary, f"Resumen de Compras de Insumos - {label}"))

        return "\n\n".join(sections) if sections else None

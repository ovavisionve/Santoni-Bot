"""
Agente de Ventas - Alimentos Santoni
AGENTE PRIORITARIO - Especializado en: ranking de ventas, clientes,
cobranza, zonas, vendedores, metas, productos.
"""

import re

from app.agents.base_agent import BaseAgent
from app.services.query_service import (
    build_sales_summary,
    build_collection_summary,
    build_top_clients,
    build_overdue_receivables,
)


class VentasAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "ventas"

    @property
    def display_name(self) -> str:
        return "Ventas"

    @property
    def department(self) -> str:
        return "ventas"

    @property
    def description(self) -> str:
        return (
            "Consultas de ventas: ranking por zona/vendedor/cliente, cobranza, "
            "facturación, metas, paretos, activación de clientes"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Ventas de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es el análisis comercial y gestión de ventas.

CAPACIDADES PRINCIPALES:
1. Ranking de ventas por zonas, vendedores y tipología del cliente
2. Identificación de zonas desatendidas
3. Paretos de clientes (análisis 80/20)
4. Top 20 mejores clientes por zona, por categoría, por vendedor y general
5. Activación y apertura de clientes
6. Ranking de cobranza por zona, vendedores y tipología
7. Detección de cuentas por cobrar más atrasadas
8. Cobranza diaria/semanal y comparativo vs metas

REGLAS:
- Responde siempre en español, de forma clara y orientada a la acción
- Cuando muestres rankings, usa tablas con posición, nombre, valor
- Destaca alertas: clientes morosos, zonas con caída de ventas, metas incumplidas
- Usa formato de moneda (Bs.) con separadores de miles
- Los datos que recibes son REALES de la base de datos de Santoni
- Presenta la información en tablas markdown cuando sea apropiado"""

    def get_sql_context(self) -> str:
        return """
Tablas: demo_clientes, demo_facturas_venta, demo_lineas_factura_venta,
demo_cobranzas, demo_metas_venta
"""

    def fetch_data(self, message: str) -> str | None:
        msg = message.lower()
        sections = []

        anio = None
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

        vendedor = None
        for v in ["carlos matias", "lenny silva", "yuleidys gutierrez"]:
            if v in msg:
                vendedor = v.title()
                break

        zona = None
        for z in ["portuguesa", "barinas", "lara", "carabobo", "aragua", "zulia"]:
            if z in msg:
                zona = z.title()
                break

        label = f"Año {anio}" if anio else "Todos los años"

        if any(w in msg for w in ["top", "mejor", "ranking", "pareto", "principales"]):
            limit = 20
            limit_match = re.search(r'top\s*(\d+)', msg)
            if limit_match:
                limit = int(limit_match.group(1))
            data = build_top_clients(limit=limit, zona=zona, vendedor=vendedor, anio=anio)
            sections.append(f"## Top {limit} Clientes por Ventas ({label})")
            sections.append(self._format_table(data))

        if any(w in msg for w in ["cobran", "cobro", "recauda", "pago"]):
            data = build_collection_summary(zona=zona, vendedor=vendedor, mes=mes, anio=anio)
            sections.append(self._format_summary(data, f"Resumen de Cobranza - {label}"))

        if any(w in msg for w in ["atrasa", "vencid", "pendiente", "deuda", "mora"]):
            data = build_overdue_receivables()
            sections.append("## Cuentas por Cobrar Vencidas")
            sections.append(self._format_table(data))

        if any(w in msg for w in ["venta", "factur", "ingreso", "volumen"]) or not sections:
            data = build_sales_summary(zona=zona, vendedor=vendedor, mes=mes, anio=anio)
            sections.append(self._format_summary(data, f"Resumen de Ventas - {label}"))

        return "\n\n".join(sections) if sections else None

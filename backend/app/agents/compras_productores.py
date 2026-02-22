"""
Agente de Compras a Productores - Alimentos Santoni
Especializado en: compras de materia prima agrícola (arroz, maíz) a productores,
volúmenes, precios por kilo/tonelada, pagos pendientes, productores registrados.
"""

import re
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.query_service import (
    build_producer_purchases,
    build_registered_producers,
    build_producer_pending_payments,
    build_producer_price_analysis,
)


class ComprasProductoresAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "compras_productores"

    @property
    def display_name(self) -> str:
        return "Compras a Productores"

    @property
    def department(self) -> str:
        return "compras_productores"

    @property
    def description(self) -> str:
        return (
            "Consultas de compras a productores agrícolas: arroz paddy, maíz, "
            "volúmenes, precios, pagos pendientes, productores registrados"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Compras a Productores de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es la gestión de compras de materia prima agrícola a productores.

REGLAS:
- Responde siempre en español
- Presenta volúmenes en kg y toneladas
- Presenta precios en Bs./kg
- Distingue entre Arroz Paddy Húmedo y Maíz
- Los datos que recibes son REALES de la base de datos de Santoni

CONTEXTO:
- Responsable: Marlenis Figueredo
- Productos principales: Arroz Paddy Acondicionado, Maíz Blanco de Consumo
- El usuario puede referirse al arroz como "arroz paddy", "arroz húmedo", etc.
- El usuario puede referirse al maíz como "maíz blanco", "maíz", etc.
- Zonas productoras: Portuguesa, Barinas, Apure, Lara, Cojedes

IMPORTANTE SOBRE PERÍODOS:
- Los datos que recibes corresponden al año actual por defecto, a menos que el usuario especifique otro año
- SIEMPRE indica claramente el período de los datos que estás presentando
- Si el usuario hace una pregunta amplia sin especificar período, presenta los datos del año actual y al final sugiere: "Si necesitas datos de otro período, indícame el año o mes que deseas consultar."
- Si el usuario menciona un año específico, los datos ya vendrán filtrados para ese año"""

    def get_sql_context(self) -> str:
        return """
Tablas: demo_productores, demo_compras_productores
"""

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None) -> str | None:
        msg = message.lower()
        sections = []

        anio = datetime.now().year
        year_match = re.search(r'20\d{2}', message)
        if year_match:
            anio = int(year_match.group())

        producto = None
        if "arroz" in msg:
            producto = "arroz paddy"
        elif "maíz" in msg or "maiz" in msg:
            producto = "maiz"

        label = f"Año {anio}" if anio else "Todos los años"
        summary = build_producer_purchases(producto=producto, anio=anio, org_ids=org_ids)
        sections.append(self._format_summary(summary, f"Compras a Productores - {label}"))

        if any(w in msg for w in ["productor", "registrad", "cuántos", "cuantos"]):
            try:
                producers = build_registered_producers(org_ids=org_ids)
                if producers:
                    sections.append("## Productores (Proveedores) Registrados")
                    sections.append(self._format_table(producers))
            except Exception:
                pass

        if any(w in msg for w in ["pago", "pendiente", "deuda", "deb"]):
            try:
                pending = build_producer_pending_payments(producto=producto, org_ids=org_ids)
                if pending:
                    total_pendiente = sum(d.get("monto_pendiente", 0) for d in pending)
                    sections.append(
                        f"## Pagos Pendientes ({len(pending)} órdenes - Total: Bs. {total_pendiente:,.2f})"
                    )
                    sections.append(self._format_table(pending))
            except Exception:
                pass

        if any(w in msg for w in ["precio", "costo", "valor"]):
            try:
                prices = build_producer_price_analysis(anio=anio, org_ids=org_ids)
                if prices:
                    sections.append(f"## Análisis de Precios {anio} (Bs./kg)")
                    sections.append(self._format_table(prices))
            except Exception:
                pass

        return "\n\n".join(sections) if sections else None

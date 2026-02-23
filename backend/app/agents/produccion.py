"""
Agente de Producción - Alimentos Santoni
Especializado en: producción diaria, órdenes de producción, eficiencia (OEE),
desperdicios, mantenimientos.

Fuente de datos: pp_order, pp_order_bomline, pp_cost_collector,
m_product, m_warehouse en iDempiere (PostgreSQL 13).
"""

from app.agents.base_agent import BaseAgent
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
)
from app.services.query_service import (
    build_production_summary,
    build_production_orders,
)


class ProduccionAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "produccion"

    @property
    def display_name(self) -> str:
        return "Producción"

    @property
    def department(self) -> str:
        return "produccion"

    @property
    def description(self) -> str:
        return (
            "Consultas de producción: producción diaria, órdenes, eficiencia OEE, "
            "desperdicios, mantenimientos, turnos"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Producción de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es el análisis de operaciones de producción agroindustrial.

CAPACIDADES:
- Órdenes de manufactura (completadas, en proceso, planificadas)
- Productos terminados y cantidades producidas
- Lista de materiales (BOM) por orden de producción
- Registro de costos de producción (cost collector)

CONTEXTO iDEMPIERE:
- Órdenes de manufactura: pp_order (documentno, dateordered, datepromised, m_product_id, qtyordered, qtydelivered, docstatus)
- Lista de materiales: pp_order_bomline (pp_order_id, m_product_id, qtyrequiered, qtyreserved)
- Recolección de costos: pp_cost_collector (pp_order_id, movementqty, costcollectortype)
- Productos: m_product (40,766 productos) con m_product_category
- Almacenes: m_warehouse
- Movimientos de inventario: m_inout (262,794 registros), m_inoutline
- Organizaciones: INPROA SANTONI, AGROINPROA, AGROPECUARIA R.R., Agro Import, INVERSIONES AGA, InproMaiz, AGA AGRICOLA, Santoni Service

REGLAS:
- Responde siempre en español, de forma técnica pero comprensible
- Usa unidades métricas (kg, toneladas)
- Presenta porcentajes de eficiencia y desperdicio cuando haya datos
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa claramente

CONTEXTO OPERATIVO:
- 2 plantas en Agua Blanca, Estado Portuguesa
- Productos principales: Arroz Santoni Premium, Harina de Maíz Santoni
- Turnos rotativos en planta

FORMATOS DE FECHA SOPORTADOS:
- Rango específico: "01/01/2026 al 31/01/2026"
- Mes y año: "enero 2026"
- Solo año: "2026"

IMPORTANTE SOBRE PERÍODOS:
- Los datos corresponden al año actual por defecto, a menos que el usuario especifique otro año
- SIEMPRE indica claramente el período de los datos que estás presentando
- Si el usuario hace una pregunta amplia sin período, presenta datos del año actual y sugiere: "Si necesitas datos de otro período, indícame el año, mes o rango de fechas."
- Si el usuario especificó un rango de fechas, los datos ya vienen filtrados para ese rango exacto"""

    def get_sql_context(self) -> str:
        return """
Datos de producción en iDempiere:
- pp_order: Órdenes de manufactura (documentno, dateordered, datepromised, m_product_id, qtyordered, qtydelivered, docstatus)
- pp_order_bomline: Lista de materiales por orden (m_product_id, qtyrequiered)
- pp_cost_collector: Recolección de costos (movementqty, costcollectortype)
- m_product: Productos (name, m_product_category_id)
- m_warehouse: Almacenes
- m_inout: Movimientos de inventario (262,794 registros)
"""

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)
        if date_from and date_to:
            mes = None

        label = build_period_label(date_from, date_to, mes, anio)

        # Production summary (always)
        summary = build_production_summary(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
        )
        sections.append(self._format_summary(summary, f"Resumen de Producción - {label}"))

        if any(w in msg for w in ["orden", "pedido", "planific", "manufactura"]):
            data = build_production_orders(
                mes=mes, anio=anio, org_ids=org_ids,
                date_from=date_from, date_to=date_to,
            )
            if data:
                sections.append(f"## Órdenes de Manufactura ({len(data)} registros)")
                sections.append(self._format_table(data))

        return "\n\n".join(sections) if sections else None

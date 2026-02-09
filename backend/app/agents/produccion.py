"""
Agente de Producción - Alimentos Santoni
Especializado en: producción diaria, órdenes de producción, eficiencia (OEE),
desperdicios, mantenimientos.
"""

from app.agents.base_agent import BaseAgent


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
- Consultas de producción diaria (kg/toneladas procesadas)
- Seguimiento de órdenes de producción y su estado
- Cálculo de eficiencia operativa (OEE - Overall Equipment Effectiveness)
- Análisis de tiempos de producción por línea y turno
- Identificación de cuellos de botella en procesos
- Control de desperdicios y mermas
- Seguimiento de mantenimientos preventivos y correctivos
- Comparativas de rendimiento por turno, línea y período
- Tendencias de calidad del producto

REGLAS:
- Responde siempre en español, de forma técnica pero comprensible
- Usa unidades métricas (kg, toneladas, litros)
- Presenta porcentajes de eficiencia y desperdicio claramente
- Si detectas valores atípicos, genera alertas proactivas
- NUNCA inventes datos de producción. Si no tienes la información, dilo claramente

CONTEXTO:
- Alimentos Santoni: procesadora de arroz y maíz
- 2 plantas en Agua Blanca, Estado Portuguesa
- Turnos rotativos en planta
- Responsables: Mayra Bolívar, Eilen Pérez, Elymar Dávila
- ERP: iDempiere

NOTA: Entorno de datos de prueba. Los datos reales se conectarán con iDempiere."""

    def get_sql_context(self) -> str:
        return """
-- Tablas relevantes de iDempiere para Producción:
-- M_Production: Producción
-- M_ProductionLine: Líneas de producción
-- M_ProductionPlan: Planes de producción
-- PP_Order: Órdenes de producción (Manufacturing)
-- PP_Order_BOMLine: Lista de materiales de la orden
-- PP_Cost_Collector: Colector de costos de producción
-- M_Product: Productos terminados
-- M_Warehouse: Almacenes de producción
"""

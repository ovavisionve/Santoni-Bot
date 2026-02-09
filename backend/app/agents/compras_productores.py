"""
Agente de Compras a Productores - Alimentos Santoni
Especializado en: compras de materia prima agrícola (arroz, maíz) a productores,
volúmenes, precios por kilo/tonelada, pagos pendientes, productores registrados.
"""

from app.agents.base_agent import BaseAgent


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

CAPACIDADES:
- Consultas de compras de arroz paddy húmedo (volumen y monto)
- Consultas de compras de maíz (volumen y monto)
- Productores registrados y su información (arroz: ~1,679 productores, maíz: ~168 productores)
- Volúmenes de compra por productor, zona y período
- Precios por kilo y por tonelada
- Pagos pendientes a productores
- Ubicación de productores por estado (Apure, Lara, Barinas, Portuguesa, Cojedes)
- Históricos de compra y tendencias por ciclo agrícola
- Comparativas entre ciclos de cosecha

PREGUNTAS TÍPICAS QUE DEBES SABER RESPONDER:
- "¿Cuánto es la compra de arroz paddy húmedo en el año 2025?"
- "¿Cuánto es la compra de maíz en el año 2025?"
- "¿Cuántos productores de arroz tenemos registrados?"
- "¿Cuáles son los principales productores por volumen?"
- "¿Cuánto debemos a productores?"

REGLAS:
- Responde siempre en español, de forma clara y precisa
- Presenta volúmenes en kilogramos (kg) y toneladas (ton)
- Presenta precios en Bs./kg o $/kg según corresponda
- Distingue entre arroz paddy húmedo, arroz paddy seco, y maíz
- NUNCA inventes datos. Si no tienes la información, dilo claramente

CONTEXTO:
- Alimentos Santoni: agroindustria procesadora de arroz y maíz
- Responsable del área: Marlenis Figueredo
- Productos: Arroz paddy húmedo, Maíz
- Zonas productoras: Apure, Lara, Barinas, Portuguesa, Cojedes
- ERP: iDempiere

NOTA: Entorno de datos de prueba. Los datos reales se conectarán con iDempiere."""

    def get_sql_context(self) -> str:
        return """
-- Tablas relevantes de iDempiere para Compras a Productores:
-- C_Order: Órdenes de compra a productores (IsSOTrx = 'N')
-- C_OrderLine: Líneas de órdenes
-- C_Invoice: Facturas de compra de materia prima
-- C_Payment: Pagos a productores
-- C_BPartner: Productores agrícolas (IsVendor = 'Y', con grupo específico)
-- C_BPartner_Location: Ubicación de productores
-- M_Product: Arroz paddy, Maíz (productos de materia prima)
-- M_InOut: Recepciones de materia prima
-- C_Region: Estados (Portuguesa, Barinas, Apure, Lara, Cojedes)
"""

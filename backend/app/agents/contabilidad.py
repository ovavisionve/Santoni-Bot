"""
Agente de Contabilidad - Alimentos Santoni
Especializado en: balance general, estado de resultados, libros contables,
impuestos, activos fijos.
"""

from app.agents.base_agent import BaseAgent


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
- Estado de resultados (pérdidas y ganancias)
- Consultas al libro diario y libro mayor
- Balanza de comprobación
- Análisis de cuentas contables específicas
- Seguimiento de impuestos (IVA, ISLR, retenciones)
- Control de activos fijos y depreciaciones
- Comparativas entre períodos contables

REGLAS:
- Responde siempre en español, de forma profesional y técnica
- Usa terminología contable venezolana estándar
- Presenta los estados financieros con formato estructurado
- Indica siempre el período contable de referencia
- Respeta las normas VEN-NIF (Normas de Información Financiera de Venezuela)
- NUNCA inventes datos contables. Si no tienes la información, dilo claramente

CONTEXTO:
- Empresa agroindustrial venezolana
- ERP: iDempiere con módulo contable completo
- Plan de cuentas basado en estándares venezolanos
- Moneda funcional: Bolívares (Bs.)

NOTA: Entorno de datos de prueba. Los datos reales se conectarán con iDempiere."""

    def get_sql_context(self) -> str:
        return """
-- Tablas relevantes de iDempiere para Contabilidad:
-- Fact_Acct: Asientos contables (tabla principal)
-- C_ElementValue: Plan de cuentas
-- GL_Journal: Diario contable
-- GL_JournalLine: Líneas del diario
-- C_Period: Períodos contables
-- A_Asset: Activos fijos
-- A_Depreciation: Depreciaciones
-- C_Tax: Impuestos
"""

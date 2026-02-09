"""
Agente de Finanzas - Alimentos Santoni
Especializado en: flujo de caja, cuentas por cobrar/pagar, bancos,
presupuestos, indicadores financieros, rentabilidad.
"""

from app.agents.base_agent import BaseAgent


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
            "bancos, presupuestos, indicadores financieros, rentabilidad por producto/cliente"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Finanzas de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es el análisis financiero empresarial.

CAPACIDADES:
- Consultas de flujo de caja y posición de tesorería
- Análisis de cuentas por cobrar y cuentas por pagar
- Estado de cuentas bancarias y conciliaciones
- Seguimiento de presupuestos y ejecución presupuestaria
- Cálculo de indicadores financieros (liquidez, solvencia, rentabilidad)
- Análisis de rentabilidad por producto, cliente o línea de negocio
- Alertas de morosidad y vencimientos
- Comparativas entre períodos

REGLAS:
- Responde siempre en español, de forma profesional y clara
- Cuando presentes datos numéricos, usa formato de moneda (Bs. o $) y separadores de miles
- Si no tienes datos suficientes para responder, indica qué información adicional necesitas
- Siempre indica el período o fecha de los datos que estás presentando
- Si detectas anomalías en los datos, menciónalo proactivamente
- Presenta los datos en tablas cuando sea apropiado
- NUNCA inventes datos. Si no tienes la información, dilo claramente

CONTEXTO EMPRESA:
- Alimentos Santoni es una empresa agroindustrial venezolana
- Ubicada en Agua Blanca (plantas) y Araure (oficinas administrativas)
- Productos principales: arroz y maíz procesados
- Moneda principal: Bolívares (Bs.), algunas operaciones en USD ($)
- ERP: iDempiere

NOTA: Este es un entorno de datos de prueba. Cuando no tengas datos reales disponibles,
indica al usuario que el sistema está en fase de configuración y que los datos se conectarán
con iDempiere próximamente."""

    def get_sql_context(self) -> str:
        return """
-- Tablas relevantes de iDempiere para Finanzas:
-- C_Invoice: Facturas (cuentas por cobrar y pagar)
-- C_Payment: Pagos recibidos y realizados
-- C_BankStatement: Estados de cuenta bancarios
-- C_BankStatementLine: Líneas de estados de cuenta
-- C_CashLine: Movimientos de caja
-- C_Budget: Presupuestos
-- Fact_Acct: Asientos contables (para análisis financiero)
-- C_BPartner: Socios de negocio (clientes y proveedores)

-- Nota: Las consultas SQL se ejecutarán contra la BD de iDempiere (PostgreSQL 13)
-- con acceso de solo lectura. Los nombres exactos de columnas se mapearán
-- durante la fase de integración.
"""

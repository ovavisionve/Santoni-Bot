"""
Agente de Finanzas - Alimentos Santoni
Especializado en: flujo de caja, cuentas por cobrar/pagar, bancos,
presupuestos, indicadores financieros, rentabilidad.

Fuente de datos: c_bankaccount, c_payment, c_invoice en iDempiere (PostgreSQL 13).
"""

from app.agents.base_agent import BaseAgent
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
)
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

CONTEXTO iDEMPIERE:
- Cuentas bancarias: c_bankaccount (saldo actual, tipo, moneda) + c_bank
- Cobros recibidos: c_payment (isreceipt='Y', docstatus='CO') - 798,150 pagos
- Facturas por cobrar: c_invoice (issotrx='Y', ispaid='N') con c_paymentterm (días de crédito)
- Facturas por pagar: c_invoice (issotrx='N', ispaid='N')
- Clientes/proveedores: c_bpartner (26,070 registros)
- Monedas: VES (Bolívares, ID 205), USD (Dólares, ID 100)
- Organizaciones: INPROA SANTONI, AGROINPROA, AGROPECUARIA R.R., Agro Import, INVERSIONES AGA, InproMaiz, AGA AGRICOLA, Santoni Service
- Campos fiscales venezolanos: lve_controlnumber, withholdingamt, lve_factfiscal

REGLAS:
- Responde siempre en español, de forma profesional y clara
- Usa formato de moneda (Bs. o $) con separadores de miles (punto=miles, coma=decimal)
- Indica el período o fecha de los datos
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa claramente

FORMATOS DE FECHA SOPORTADOS:
- Rango con separadores: "01/01/2026 al 31/01/2026" o "01/01/26 al 31/01/26"
- Rango compacto: "01012026 al 31012026" o "010126 al 310126"
- Mes y año: "enero 2026"
- Solo año: "2026"

IMPORTANTE SOBRE PERÍODOS:
- Los datos corresponden al año actual por defecto, a menos que el usuario especifique otro año
- SIEMPRE indica claramente el período de los datos que estás presentando
- Si el usuario hace una pregunta amplia sin período, presenta datos del año actual y sugiere: "Si necesitas datos de otro período, indícame el año, mes o rango de fechas."
- Si el usuario especificó un rango de fechas, los datos ya vienen filtrados para ese rango exacto"""

    def get_sql_context(self) -> str:
        return """
Datos financieros de iDempiere:
- c_bankaccount: Cuentas bancarias (accountno, currentbalance, bankaccounttype, c_currency_id)
- c_bank: Bancos (name)
- c_payment: Pagos (isreceipt, datetrx, payamt, tendertype=X/C/K/D/T, docstatus)
- c_invoice: Facturas por cobrar (issotrx='Y', ispaid='N') y por pagar (issotrx='N', ispaid='N')
- c_paymentterm: Términos de pago (netdays)
- c_allocationline: Asignación de pagos a facturas
"""

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None, history: list[tuple[str, str]] | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)
        if date_from and date_to:
            mes = None

        label = build_period_label(date_from, date_to, mes, anio)
        summary = build_financial_summary(
            mes=mes, anio=anio, org_ids=org_ids,
            date_from=date_from, date_to=date_to,
        )
        sections.append(self._format_summary(summary, f"Resumen Financiero - {label}"))

        if any(w in msg for w in ["cobrar", "morosidad", "vencid", "atras"]):
            data = build_overdue_receivables(org_ids=org_ids)
            sections.append("## Cuentas por Cobrar Vencidas")
            sections.append(self._format_table(data))

        return "\n\n".join(sections) if sections else None

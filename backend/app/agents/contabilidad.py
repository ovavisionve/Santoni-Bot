"""
Agente de Contabilidad - Alimentos Santoni
Especializado en: balance general, estado de resultados, libros contables,
impuestos, activos fijos, consultas de cuentas específicas.

Fuente de datos: fact_acct y c_elementvalue en iDempiere (PostgreSQL 13).
"""

import re

from app.agents.base_agent import BaseAgent
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
)
from app.services.query_service import build_accounting_summary, build_account_detail


# Regex for account codes like 2.01.01.10, 1.01.02, etc.
_ACCOUNT_CODE_RE = re.compile(r'\b(\d\.\d{2}(?:\.\d{2}){1,3})\b')


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
            "libro diario/mayor, impuestos, activos fijos, cuentas específicas"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Contabilidad de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es la contabilidad empresarial y reportes financieros formales.

CAPACIDADES:
- Consultar saldos y movimientos de cuentas específicas por código (ej: 2.01.01.10)
- Balance general y análisis de estructura patrimonial
- Estado de resultados
- Libro diario y libro mayor
- Balanza de comprobación
- Comparativas entre períodos contables

CONTEXTO iDEMPIERE:
- Los datos provienen de fact_acct (7.7 millones de asientos contables) y c_elementvalue (plan de cuentas)
- Tipos de cuenta: A=Activo (1054 cuentas), E=Gasto (1626), L=Pasivo (494), O=Patrimonio (116), R=Ingreso (266)
- Monedas: VES (Bolívares, ID 205), USD (Dólares, ID 100)
- Organizaciones: INPROA SANTONI, AGROINPROA, AGROPECUARIA R.R., Agro Import, INVERSIONES AGA, InproMaiz, AGA AGRICOLA, Santoni Service

REGLAS:
- Responde siempre en español, de forma profesional y técnica
- Usa terminología contable venezolana estándar
- Indica el período contable de referencia
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si los datos dicen 0 movimientos, informa que no hay movimientos
- Si recibes un error indicando que la cuenta no fue encontrada, informa al usuario

FORMATOS DE FECHA SOPORTADOS:
- Rango con separadores: "01/01/2026 al 31/01/2026" o "01/01/26 al 31/01/26"
- Rango compacto: "01012026 al 31012026" o "010126 al 310126"
- Mes y año: "enero 2026"
- Solo año: "2026"

SOBRE SALDOS Y NATURALEZA DE CUENTAS:
- Cuentas de Activo (A) y Gasto (E): naturaleza DÉBITO → saldo = debe - haber
- Cuentas de Pasivo (L), Patrimonio (O) e Ingreso (R): naturaleza CRÉDITO → saldo = haber - debe
- Un saldo positivo indica el balance natural de la cuenta
- Los datos ya vienen calculados con la naturaleza correcta. Presenta los saldos como valores positivos.

IMPORTANTE SOBRE PERÍODOS:
- Los datos corresponden al año actual por defecto, a menos que el usuario especifique otro
- SIEMPRE indica claramente el período contable de los datos que estás presentando
- Usa formato venezolano: punto=miles, coma=decimal (ej: 1.234.567,89)
- Si el usuario especificó un rango de fechas, los datos ya vienen filtrados para ese rango exacto"""

    def get_sql_context(self) -> str:
        return """
Datos contables de iDempiere:
- fact_acct: Asientos contables (dateacct, account_id, amtacctdr, amtacctcr, ad_org_id)
- c_elementvalue: Plan de cuentas (value=código, name=nombre, accounttype=A/L/O/R/E)
- c_acctschema: Esquemas contables
- c_period: Períodos contables
Se pueden consultar cuentas específicas por código (ej: 2.01.01.10) con rango de fechas.
"""

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None) -> str | None:
        sections = []

        # Check if user is asking about a specific account code
        account_match = _ACCOUNT_CODE_RE.search(message)

        if account_match:
            account_code = account_match.group(1)

            # Try to extract date range first (dd/mm/yyyy al dd/mm/yyyy)
            date_from, date_to = extract_date_range(message)

            if date_from and date_to:
                detail = build_account_detail(
                    account_code=account_code,
                    date_from=date_from,
                    date_to=date_to,
                    org_ids=org_ids,
                )
            else:
                mes, anio = extract_month_year(message)
                detail = build_account_detail(
                    account_code=account_code,
                    mes=mes,
                    anio=anio,
                    org_ids=org_ids,
                )

            if "error" in detail:
                sections.append(f"**ERROR:** {detail['error']}")
            else:
                sections.append(self._format_summary(detail, f"Cuenta {account_code}"))
        else:
            # General accounting summary (no specific account)
            date_from, date_to = extract_date_range(message)
            if date_from and date_to:
                summary = build_accounting_summary(
                    date_from=date_from, date_to=date_to, org_ids=org_ids,
                )
                label = build_period_label(date_from=date_from, date_to=date_to)
            else:
                mes, anio = extract_month_year(message)
                summary = build_accounting_summary(mes=mes, anio=anio, org_ids=org_ids)
                label = build_period_label(mes=mes, anio=anio)
            sections.append(self._format_summary(summary, f"Resumen Contable - {label}"))

        return "\n\n".join(sections) if sections else None

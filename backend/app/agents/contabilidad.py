"""
Agente de Contabilidad - Alimentos Santoni
Especializado en: balance general, estado de resultados, libros contables,
impuestos, activos fijos, consultas de cuentas específicas.

Fuente de datos: fact_acct y c_elementvalue en iDempiere (PostgreSQL 13).
"""

import logging
import re

from app.agents.base_agent import BaseAgent
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
    detect_currency,
)
from app.services.query_service import build_accounting_summary, build_account_detail

logger = logging.getLogger("santonibot.agents.contabilidad")


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
- NUNCA inventes datos
- Si recibes un error indicando que la cuenta no fue encontrada, informa al usuario
- PROHIBIDO decir "no tengo acceso", "no puedo acceder", "no dispongo" o "no tengo acceso directo". TÚ TIENES ACCESO COMPLETO a la base de datos de Santoni y los datos se consultan automáticamente. Si no hay datos para una consulta, di "No se encontraron datos" y sugiere consultas alternativas.

IMPORTANTE - CASO DE 0 MOVIMIENTOS:
- Si los datos muestran movimientos=0, NO digas "no tengo información". La cuenta SÍ existe.
- Con 0 movimientos, SIEMPRE muestra: saldo_inicial, saldo_final (serán iguales), y explica que no hubo movimientos en el período.
- Ejemplo: "La cuenta X no registró movimientos en el período consultado. El saldo al inicio y cierre del período es de Bs. 1.234,56."
- Si recibes un ERROR indicando que la cuenta no existe, informa que el código de cuenta no fue encontrado en el sistema.

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

    def get_capabilities(self) -> str:
        return (
            "CAPACIDADES REALES (lo que SÍ puedo consultar en la base de datos):\n"
            "✅ Resumen contable: totales por tipo de cuenta (Activo, Pasivo, Patrimonio, Ingreso, Gasto)\n"
            "✅ Detalle de cuenta específica por código (ej: 2.01.01.10) con saldo inicial, movimientos y saldo final\n"
            "✅ Desglose diario de movimientos de una cuenta\n"
            "✅ Top cuentas por volumen de movimiento\n"
            "\n❌ NO puedo consultar: activos fijos, depreciación o reportes de impuestos separados. "
            "Redirige al usuario al departamento correspondiente."
        )

    def get_sql_context(self) -> str:
        return """
Datos contables de iDempiere:
- fact_acct: Asientos contables (dateacct, account_id, amtacctdr, amtacctcr, ad_org_id)
- c_elementvalue: Plan de cuentas (value=código, name=nombre, accounttype=A/L/O/R/E)
- c_acctschema: Esquemas contables
- c_period: Períodos contables
Se pueden consultar cuentas específicas por código (ej: 2.01.01.10) con rango de fechas.
"""

    @staticmethod
    def _format_zero_movement(detail: dict) -> str:
        """Build an explicit message for accounts with 0 movements in the period.

        This bypasses _format_summary to prevent the LLM from misinterpreting
        0 movements as 'no information available'.
        """
        code = detail.get("cuenta_codigo", "")
        name = detail.get("cuenta_nombre", "")
        acct_type = detail.get("tipo_cuenta", "")
        nature = detail.get("naturaleza", "")
        period = detail.get("periodo", "")
        currency = detail.get("moneda", "VES")
        saldo_ini = detail.get("saldo_inicial", 0.0)
        saldo_fin = detail.get("saldo_final", 0.0)

        lines = [
            f"## Cuenta {code} — {name}",
            f"- Tipo de cuenta: {acct_type}",
            f"- Naturaleza: {nature}",
            f"- Moneda: {currency}",
            f"- Período consultado: {period}",
            "",
            "**La cuenta NO registró movimientos en este período.**",
            "",
            f"| Concepto | Monto ({currency}) |",
            "|---|---:|",
            f"| Saldo Inicial | {saldo_ini:,.2f} |",
            f"| Debe en el período | 0,00 |",
            f"| Haber en el período | 0,00 |",
            f"| **Saldo Final** | **{saldo_fin:,.2f}** |",
            "",
            "El saldo se mantiene sin cambios al no haber movimientos en el período consultado.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _extract_account_from_history(
        history: list[tuple[str, str]],
    ) -> str | None:
        """Try to find an account code (e.g. 2.01.01.10) from recent user messages."""
        if not history:
            return None
        for role, content in reversed(history):
            if role == "user":
                match = _ACCOUNT_CODE_RE.search(content)
                if match:
                    return match.group(1)
        return None

    @staticmethod
    def _extract_dates_from_history(
        history: list[tuple[str, str]],
    ) -> tuple[str | None, str | None, int | None, int | None]:
        """Extract temporal context from recent history for follow-ups."""
        for role, content in reversed(history):
            if role != "user":
                continue
            df, dt = extract_date_range(content)
            if df:
                m, a = extract_month_year(content)
                return df, dt, m, a
            m, a = extract_month_year(content)
            if m is not None:
                return None, None, m, a
        return None, None, None, None

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None, history: list[tuple[str, str]] | None = None) -> str | None:
        sections = []

        # Detect currency from message (or carry over from history)
        currency_ids = detect_currency(message)
        if not currency_ids and history:
            for role, content in reversed(history):
                if role == "user":
                    c = detect_currency(content)
                    if c:
                        currency_ids = c
                        break

        # Check if user is asking about a specific account code
        account_match = _ACCOUNT_CODE_RE.search(message)
        account_code = account_match.group(1) if account_match else None

        # Follow-up: if no account code in current message, check history
        if not account_code and history:
            account_code = self._extract_account_from_history(history)

        try:
            if account_code:
                # Try to extract date range first (dd/mm/yyyy al dd/mm/yyyy)
                date_from, date_to = extract_date_range(message)
                mes, anio = extract_month_year(message) if not (date_from and date_to) else (None, None)

                # Inherit temporal context from history for follow-ups
                if not date_from and not date_to and not mes and history:
                    h_df, h_dt, h_mes, h_anio = self._extract_dates_from_history(history)
                    if h_df:
                        date_from, date_to = h_df, h_dt
                    elif h_mes is not None:
                        mes, anio = h_mes, h_anio

                if date_from and date_to:
                    detail = build_account_detail(
                        account_code=account_code,
                        date_from=date_from,
                        date_to=date_to,
                        org_ids=org_ids,
                        currency_ids=currency_ids,
                    )
                else:
                    if mes is None:
                        mes, anio = extract_month_year(message)
                    detail = build_account_detail(
                        account_code=account_code,
                        mes=mes,
                        anio=anio,
                        org_ids=org_ids,
                        currency_ids=currency_ids,
                    )

                if "error" in detail:
                    sections.append(f"**ERROR:** {detail['error']}")
                else:
                    if detail.get("movimientos", 0) == 0:
                        sections.append(self._format_zero_movement(detail))
                    else:
                        sections.append(self._format_summary(detail, f"Cuenta {account_code}"))
            else:
                # General accounting summary (no specific account)
                date_from, date_to = extract_date_range(message)
                mes, anio = None, None
                if date_from and date_to:
                    summary = build_accounting_summary(
                        date_from=date_from, date_to=date_to, org_ids=org_ids,
                    )
                    label = build_period_label(date_from=date_from, date_to=date_to)
                else:
                    mes, anio = extract_month_year(message)
                    # Inherit temporal context from history for follow-ups
                    if not mes and history:
                        h_df, h_dt, h_mes, h_anio = self._extract_dates_from_history(history)
                        if h_df:
                            date_from, date_to = h_df, h_dt
                        elif h_mes is not None:
                            mes, anio = h_mes, h_anio
                    if date_from and date_to:
                        summary = build_accounting_summary(
                            date_from=date_from, date_to=date_to, org_ids=org_ids,
                        )
                        label = build_period_label(date_from=date_from, date_to=date_to)
                    else:
                        summary = build_accounting_summary(mes=mes, anio=anio, org_ids=org_ids)
                        label = build_period_label(mes=mes, anio=anio)
                sections.append(self._format_summary(summary, f"Resumen Contable - {label}"))

        except Exception as exc:
            logger.error("Error consultando datos contables: %s: %s", type(exc).__name__, exc, exc_info=True)
            sections.append(
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Intenta de nuevo en unos momentos."
            )

        return "\n\n".join(sections) if sections else None

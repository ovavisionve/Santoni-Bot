"""
Agente de Finanzas - Alimentos Santoni
Especializado en: flujo de caja, cuentas por cobrar/pagar, bancos,
presupuestos, indicadores financieros, rentabilidad.

Fuente de datos: c_bankaccount, c_payment, c_invoice en iDempiere (PostgreSQL 13).
"""

import logging

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

logger = logging.getLogger("santonibot.agents.finanzas")


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
- Cobros recibidos: c_payment (isreceipt='Y', docstatus IN ('CO','CL')). CO=completado, CL=cerrado.
- Facturas por cobrar: c_invoice (issotrx='Y', ispaid='N') con c_paymentterm (días de crédito)
- Facturas por pagar: c_invoice (issotrx='N', ispaid='N')
- Clientes/proveedores: c_bpartner
- Monedas: VES (Bolívares, ID 205), USD (Dólares, ID 100)
- Organizaciones: INPROA SANTONI, AGROINPROA, AGROPECUARIA R.R., Agro Import, INVERSIONES AGA, InproMaiz, AGA AGRICOLA, Santoni Service
- Campos fiscales venezolanos: lve_controlnumber, withholdingamt, lve_factfiscal

IMPORTANTE SOBRE SALDOS BANCARIOS:
- Los saldos bancarios se presentan SEPARADOS por moneda (VES y USD)
- NUNCA sumes saldos de diferentes monedas entre sí
- Presenta los totales por moneda: "Total en Bs.: X" y "Total en $: Y"
- Cada cuenta muestra: banco, número de cuenta, tipo, organización y saldo
- Si el usuario pregunta por saldos, presenta las tablas por moneda de forma clara

IMPORTANTE SOBRE CUENTAS POR COBRAR Y PAGAR:
- Las cuentas por cobrar y por pagar están SEPARADAS por moneda (Bs. y USD)
- NUNCA sumes montos de diferentes monedas
- Presenta cada moneda por separado: "Por cobrar en Bs.: X" y "Por cobrar en $: Y"
- Las facturas vencidas también se presentan separadas por moneda
- Si el usuario pregunta cuánto le deben, presenta por moneda de forma clara

REGLAS:
- Responde siempre en español, de forma profesional y clara
- Usa formato de moneda (Bs. o $) con separadores de miles (punto=miles, coma=decimal)
- Indica el período o fecha de los datos
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa claramente
- PROHIBIDO decir "no tengo acceso", "no puedo acceder", "no dispongo" o "no tengo acceso directo". TÚ TIENES ACCESO COMPLETO a la base de datos de Santoni y los datos se consultan automáticamente. Si no hay datos para una consulta específica (ej: préstamos, flujo de caja proyectado), di "No se encontraron datos para esa consulta" y sugiere consultas alternativas que SÍ puedes hacer.
- Si la pregunta es ambigua, personal o usa palabras como "mi", "yo", "me" (ej: "mi cuenta", "mis pagos"), NO adivines. Pide al usuario que reformule especificando: la organización, cuenta, período u otros datos necesarios.

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

    def get_capabilities(self) -> str:
        return (
            "CAPACIDADES REALES (lo que SÍ puedo consultar en la base de datos):\n"
            "✅ Saldos bancarios actuales por banco, cuenta, moneda y organización\n"
            "✅ Cuentas por cobrar pendientes (facturas de venta no pagadas) con días de atraso\n"
            "✅ Cuentas por pagar pendientes (facturas de compra no pagadas)\n"
            "✅ Resumen financiero general (bancos + CxC + CxP)\n"
            "\n❌ NO puedo consultar: presupuestos, flujo de caja proyectado o indicadores financieros calculados. "
            "Redirige al usuario al departamento correspondiente."
        )

    def get_sql_context(self) -> str:
        return """
Datos financieros de iDempiere:
- c_bankaccount: Cuentas bancarias (accountno, currentbalance, bankaccounttype, c_currency_id)
- c_bank: Bancos (name)
- c_payment: Pagos (isreceipt, datetrx, payamt, tendertype: W=Transferencia, X=Efectivo, K=Cheque, C=Tarjeta Crédito, B=Tarjeta Débito, S=Transferencia Empresas, Z=Dólar Transferencia, Y=Dólar Efectivo, docstatus)
- c_invoice: Facturas por cobrar (issotrx='Y', ispaid='N') y por pagar (issotrx='N', ispaid='N')
- c_paymentterm: Términos de pago (netdays)
- c_allocationline: Asignación de pagos a facturas
"""

    _RECEIVABLES_KEYWORDS = ["cobrar", "morosidad", "vencid", "atras"]

    # -- helpers for currency-aware bank formatting --
    _BANK_COLUMNS = ["banco", "numero_cuenta", "tipo", "organizacion", "saldo"]

    @staticmethod
    def _format_bank_section(title: str, accounts: list[dict], currency_symbol: str) -> str:
        """Format a group of bank accounts for a single currency."""
        if not accounts:
            return ""
        lines = [f"### {title}"]
        lines.append(BaseAgent._format_table(accounts, columns=FinanzasAgent._BANK_COLUMNS))
        total = sum(a["saldo"] for a in accounts)
        lines.append(f"\n**Total {currency_symbol}: {total:,.2f}**")
        return "\n".join(lines)

    def _format_financial_summary(self, summary: dict, label: str) -> str:
        """Custom formatting for the financial summary with currency separation."""
        lines = [f"## Resumen Financiero - {label}"]

        # --- Bank balances separated by currency ---
        lines.append("\n## Saldos Bancarios")

        ves_section = self._format_bank_section(
            "Cuentas en Bolívares (VES)",
            summary.get("saldos_bancarios_ves", []),
            "Bs.",
        )
        if ves_section:
            lines.append(ves_section)

        usd_section = self._format_bank_section(
            "Cuentas en Dólares (USD)",
            summary.get("saldos_bancarios_usd", []),
            "$",
        )
        if usd_section:
            lines.append(usd_section)

        other_section = self._format_bank_section(
            "Cuentas en Otras Monedas",
            summary.get("saldos_bancarios_otras", []),
            "",
        )
        if other_section:
            lines.append(other_section)

        # Totals per currency summary
        totals = summary.get("totales_por_moneda", {})
        if totals:
            lines.append("\n### Resumen de Saldos por Moneda")
            for cur, total in sorted(totals.items()):
                symbol = "Bs." if cur == "VES" else "$" if cur == "USD" else cur
                lines.append(f"- **{cur}**: {symbol} {total:,.2f}")

        # --- Receivables (separated by currency) ---
        ar = summary.get("cuentas_por_cobrar", {})
        if ar:
            lines.append("\n### Cuentas Por Cobrar")
            lines.append(f"- Facturas pendientes: {ar.get('facturas_pendientes', 0)}")
            ar_by_cur = ar.get("por_moneda", [])
            if ar_by_cur:
                for item in ar_by_cur:
                    sym = "Bs." if item["moneda"] == "Bs." else "$" if item["moneda"] == "USD" else item["moneda"]
                    lines.append(f"  - **{item['moneda']}**: {item['facturas']} facturas por {sym} {item['total']:,.2f}")
            else:
                lines.append(f"- Total por cobrar: {ar.get('total_por_cobrar', 0):,.2f}")
            if ar.get("facturas_vencidas"):
                lines.append(f"- Facturas vencidas: {ar['facturas_vencidas']}")
                vencidas_cur = ar.get("vencidas_por_moneda", [])
                if vencidas_cur:
                    for item in vencidas_cur:
                        sym = "Bs." if item["moneda"] == "Bs." else "$" if item["moneda"] == "USD" else item["moneda"]
                        lines.append(f"  - **{item['moneda']}**: {item['facturas']} vencidas por {sym} {item['total']:,.2f}")
                else:
                    lines.append(f"- Total vencido: {ar.get('total_vencido', 0):,.2f}")

        # --- Payables (separated by currency) ---
        ap = summary.get("cuentas_por_pagar", {})
        if ap:
            lines.append("\n### Cuentas Por Pagar")
            lines.append(f"- Facturas pendientes: {ap.get('facturas_pendientes', 0)}")
            ap_by_cur = ap.get("por_moneda", [])
            if ap_by_cur:
                for item in ap_by_cur:
                    sym = "Bs." if item["moneda"] == "Bs." else "$" if item["moneda"] == "USD" else item["moneda"]
                    lines.append(f"  - **{item['moneda']}**: {item['facturas']} facturas por {sym} {item['total']:,.2f}")
            else:
                lines.append(f"- Total por pagar: {ap.get('total_por_pagar', 0):,.2f}")
            if ap.get("facturas_vencidas"):
                lines.append(f"- Facturas vencidas: {ap['facturas_vencidas']}")
                vencidas_cur = ap.get("vencidas_por_moneda", [])
                if vencidas_cur:
                    for item in vencidas_cur:
                        sym = "Bs." if item["moneda"] == "Bs." else "$" if item["moneda"] == "USD" else item["moneda"]
                        lines.append(f"  - **{item['moneda']}**: {item['facturas']} vencidas por {sym} {item['total']:,.2f}")
                else:
                    lines.append(f"- Total vencido: {ap.get('total_vencido', 0):,.2f}")
            top_proveedores = ap.get("top_proveedores_vencidos", [])
            if top_proveedores:
                lines.append("\n### Top Proveedores con Mayor Deuda Vencida")
                lines.append("| # | Proveedor | Moneda | Facturas | Total Adeudado |")
                lines.append("|---|-----------|--------|----------|----------------|")
                for i, p in enumerate(top_proveedores, 1):
                    sym = "Bs." if p["moneda"] == "Bs." else "$" if p["moneda"] == "USD" else p["moneda"]
                    lines.append(f"| {i} | {p['proveedor']} | {p['moneda']} | {p['facturas']} | {sym} {p['total_adeudado']:,.2f} |")

        # --- Top morosos (receivables) ---
        top_morosos = ar.get("top_clientes_morosos", []) if ar else []
        if top_morosos:
            lines.append("\n### Top Clientes Morosos (Mayor Deuda Vencida)")
            lines.append("| # | Cliente | Moneda | Facturas | Total Adeudado |")
            lines.append("|---|---------|--------|----------|----------------|")
            for i, c in enumerate(top_morosos, 1):
                sym = "Bs." if c["moneda"] == "Bs." else "$" if c["moneda"] == "USD" else c["moneda"]
                lines.append(f"| {i} | {c['cliente']} | {c['moneda']} | {c['facturas']} | {sym} {c['total_adeudado']:,.2f} |")

        return "\n".join(lines)

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None, history: list[tuple[str, str]] | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)
        if date_from and date_to:
            mes = None
            anio = None

        # Inherit temporal context from history for follow-ups
        if not date_from and not date_to and not mes and history:
            for role, content in reversed(history):
                if role != "user":
                    continue
                df, dt = extract_date_range(content)
                if df and dt:
                    date_from, date_to = df, dt
                    break
                m, a = extract_month_year(content)
                if m:
                    mes, anio = m, a
                    break

        label = build_period_label(date_from, date_to, mes, anio)

        try:
            summary = build_financial_summary(
                mes=mes, anio=anio, org_ids=org_ids,
                date_from=date_from, date_to=date_to,
            )
            sections.append(self._format_financial_summary(summary, label))

            include_receivables = any(w in msg for w in self._RECEIVABLES_KEYWORDS)
            # Follow-up: carry over receivables section from history
            if not include_receivables and history:
                for role, content in reversed(history):
                    if role == "user" and any(
                        w in content.lower() for w in self._RECEIVABLES_KEYWORDS
                    ):
                        include_receivables = True
                        break

            if include_receivables:
                data = build_overdue_receivables(org_ids=org_ids)
                sections.append("## Cuentas por Cobrar Vencidas")
                sections.append(self._format_table(data))

        except Exception as exc:
            logger.error("Error consultando datos financieros: %s: %s", type(exc).__name__, exc, exc_info=True)
            sections.append(
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Intenta de nuevo en unos momentos."
            )

        return "\n\n".join(sections) if sections else None

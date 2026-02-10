"""
Agente de Finanzas - Alimentos Santoni
Especializado en: flujo de caja, cuentas por cobrar/pagar, bancos,
presupuestos, indicadores financieros, rentabilidad.
"""

import re

from app.agents.base_agent import BaseAgent
from app.services.query_service import (
    build_financial_summary,
    build_overdue_receivables,
    execute_demo_query,
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

REGLAS:
- Responde siempre en español, de forma profesional y clara
- Usa formato de moneda (Bs. o $) y separadores de miles
- Indica el período o fecha de los datos
- Los datos que recibes son REALES de la base de datos de Santoni"""

    def get_sql_context(self) -> str:
        return """
Tablas: demo_cuentas_bancarias, demo_movimientos_bancarios, demo_cuentas_por_pagar
"""

    def fetch_data(self, message: str) -> str | None:
        msg = message.lower()
        sections = []

        anio = 2025
        year_match = re.search(r'20\d{2}', message)
        if year_match:
            anio = int(year_match.group())

        mes = None
        meses_map = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
            "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
            "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
        }
        for nombre, num in meses_map.items():
            if nombre in msg:
                mes = num
                break

        summary = build_financial_summary(mes=mes, anio=anio)
        sections.append(self._format_summary(summary, f"Resumen Financiero {anio}"))

        if any(w in msg for w in ["banco", "cuenta", "saldo", "bancari"]):
            try:
                banks = execute_demo_query(
                    "SELECT banco, numero_cuenta, tipo, moneda, saldo, fecha_saldo "
                    "FROM demo_cuentas_bancarias ORDER BY saldo DESC"
                )
                sections.append("## Cuentas Bancarias")
                sections.append(self._format_table(banks))
            except Exception:
                pass

        if any(w in msg for w in ["pagar", "proveedor", "deuda", "pasivo"]):
            try:
                payables = execute_demo_query(
                    "SELECT proveedor, numero_factura, fecha_vencimiento, "
                    "monto_original, monto_pendiente, estado "
                    "FROM demo_cuentas_por_pagar WHERE monto_pendiente > 0 "
                    "ORDER BY fecha_vencimiento"
                )
                sections.append("## Cuentas por Pagar Pendientes")
                sections.append(self._format_table(payables))
            except Exception:
                pass

        if any(w in msg for w in ["cobrar", "morosidad", "vencid", "atras"]):
            data = build_overdue_receivables()
            sections.append("## Cuentas por Cobrar Vencidas")
            sections.append(self._format_table(data))

        return "\n\n".join(sections) if sections else None

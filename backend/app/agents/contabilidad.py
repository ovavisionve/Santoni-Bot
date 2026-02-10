"""
Agente de Contabilidad - Alimentos Santoni
Especializado en: balance general, estado de resultados, libros contables,
impuestos, activos fijos.
"""

import re

from app.agents.base_agent import BaseAgent
from app.services.query_service import execute_demo_query


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
- Estado de resultados
- Libro diario y libro mayor
- Balanza de comprobación
- Comparativas entre períodos contables

REGLAS:
- Responde siempre en español, de forma profesional y técnica
- Usa terminología contable venezolana estándar
- Indica el período contable de referencia
- Los datos que recibes son REALES de la base de datos de Santoni"""

    def get_sql_context(self) -> str:
        return """
Tablas: demo_asientos_contables, demo_balance_general
"""

    def fetch_data(self, message: str) -> str | None:
        msg = message.lower()
        sections = []

        periodo = None
        meses_map = {
            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
            "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
            "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
        }
        for nombre, num in meses_map.items():
            if nombre in msg:
                periodo = f"2025-{num}"
                break

        if any(w in msg for w in ["balance", "patrimon", "activo", "pasivo"]):
            try:
                p = periodo or "2025-06"
                data = execute_demo_query(
                    "SELECT tipo_cuenta, grupo, cuenta, saldo "
                    "FROM demo_balance_general WHERE periodo = :periodo "
                    "ORDER BY tipo_cuenta, grupo, cuenta",
                    {"periodo": p},
                )
                sections.append(f"## Balance General - Período {p}")
                for tipo in ["activo", "pasivo", "patrimonio"]:
                    items = [d for d in data if d["tipo_cuenta"] == tipo]
                    if items:
                        total = sum(d["saldo"] for d in items)
                        sections.append(f"\n### {tipo.upper()} (Total: Bs. {total:,.2f})")
                        sections.append(self._format_table(items, ["grupo", "cuenta", "saldo"]))
            except Exception:
                pass

        if any(w in msg for w in ["diario", "asiento", "mayor", "balanza"]):
            try:
                if periodo:
                    data = execute_demo_query(
                        "SELECT numero_asiento, fecha, cuenta_contable, nombre_cuenta, "
                        "descripcion, debe, haber FROM demo_asientos_contables "
                        "WHERE periodo = :periodo ORDER BY fecha, numero_asiento",
                        {"periodo": periodo},
                    )
                else:
                    data = execute_demo_query(
                        "SELECT numero_asiento, fecha, cuenta_contable, nombre_cuenta, "
                        "descripcion, debe, haber FROM demo_asientos_contables "
                        "ORDER BY fecha DESC LIMIT 50"
                    )
                total_debe = sum(d["debe"] for d in data)
                total_haber = sum(d["haber"] for d in data)
                sections.append(f"## Asientos Contables ({len(data)} registros)")
                sections.append(f"Total Debe: Bs. {total_debe:,.2f} | Total Haber: Bs. {total_haber:,.2f}")
                sections.append(self._format_table(data))
            except Exception:
                pass

        if not sections:
            try:
                data = execute_demo_query(
                    "SELECT tipo_cuenta, SUM(saldo) as total "
                    "FROM demo_balance_general WHERE periodo = '2025-06' "
                    "GROUP BY tipo_cuenta ORDER BY tipo_cuenta"
                )
                sections.append("## Resumen Balance General - Junio 2025")
                sections.append(self._format_table(data))
            except Exception:
                pass

        return "\n\n".join(sections) if sections else None

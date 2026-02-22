"""
Agente de Producción - Alimentos Santoni
Especializado en: producción diaria, órdenes de producción, eficiencia (OEE),
desperdicios, mantenimientos.
"""

import re
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.query_service import build_production_summary, execute_demo_query


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

REGLAS:
- Responde siempre en español, de forma técnica pero comprensible
- Usa unidades métricas (kg, toneladas)
- Presenta porcentajes de eficiencia y desperdicio
- Los datos que recibes son REALES de la base de datos de Santoni

CONTEXTO:
- 2 plantas en Agua Blanca, Estado Portuguesa
- Productos: Arroz Santoni Premium, Harina de Maíz Santoni
- Turnos rotativos en planta

IMPORTANTE SOBRE PERÍODOS:
- Los datos que recibes corresponden al año actual por defecto, a menos que el usuario especifique otro año
- SIEMPRE indica claramente el período de los datos que estás presentando
- Si el usuario hace una pregunta amplia sin especificar período, presenta los datos del año actual y al final sugiere: "Si necesitas datos de otro período, indícame el año o mes que deseas consultar."
- Si el usuario menciona un año específico, los datos ya vendrán filtrados para ese año"""

    def get_sql_context(self) -> str:
        return """
Tablas: demo_produccion_diaria, demo_ordenes_produccion
"""

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None) -> str | None:
        msg = message.lower()
        sections = []

        anio = datetime.now().year
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

        label = f"Año {anio}" if anio else "Todos los años"
        summary = build_production_summary(mes=mes, anio=anio, org_ids=org_ids)
        sections.append(self._format_summary(summary, f"Resumen de Producción - {label}"))

        if any(w in msg for w in ["orden", "pedido", "planific"]):
            try:
                data = execute_demo_query(
                    "SELECT numero_orden, fecha, producto, planta, "
                    "cantidad_planificada, cantidad_producida, estado "
                    "FROM demo_ordenes_produccion ORDER BY fecha DESC"
                )
                sections.append(f"## Órdenes de Producción ({len(data)} total)")
                sections.append(self._format_table(data))
                completadas = sum(1 for d in data if d["estado"] == "completada")
                sections.append(
                    f"\nTasa de completación: {completadas}/{len(data)} "
                    f"({completadas/len(data)*100:.1f}%)" if data else ""
                )
            except Exception:
                pass

        if any(w in msg for w in ["desperdicio", "merma", "pérdida", "scrap"]):
            try:
                data = execute_demo_query(
                    "SELECT planta, linea, producto, "
                    "SUM(cantidad_kg) as producido_kg, "
                    "SUM(desperdicio_kg) as desperdicio_kg, "
                    "ROUND(SUM(desperdicio_kg)/NULLIF(SUM(cantidad_kg),0)*100, 2) as porcentaje "
                    "FROM demo_produccion_diaria "
                    "GROUP BY planta, linea, producto ORDER BY porcentaje DESC"
                )
                sections.append("## Análisis de Desperdicios")
                sections.append(self._format_table(data))
            except Exception:
                pass

        if any(w in msg for w in ["eficiencia", "oee", "rendimiento", "parada"]):
            try:
                data = execute_demo_query(
                    "SELECT planta, linea, turno, "
                    "SUM(horas_operacion) as hrs_operacion, "
                    "SUM(horas_parada) as hrs_parada, "
                    "ROUND(SUM(horas_operacion)/NULLIF(SUM(horas_operacion)+SUM(horas_parada),0)*100, 1) as oee "
                    "FROM demo_produccion_diaria "
                    "GROUP BY planta, linea, turno ORDER BY oee DESC"
                )
                sections.append("## Eficiencia por Planta/Línea/Turno")
                sections.append(self._format_table(data))
            except Exception:
                pass

        return "\n\n".join(sections) if sections else None

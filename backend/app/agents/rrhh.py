"""
Agente de Recursos Humanos - Alimentos Santoni
Especializado en: nómina, vacaciones, asistencia, datos de empleados.
"""

from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.services.query_service import build_employee_summary, execute_demo_query


class RRHHAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "rrhh"

    @property
    def display_name(self) -> str:
        return "Recursos Humanos"

    @property
    def department(self) -> str:
        return "rrhh"

    @property
    def description(self) -> str:
        return (
            "Consultas de RRHH: nómina, vacaciones, asistencia, "
            "datos de empleados, evaluaciones"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Recursos Humanos de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es la gestión del talento humano y consultas de nómina.

REGLAS:
- Responde siempre en español, de forma profesional
- Los datos de RRHH son ALTAMENTE SENSIBLES
- Presenta montos salariales en Bolívares (Bs.)
- Los datos que recibes son REALES de la base de datos de Santoni

CONTEXTO:
- Ubicaciones: Agua Blanca (2 plantas), Araure (oficinas administrativas)
- Turnos: Oficina diurno, Planta rotativo
- Horario oficina: 7:30am a 5pm

IMPORTANTE SOBRE PERÍODOS:
- SIEMPRE indica claramente el período de los datos que estás presentando
- Si el usuario hace una pregunta amplia sin especificar período, presenta los datos disponibles y al final sugiere: "Si necesitas datos de un período específico, indícame el mes o año que deseas consultar."
- Si el usuario menciona un período específico, los datos ya vendrán filtrados"""

    def get_sql_context(self) -> str:
        return """
Tablas: demo_empleados, demo_nominas, demo_asistencias
"""

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None) -> str | None:
        msg = message.lower()
        sections = []

        summary = build_employee_summary(org_ids=org_ids)
        sections.append(self._format_summary(summary, "Resumen de Personal"))

        if any(w in msg for w in ["empleado", "personal", "lista", "cuántos", "cuantos"]):
            try:
                data = execute_demo_query(
                    "SELECT nombre, cargo, departamento, ubicacion, turno, activo "
                    "FROM demo_empleados ORDER BY departamento, nombre"
                )
                sections.append(f"## Lista de Empleados ({len(data)} total)")
                sections.append(self._format_table(data))
            except Exception:
                pass

        if any(w in msg for w in ["nómina", "nomina", "salario", "sueldo", "pago"]):
            try:
                periodo = None
                anio = datetime.now().year
                meses_map = {
                    "enero": f"{anio}-01", "febrero": f"{anio}-02", "marzo": f"{anio}-03",
                    "abril": f"{anio}-04", "mayo": f"{anio}-05", "junio": f"{anio}-06",
                    "julio": f"{anio}-07", "agosto": f"{anio}-08", "septiembre": f"{anio}-09",
                    "octubre": f"{anio}-10", "noviembre": f"{anio}-11", "diciembre": f"{anio}-12",
                }
                for nombre, per in meses_map.items():
                    if nombre in msg:
                        periodo = per
                        break

                if periodo:
                    data = execute_demo_query(
                        "SELECT e.nombre, e.cargo, e.departamento, n.salario_basico, "
                        "n.asignaciones, n.deducciones, n.neto_pagar "
                        "FROM demo_nominas n JOIN demo_empleados e ON n.empleado_id = e.id "
                        "WHERE n.periodo = :periodo ORDER BY n.neto_pagar DESC",
                        {"periodo": periodo},
                    )
                    total = sum(d["neto_pagar"] for d in data)
                    sections.append(f"## Nómina {periodo} (Total: Bs. {total:,.2f})")
                    sections.append(self._format_table(data))
                else:
                    data = execute_demo_query(
                        "SELECT periodo, COUNT(*) as empleados, "
                        "SUM(neto_pagar) as total_nomina, AVG(neto_pagar) as promedio "
                        "FROM demo_nominas GROUP BY periodo ORDER BY periodo"
                    )
                    sections.append("## Resumen de Nóminas por Período")
                    sections.append(self._format_table(data))
            except Exception:
                pass

        if any(w in msg for w in ["asistencia", "falta", "ausent", "permiso", "inasist"]):
            try:
                data = execute_demo_query(
                    "SELECT tipo, COUNT(*) as cantidad "
                    "FROM demo_asistencias GROUP BY tipo ORDER BY cantidad DESC"
                )
                sections.append("## Resumen de Asistencia (Enero 2025)")
                sections.append(self._format_table(data))

                faltas = execute_demo_query(
                    "SELECT e.nombre, e.departamento, COUNT(*) as faltas "
                    "FROM demo_asistencias a JOIN demo_empleados e ON a.empleado_id = e.id "
                    "WHERE a.tipo = 'falta' GROUP BY e.nombre, e.departamento "
                    "ORDER BY faltas DESC LIMIT 10"
                )
                if faltas:
                    sections.append("## Empleados con Más Faltas")
                    sections.append(self._format_table(faltas))
            except Exception:
                pass

        return "\n\n".join(sections) if sections else None

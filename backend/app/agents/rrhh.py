"""
Agente de Recursos Humanos - Alimentos Santoni
Especializado en: nómina, vacaciones, asistencia, datos de empleados.

Fuente de datos: hr_employee, hr_process, hr_movement, hr_concept,
hr_payroll + c_bpartner en iDempiere (PostgreSQL 13).
"""

from app.agents.base_agent import BaseAgent
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
)
from app.services.query_service import (
    build_employee_summary,
    build_employee_list,
    build_birthday_list,
    build_payroll_summary,
    build_attendance_summary,
    build_turnover_summary,
)


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

CAPACIDADES:
- Listado y resumen de empleados por organización/departamento
- Cumpleañeros del mes (fecha de cumpleaños de empleados)
- Consultas de nómina por período (quincenas, mensuales)
- Conceptos de nómina: salario base, bonos, deducciones, neto a pagar
- Historial de procesos de nómina
- Indicadores de ausentismo: conceptos de ausencia en nómina (inasistencia, falta, permiso, reposo, incapacidad, licencia)
- NOTA AUSENTISMO: Los datos de ausentismo provienen de conceptos de nómina y se expresan en cantidad de OCURRENCIAS y MONTO en Bs. No se dispone de horas-hombre en el sistema de nómina de iDempiere.

CONTEXTO iDEMPIERE:
- Empleados: hr_employee (vinculado a c_bpartner via c_bpartner_id, con hr_department_id y hr_job_id)
- Departamentos: hr_department (name)
- Cargos: hr_job (name)
- Procesos de nómina: hr_process (documentno, dateacct, c_period_id, docstatus)
- Movimientos de nómina: hr_movement (hr_process_id, hr_employee_id, hr_concept_id, amount, qty)
- Conceptos: hr_concept (value, name, columntype, type)
- Nóminas definidas: hr_payroll (name, hr_payroll_id)
- Organizaciones: INPROA SANTONI (444 empleados), InproMaiz (206), Santoni Service (134), AGROPECUARIA R.R. (124), AGA AGRICOLA (91), AGROINPROA (38), INVERSIONES AGA (4)
- NOTA: Los conteos de empleados usan DISTINCT por c_bpartner_id ya que hr_employee tiene múltiples registros por persona

REGLAS:
- Responde siempre en español, de forma profesional
- Los datos de RRHH son ALTAMENTE SENSIBLES - no divulgar salarios individuales sin autorización
- Presenta montos salariales en Bolívares (Bs.) con formato venezolano (punto=miles, coma=decimal)
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa claramente

CONTEXTO ORGANIZACIONAL:
- Ubicaciones: Agua Blanca (2 plantas), Araure (oficinas administrativas)
- Turnos: Oficina diurno, Planta rotativo
- Horario oficina: 7:30am a 5pm

FORMATOS DE FECHA SOPORTADOS:
- Rango con separadores: "01/01/2026 al 31/01/2026" o "01/01/26 al 31/01/26"
- Rango compacto: "01012026 al 31012026" o "010126 al 310126"
- Mes y año: "enero 2026"
- Solo año: "2026"

IMPORTANTE SOBRE PERÍODOS:
- SIEMPRE indica claramente el período de los datos que estás presentando
- Si el usuario hace una pregunta amplia sin período, presenta datos disponibles y sugiere: "Si necesitas datos de un período específico, indícame el mes, año o rango de fechas."
- Si el usuario especificó un rango de fechas, los datos ya vienen filtrados para ese rango exacto"""

    def get_sql_context(self) -> str:
        return """
Datos de RRHH en iDempiere:
- hr_employee: Empleados (c_bpartner_id, hr_department_id, hr_job_id, startdate, enddate, isactive)
- hr_process: Procesos de nómina (hr_payroll_id, c_period_id, dateacct, documentno, docstatus)
- hr_movement: Movimientos (hr_process_id, hr_employee_id, hr_concept_id, amount, qty)
- hr_concept: Conceptos de nómina (value, name, type, columntype)
- hr_payroll: Definiciones de nómina (name)
- c_bpartner: Datos de empleados (isemployee='Y', name, value)
"""

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)
        if date_from and date_to:
            mes = None

        label = build_period_label(date_from, date_to, mes, anio)

        # Employee summary (always included)
        summary = build_employee_summary(org_ids=org_ids)
        sections.append(self._format_summary(summary, "Resumen de Personal"))

        if any(w in msg for w in [
            "empleado", "personal", "lista", "cuántos", "cuantos",
            "trabajador", "trabajadores", "plantilla", "activo", "activos",
        ]):
            data = build_employee_list(org_ids=org_ids)
            if data:
                sections.append(f"## Lista de Empleados Activos ({len(data)} registros)")
                sections.append(self._format_table(data))

        if any(w in msg for w in [
            "cumpleaño", "cumpleaños", "cumpleañero", "cumpleañeros",
        ]):
            # For birthdays, use mes from the message (or current month if not specified)
            birthday_mes = mes
            if birthday_mes is None and not date_from:
                from datetime import datetime as _dt
                birthday_mes = _dt.now().month
            from app.agents.date_utils import MESES_NOMBRES
            mes_label = MESES_NOMBRES.get(birthday_mes, str(birthday_mes)) if birthday_mes else "Todos los meses"
            try:
                data = build_birthday_list(mes=birthday_mes, org_ids=org_ids)
                if data:
                    sections.append(f"## Cumpleañeros de {mes_label} ({len(data)} empleados)")
                    sections.append(self._format_table(data))
                else:
                    sections.append(
                        f"## Cumpleañeros de {mes_label}\n"
                        f"No se encontraron empleados con cumpleaños registrado para {mes_label}. "
                        f"Es posible que la fecha de nacimiento no esté cargada en el sistema ERP."
                    )
            except Exception as exc:
                sections.append(
                    f"## Cumpleañeros de {mes_label}\n"
                    f"No se pudo consultar la información de cumpleaños: {type(exc).__name__}. "
                    f"Es posible que el campo de fecha de nacimiento no esté disponible en la base de datos."
                )

        if any(w in msg for w in ["nómina", "nomina", "salario", "sueldo", "pago"]):
            data = build_payroll_summary(
                mes=mes, anio=anio, org_ids=org_ids,
                date_from=date_from, date_to=date_to,
            )
            sections.append(self._format_summary(data, f"Resumen de Nómina - {label}"))

        if any(w in msg for w in [
            "ausentismo", "ausentimos", "ausencia", "inasistencia",
            "falta", "faltas", "permiso", "reposo", "incapacidad",
            "licencia", "asistencia",
        ]):
            data = build_attendance_summary(
                mes=mes, anio=anio, org_ids=org_ids,
                date_from=date_from, date_to=date_to,
            )
            sections.append(self._format_summary(
                data, f"Indicadores de Ausentismo - {label}",
            ))

        if any(w in msg for w in [
            "rotación", "rotacion", "baja", "bajas", "egreso", "egresos",
            "renuncia", "despido", "turnover", "salida", "salidas",
        ]):
            data = build_turnover_summary(anio=anio, org_ids=org_ids)
            sections.append(self._format_summary(
                data, f"Indicadores de Rotación - Año {anio}",
            ))

        return "\n\n".join(sections) if sections else None

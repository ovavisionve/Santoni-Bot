"""
Agente de Recursos Humanos - Alimentos Santoni
Especializado en: nómina, vacaciones, asistencia, datos de empleados.

Fuente de datos: hr_employee, hr_process, hr_movement, hr_concept,
hr_payroll + c_bpartner en iDempiere (PostgreSQL 13).
"""

import logging

from app.agents.base_agent import BaseAgent
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
)

logger = logging.getLogger("santonibot.agents.rrhh")
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
- Listado y resumen de empleados por organización/departamento/cargo
- Búsqueda de empleados por cargo/puesto (ej: "cuantos obreros integrales", "lista de gerentes")
- Los datos incluyen desglose por cargo (por_cargo) con conteos exactos
- Cumpleañeros del mes (fecha de cumpleaños de empleados)
- Consultas de nómina por período (quincenas, mensuales)
- Conceptos de nómina: salario base, bonos, deducciones, neto a pagar
- Historial de procesos de nómina
- Indicadores de ausentismo: conceptos de ausencia en nómina (inasistencia, falta, permiso, reposo, incapacidad, licencia)
- NOTA AUSENTISMO: Los datos de ausentismo provienen de conceptos de nómina y se expresan en cantidad de OCURRENCIAS y MONTO en Bs. No se dispone de horas-hombre en el sistema de nómina de iDempiere.
- Vacaciones: los datos de vacaciones están en hr_movement como conceptos de nómina (buscar conceptos que contengan "vacacion" o "bono vacacional"). Se puede consultar quiénes tomaron vacaciones, días disfrutados y montos pagados por período.

CONTEXTO iDEMPIERE:
- Empleados: hr_employee (vinculado a c_bpartner via c_bpartner_id, con hr_department_id y hr_job_id)
- Departamentos: hr_department (name)
- Cargos: hr_job (name)
- Procesos de nómina: hr_process (documentno, dateacct, c_period_id, docstatus)
- Movimientos de nómina: hr_movement (hr_process_id, c_bpartner_id, hr_concept_id, amount, qty)
- Conceptos: hr_concept (value, name, columntype, type)
- Nóminas definidas: hr_payroll (name, hr_payroll_id)
- Organizaciones: INPROA SANTONI (444 empleados), InproMaiz (206), Santoni Service (134), AGROPECUARIA R.R. (124), AGA AGRICOLA (91), AGROINPROA (38), INVERSIONES AGA (4)
- NOTA: Los conteos de empleados usan DISTINCT por c_bpartner_id ya que hr_employee tiene múltiples registros por persona

REGLAS:
- Responde siempre en español, de forma profesional
- SÍ puedes compartir: nombres, apellidos, cargos, departamentos, organizaciones y estado (activo/inactivo) de los empleados. Esta información NO es confidencial para usuarios autorizados de RRHH.
- NO divulgar salarios individuales ni montos de nómina por persona sin autorización explícita. Los resúmenes agregados de nómina (totales por organización, departamento) SÍ se pueden compartir.
- Presenta montos salariales en Bolívares (Bs.) con formato venezolano (punto=miles, coma=decimal)
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa claramente. JAMÁS generes nombres, cédulas, cargos o fechas ficticias. Si los datos recibidos solo cubren un mes y el usuario pide otro mes, di "No se encontraron datos para ese mes" en vez de inventar registros
- PROHIBIDO decir "no tengo acceso", "no puedo acceder", "no dispongo" o "no tengo acceso directo". TÚ TIENES ACCESO COMPLETO a la base de datos de Santoni y los datos se consultan automáticamente. Si no hay datos para una consulta, di "No se encontraron datos" y sugiere consultas alternativas.
- Si la pregunta es ambigua, personal o usa palabras como "mi", "yo", "me" (ej: "mi departamento", "mi nómina", "mi estimado"), NO adivines a qué se refiere. Pide al usuario que reformule especificando: la organización, departamento, período u otros datos necesarios. Ejemplo: "Para poder ayudarte, indícame: ¿De qué organización o departamento necesitas el dato? ¿Y de qué período (mes/año)?"

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

    def get_capabilities(self) -> str:
        return (
            "CAPACIDADES REALES (lo que SÍ puedo consultar en la base de datos):\n"
            "✅ Resumen de empleados activos por organización, departamento y cargo\n"
            "✅ Búsqueda de empleados por cargo (ej: obreros, choferes, gerentes)\n"
            "✅ Empleados que ingresaron en un rango de fechas (filtro por startdate)\n"
            "✅ Cumpleañeros del mes\n"
            "✅ Resumen de nómina por período (totales devengado, deducciones, neto)\n"
            "✅ Indicadores de ausentismo (ocurrencias y monto por concepto de nómina)\n"
            "✅ Rotación de personal (bajas por año)\n"
            "\nNOTA: Los datos de empleados reflejan el estado ACTUAL en iDempiere. "
            "Para ver ingresos en un período específico, filtra por fecha de ingreso (startdate).\n"
            "\n✅ Vacaciones: datos de vacaciones disponibles en conceptos de nómina (hr_movement). "
            "Se puede consultar quiénes tomaron vacaciones, días y montos por período.\n"
            "\n❌ Consultas NO disponibles: evaluaciones de desempeño o prestaciones sociales "
            "(no están en las tablas consultadas). "
            "Indica al usuario que esos datos deben solicitarse al departamento de Talento Humano. "
            "NUNCA digas 'no tengo acceso' — di 'esa información no está disponible en el sistema'."
        )

    def get_sql_context(self) -> str:
        return """
Datos de RRHH en iDempiere:
- hr_employee: Empleados (c_bpartner_id, hr_department_id, hr_job_id, startdate, enddate, isactive)
- hr_process: Procesos de nómina (hr_payroll_id, c_period_id, dateacct, documentno, docstatus)
- hr_movement: Movimientos (hr_process_id, c_bpartner_id, hr_concept_id, amount, qty)
- hr_concept: Conceptos de nómina (value, name, type, columntype)
- hr_payroll: Definiciones de nómina (name)
- c_bpartner: Datos de empleados (isemployee='Y', name, value)
"""

    # Job title keywords that indicate a cargo-specific query.
    # When any of these appear, extract the surrounding words as the cargo search term.
    _CARGO_KEYWORDS = [
        "obrero", "obreros", "gerente", "gerentes", "analista", "analistas",
        "supervisor", "supervisora", "supervisores", "coordinador", "coordinadora",
        "coordinadores", "jefe", "jefa", "jefes", "director", "directora",
        "directores", "operario", "operarios", "operador", "operadores",
        "asistente", "asistentes", "auxiliar", "auxiliares", "secretaria",
        "secretario", "técnico", "tecnicos", "técnicos", "tecnico",
        "ingeniero", "ingenieros", "ingeniera", "chofer", "choferes",
        "vigilante", "vigilantes", "electricista", "electricistas",
        "mecánico", "mecanico", "mecánicos", "mecanicos",
        "soldador", "soldadores", "almacenista", "almacenistas",
        "recepcionista", "cajero", "cajera", "contador", "contadora",
        "administrador", "administradora", "mensajero",
    ]

    def _extract_cargo_search(self, msg: str) -> str | None:
        """Extract job title search term from the message.

        Detects cargo keywords and returns a cleaned search term.
        E.g. 'cuantos obreros integrales hay' → 'obrero integral'
        E.g. 'lista de analistas de control de calidad' → 'analista de control de calidad'

        Returns None if the message asks about multiple categories (e.g.
        'cuantos empleados, cuantos obreros y cuantos gerenciales') because
        in that case the por_cargo summary is a better answer.
        """
        msg_lower = msg.lower()

        # If the message lists multiple categories, don't extract a single cargo
        # e.g. "cuantos empleados, cuantos obreros y cuantos gerenciales"
        cargo_hits = sum(1 for kw in self._CARGO_KEYWORDS if kw in msg_lower)
        if cargo_hits >= 2:
            return None
        # Find which cargo keyword appears
        found_kw = None
        kw_pos = -1
        for kw in self._CARGO_KEYWORDS:
            pos = msg_lower.find(kw)
            if pos != -1 and (kw_pos == -1 or pos < kw_pos):
                found_kw = kw
                kw_pos = pos

        if found_kw is None:
            # Also check for "cargo" / "puesto" keyword followed by a name
            for trigger in ["cargo de ", "cargo ", "puesto de ", "puesto "]:
                pos = msg_lower.find(trigger)
                if pos != -1:
                    rest = msg_lower[pos + len(trigger):].strip()
                    # Take until end or common stop words
                    for stop in [" hay", " tiene", " en ", " de la ", " activo", "?"]:
                        idx = rest.find(stop)
                        if idx != -1:
                            rest = rest[:idx]
                    return rest.strip() if rest.strip() else None
            return None

        # Extract from keyword position to end, then clean up
        rest = msg_lower[kw_pos:].strip()
        # Remove trailing stop words/phrases
        for stop in [" hay", " tiene", " tenemos", " existen", " en la",
                     " actualmente", " activo", " activos", "?"]:
            idx = rest.find(stop)
            if idx != -1:
                rest = rest[:idx]
        # Normalize plural to singular for better ILIKE matching
        # "obreros integrales" → "obrero integral"  (SQL uses ILIKE %...%)
        result = rest.strip()
        return result if result else None

    def _extract_cargo_from_history(self, history: list[tuple[str, str]]) -> str | None:
        """Try to extract a cargo search term from recent user messages in history."""
        if not history:
            return None
        # Scan history in reverse (most recent first) for a cargo keyword
        for role, content in reversed(history):
            if role == "user":
                cargo = self._extract_cargo_search(content)
                if cargo:
                    return cargo
        return None

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

        # Detect cargo/job search (current message, then history fallback)
        cargo_search = self._extract_cargo_search(message)
        if not cargo_search and (date_from or mes) and history:
            # Follow-up with dates but no cargo keyword → check history
            cargo_search = self._extract_cargo_from_history(history)

        try:
            # Employee summary (always included)
            summary = build_employee_summary(org_ids=org_ids)
            sections.append(self._format_summary(summary, "Resumen de Personal"))

            if cargo_search:
                # Cargo-specific query: filter employee list by job title
                date_label = f" (ingresados {label})" if date_from else ""
                data = build_employee_list(
                    org_ids=org_ids, cargo_search=cargo_search,
                    date_from=date_from, date_to=date_to,
                )
                if data:
                    sections.append(
                        f"## Empleados con cargo '{cargo_search.upper()}'{date_label} ({len(data)} encontrados)"
                    )
                    sections.append(self._format_table(data))
                else:
                    sections.append(
                        f"## Búsqueda por cargo: '{cargo_search}'{date_label}\n"
                        f"No se encontraron empleados activos con ese cargo"
                        f"{' en el período indicado' if date_from else ''}. "
                        f"Revisa la sección 'por_cargo' del resumen para ver los cargos disponibles."
                    )
            elif any(w in msg for w in [
                "empleado", "personal", "lista", "cuántos", "cuantos",
                "trabajador", "trabajadores", "plantilla", "activo", "activos",
                "ingreso", "ingresos", "ingresaron", "ingresó",
                "contratación", "contratacion", "contrataciones", "contrataron",
                "nuevo ingreso", "nuevos ingresos",
            ]):
                data = build_employee_list(
                    org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                )
                if data:
                    date_label = f" - {label}" if date_from else ""
                    sections.append(f"## Lista de Empleados Activos{date_label} ({len(data)} registros)")
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
                try:
                    data = build_attendance_summary(
                        mes=mes, anio=anio, org_ids=org_ids,
                        date_from=date_from, date_to=date_to,
                    )
                    sections.append(self._format_summary(
                        data, f"Indicadores de Ausentismo - {label}",
                    ))
                except Exception as exc:
                    logger.error("Error en ausentismo: %s: %s", type(exc).__name__, exc, exc_info=True)
                    sections.append(
                        f"## Indicadores de Ausentismo - {label}\n"
                        f"No se pudieron obtener los datos de ausentismo para este período. "
                        f"Error: {type(exc).__name__}. Intenta con otro período o consulta específica."
                    )

            if any(w in msg for w in [
                "rotación", "rotacion", "baja", "bajas", "egreso", "egresos",
                "renuncia", "despido", "turnover", "salida", "salidas",
            ]):
                data = build_turnover_summary(anio=anio, org_ids=org_ids)
                sections.append(self._format_summary(
                    data, f"Indicadores de Rotación - Año {anio}",
                ))

        except Exception as exc:
            logger.error("Error consultando datos de RRHH: %s: %s", type(exc).__name__, exc, exc_info=True)
            sections.append(
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Intenta de nuevo en unos momentos."
            )

        return "\n\n".join(sections) if sections else None

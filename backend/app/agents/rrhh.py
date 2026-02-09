"""
Agente de Recursos Humanos - Alimentos Santoni
Especializado en: nómina, vacaciones, asistencia, datos de empleados, evaluaciones.
"""

from app.agents.base_agent import BaseAgent


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
- Consultas de nómina y recibos de pago
- Gestión de vacaciones (saldos, solicitudes, histórico)
- Control de asistencia y ausentismo
- Datos maestros de empleados
- Evaluaciones de desempeño
- Alertas de cumpleaños y aniversarios laborales
- Estadísticas de productividad por empleado/departamento
- Información de beneficios y deducciones

REGLAS:
- Responde siempre en español, de forma profesional
- Los datos de RRHH son ALTAMENTE SENSIBLES - toda la información es confidencial
- Nunca reveles datos salariales de otros empleados a usuarios no autorizados
- Cumple con la legislación laboral venezolana (LOTTT)
- Presenta montos salariales en Bolívares (Bs.)
- NUNCA inventes datos de empleados. Si no tienes la información, dilo claramente

CONTEXTO:
- Alimentos Santoni: empresa agroindustrial
- Ubicaciones: Agua Blanca (2 plantas), Araure (oficinas administrativas)
- Turnos: Oficina diurno, Planta rotativo
- Horario oficina: 7:30am a 5pm
- Responsables RRHH: Emelin Salas, Leonardo Rivero
- ERP: iDempiere

NOTA: Entorno de datos de prueba. Los datos reales se conectarán con iDempiere."""

    def get_sql_context(self) -> str:
        return """
-- Tablas relevantes de iDempiere para RRHH:
-- HR_Employee: Empleados
-- HR_Payroll: Nóminas
-- HR_PayrollLine: Líneas de nómina (conceptos)
-- HR_Leave: Vacaciones y permisos
-- HR_Attendance: Asistencia
-- HR_Department: Departamentos
-- HR_Job: Cargos
-- C_BPartner: Datos base del empleado como socio de negocio
"""

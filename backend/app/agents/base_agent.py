"""
Base class for all SantoniBot specialized agents.
Each department agent inherits from this and implements its own
system prompt, data fetching, and query processing logic.

Supports both full-response (process) and streaming (stream) modes.
"""

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import get_settings
from app.services.llm_factory import create_llm

settings = get_settings()
logger = logging.getLogger("santonibot.agents")

# Performance limits
_MAX_TABLE_ROWS = 50
_MAX_HISTORY_MESSAGES = 40
_MAX_TOKENS = 4096

# Days of week in Spanish
_DIAS_SEMANA = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo",
}
_MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _build_datetime_context() -> str:
    """Build a context string with the current date/time for the LLM."""
    now = datetime.now()
    dia = _DIAS_SEMANA[now.weekday()]
    mes = _MESES_ES[now.month]
    return (
        f"FECHA Y HORA ACTUAL DEL SISTEMA:\n"
        f"- Hoy es: {dia} {now.day} de {mes} de {now.year}\n"
        f"- Hora: {now.strftime('%H:%M')} (Venezuela)\n"
        f"- Mes actual: {mes} {now.year}\n"
        f"- Año actual: {now.year}\n"
        f"\nCuando el usuario diga 'actual', 'hoy', 'este mes', 'del mes', 'este año' "
        f"se refiere a: {mes} {now.year}.\n"
        f"NUNCA respondas con datos de otra fecha a menos que el usuario lo pida explícitamente.\n"
    )


class BaseAgent(ABC):
    """Base agent for all department-specific agents."""

    def __init__(self):
        self.llm = create_llm(
            temperature=0.1,
            max_tokens=_MAX_TOKENS,
            purpose="agent",
        )
        self._system_prompt = self.get_system_prompt()

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier name."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the agent."""
        ...

    @property
    @abstractmethod
    def department(self) -> str:
        """Department this agent serves."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the agent's capabilities."""
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        ...

    @abstractmethod
    def get_sql_context(self) -> str:
        """Return SQL schema context relevant to this agent."""
        ...

    def fetch_data(
        self,
        message: str,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> str | None:
        """
        Fetch relevant data from the database based on the user's message.
        Override in subclasses to provide department-specific data fetching.
        history contains recent conversation tuples: (role, content).
        """
        return None

    def get_capabilities(self) -> str:
        """Return a description of what this agent CAN and CANNOT do.

        Override in subclasses to declare honest capabilities.
        """
        return ""

    def _build_messages(
        self,
        message: str,
        history: list[tuple[str, str]] | None = None,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
    ) -> tuple[list, bool]:
        """Build the LLM message list. Returns (messages, has_data)."""
        # Build datetime context
        datetime_ctx = _build_datetime_context()

        # Build capabilities context
        capabilities = self.get_capabilities()
        capabilities_block = ""
        if capabilities:
            capabilities_block = f"\n\n{capabilities}\n"

        # Enhance system prompt with date, capabilities, and instructions
        enhanced_prompt = (
            self._system_prompt + "\n\n"
            f"{datetime_ctx}"
            f"{capabilities_block}\n"
            "INSTRUCCIONES ADICIONALES:\n"
            "- Si el usuario hace una referencia contextual (ej: 'y por zona?', "
            "'dame mas detalle', 'y del mes pasado?'), usa el historial para entender el contexto.\n"
            "- Si pide COMPARACION entre periodos, presenta tabla comparativa "
            "con columnas: Concepto | Periodo 1 | Periodo 2 | Variacion | %.\n"
            "- Formato venezolano: punto=miles, coma=decimal (ej: 1.234.567,89).\n"
            "\nREGLAS ANTI-INVENCIÓN (OBLIGATORIAS):\n"
            "- Presenta SOLO los datos que recibes en el contexto. NO agregues datos adicionales.\n"
            "- Si quieres mostrar un porcentaje, CALCÚLALO de los datos reales (ej: valor/total*100).\n"
            "- NUNCA digas 'vs mes anterior' o 'comparativo' si NO tienes datos de ambos períodos.\n"
            "- NUNCA agregues secciones de 'Recomendaciones' o 'Plan de acción' con información inventada.\n"
            "- NUNCA inventes nombres de clientes, proveedores, empleados, productos ni montos.\n"
            "- Las únicas sugerencias permitidas son consultas que el sistema realmente puede ejecutar.\n"
            "- Si los datos muestran un solo período, NO inventes comparativos con otros períodos.\n"
        )
        messages = [SystemMessage(content=enhanced_prompt)]

        # Data Catalog: inject real schema/stats context from iDempiere (optional)
        try:
            from app.services.data_catalog import get_catalog_service
            catalog = get_catalog_service()
            catalog_context = catalog.get_department_context(self.department)
            if catalog_context:
                messages.append(SystemMessage(content=catalog_context))
        except Exception as exc:
            logger.debug("Data catalog unavailable for %s: %s", self.name, exc)

        # RAG: retrieve relevant knowledge-base context (optional)
        try:
            from app.services.rag_service import get_rag_service
            rag = get_rag_service()
            rag_context = rag.get_context_for_agent(self.department, message)
            if rag_context:
                messages.append(SystemMessage(content=rag_context))
        except Exception as exc:
            logger.debug("RAG context unavailable for %s: %s", self.name, exc)

        # Fetch real data from the database
        try:
            data_context = self.fetch_data(message, org_ids=org_ids, salesrep_id=salesrep_id, history=history)
        except Exception as exc:
            logger.error(
                "Error in %s.fetch_data: %s: %s",
                self.name, type(exc).__name__, exc, exc_info=True,
            )
            data_context = (
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Informa al usuario que hubo un problema de conexión con la base de datos "
                f"y que intente de nuevo en unos momentos."
            )

        if data_context:
            messages.append(
                SystemMessage(
                    content=(
                        "DATOS REALES DE LA BASE DE DATOS:\n"
                        "Usa EXCLUSIVAMENTE estos datos para responder. NO agregues información "
                        "que no esté aquí. Sé conciso y directo.\n\n"
                        f"{data_context}"
                    )
                )
            )
        else:
            sql_context = self.get_sql_context()
            messages.append(
                SystemMessage(
                    content=(
                        "⚠️ INSTRUCCIÓN OBLIGATORIA — SIN DATOS DISPONIBLES ⚠️\n\n"
                        "No se encontraron datos para esta consulta en la base de datos.\n\n"
                        "Tu ÚNICA respuesta permitida es:\n"
                        "1. Informar al usuario que no hay datos disponibles para lo que pidió.\n"
                        "2. Sugerir alternativas: otro período, otro filtro, o reformular la pregunta.\n\n"
                        "PROHIBIDO TERMINANTEMENTE:\n"
                        "- NO generes tablas con datos numéricos inventados.\n"
                        "- NO inventes nombres de clientes, proveedores, empleados ni productos.\n"
                        "- NO muestres montos, porcentajes ni cifras que no provengan de los datos.\n"
                        "- NO uses frases como 'datos referenciales' o 'datos estimados' para "
                        "justificar información inventada.\n"
                        "- Si generas CUALQUIER tabla con números sin haber recibido datos reales, "
                        "estarás MINTIENDO al usuario.\n\n"
                        + (f"Esquema disponible para referencia:\n{sql_context}" if sql_context else "")
                    )
                )
            )

        # Add conversation history (limited)
        if history:
            for role, content in history[-_MAX_HISTORY_MESSAGES:]:
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=message))
        return messages, data_context is not None

    @staticmethod
    def _detect_hallucination(response_text: str, has_data: bool) -> bool:
        """Detect if the LLM likely hallucinated data when no real data was provided.

        Returns True if hallucination is detected (no data but response has tables with numbers).
        """
        if has_data:
            return False

        # Check for markdown tables containing monetary amounts
        # Pattern: | ... number with thousands/decimals ... |
        table_with_numbers = re.search(
            r'\|[^|]*\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?[^|]*\|', response_text
        )
        if table_with_numbers:
            return True

        # Check for tables with dollar/bolivar amounts
        currency_in_table = re.search(
            r'\|[^|]*(?:Bs\.?|USD|\$)\s*\d+[^|]*\|', response_text
        )
        if currency_in_table:
            return True

        return False

    _HALLUCINATION_REPLACEMENT = (
        "No tengo datos disponibles en la base de datos para responder esta consulta.\n\n"
        "**¿Qué puedes hacer?**\n"
        "- Intenta con un período diferente (ej: otro mes o año)\n"
        "- Reformula la pregunta con más detalle\n"
        "- Consulta al administrador si los datos ya fueron cargados en el sistema\n\n"
        "*Nota: Solo puedo mostrar información que existe en la base de datos de iDempiere. "
        "No genero datos estimados ni aproximados.*"
    )

    async def process(
        self,
        message: str,
        history: list[tuple[str, str]] | None = None,
        user_departments: list[str] | None = None,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
    ) -> dict:
        """Process a user message and return a complete response."""
        messages, has_data = self._build_messages(message, history, org_ids, salesrep_id)
        response = await self.llm.ainvoke(messages)

        response_text = response.content

        # Post-response validation: detect hallucination when no data was provided
        if self._detect_hallucination(response_text, has_data):
            logger.warning(
                "Hallucination detected in %s (has_data=%s). Replacing response.",
                self.name, has_data,
            )
            response_text = self._HALLUCINATION_REPLACEMENT

        return {
            "response": response_text,
            "agent_used": self.name,
            "metadata": {
                "department": self.department,
                "has_data": has_data,
            },
        }

    async def stream(
        self,
        message: str,
        history: list[tuple[str, str]] | None = None,
        user_departments: list[str] | None = None,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens for real-time display."""
        messages, _ = self._build_messages(message, history, org_ids, salesrep_id)
        async for chunk in self.llm.astream(messages):
            if chunk.content:
                yield chunk.content

    @staticmethod
    def _format_table(data: list[dict], columns: list[str] | None = None) -> str:
        """Format a list of dicts as a markdown table string for LLM context."""
        if not data:
            return "Sin datos disponibles."

        cols = columns or list(data[0].keys())
        header = "| " + " | ".join(str(c).replace("_", " ").title() for c in cols) + " |"
        separator = "| " + " | ".join("---" for _ in cols) + " |"

        rows = []
        for row in data[:_MAX_TABLE_ROWS]:
            values = []
            for c in cols:
                v = row.get(c, "")
                if isinstance(v, float):
                    values.append(f"{v:,.2f}")
                else:
                    values.append(str(v) if v is not None else "-")
            rows.append("| " + " | ".join(values) + " |")

        table = "\n".join([header, separator] + rows)
        if len(data) > _MAX_TABLE_ROWS:
            table += f"\n\n*(Mostrando {_MAX_TABLE_ROWS} de {len(data)} registros)*"
        return table

    @staticmethod
    def _format_summary(data: dict, title: str = "") -> str:
        """Format a summary dict as readable text for LLM context."""
        lines = []
        if title:
            lines.append(f"## {title}")

        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"\n### {key.replace('_', ' ').title()}")
                for k, v in value.items():
                    if isinstance(v, float):
                        lines.append(f"- {k.replace('_', ' ').title()}: {v:,.2f}")
                    else:
                        lines.append(f"- {k.replace('_', ' ').title()}: {v}")
            elif isinstance(value, list):
                lines.append(f"\n### {key.replace('_', ' ').title()}")
                if value and isinstance(value[0], dict):
                    lines.append(BaseAgent._format_table(value))
                else:
                    for item in value[:20]:
                        lines.append(f"- {item}")
            elif isinstance(value, float):
                lines.append(f"- {key.replace('_', ' ').title()}: {value:,.2f}")
            else:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        return "\n".join(lines)

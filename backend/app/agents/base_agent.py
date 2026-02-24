"""
Base class for all SantoniBot specialized agents.
Each department agent inherits from this and implements its own
system prompt, data fetching, and query processing logic.

Supports both full-response (process) and streaming (stream) modes.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import get_settings
from app.services.llm_factory import create_llm

settings = get_settings()
logger = logging.getLogger("santonibot.agents")

# Performance limits
_MAX_TABLE_ROWS = 50
_MAX_HISTORY_MESSAGES = 40
_MAX_TOKENS = 4096


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

    def _build_messages(
        self,
        message: str,
        history: list[tuple[str, str]] | None = None,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
    ) -> tuple[list, bool]:
        """Build the LLM message list. Returns (messages, has_data)."""
        # Enhance system prompt with comparison/context instructions
        enhanced_prompt = (
            self._system_prompt + "\n\n"
            "INSTRUCCIONES ADICIONALES:\n"
            "- Si el usuario hace una referencia contextual (ej: 'y por zona?', "
            "'dame mas detalle', 'y del mes pasado?'), usa el historial para entender el contexto.\n"
            "- Si pide COMPARACION entre periodos, presenta tabla comparativa "
            "con columnas: Concepto | Periodo 1 | Periodo 2 | Variacion | %.\n"
            "- Formato venezolano: punto=miles, coma=decimal (ej: 1.234.567,89).\n"
        )
        messages = [SystemMessage(content=enhanced_prompt)]

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
        data_context = self.fetch_data(message, org_ids=org_ids, salesrep_id=salesrep_id, history=history)
        if data_context:
            messages.append(
                SystemMessage(
                    content=(
                        "DATOS REALES DE LA BASE DE DATOS:\n"
                        "Usa estos datos para responder. Sé conciso y directo.\n\n"
                        f"{data_context}"
                    )
                )
            )
        else:
            sql_context = self.get_sql_context()
            if sql_context:
                messages.append(
                    SystemMessage(
                        content=(
                            "No se encontraron datos para esta consulta. "
                            "Informa al usuario que el dato no está disponible "
                            "o pide más detalles.\n\n"
                            f"Esquema disponible:\n{sql_context}"
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

        return {
            "response": response.content,
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

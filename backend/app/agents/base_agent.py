"""
Base class for all SantoniBot specialized agents.
Each department agent inherits from this and implements its own
system prompt, data fetching, and query processing logic.
"""

import json
import logging
from abc import ABC, abstractmethod

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import get_settings
from app.services.llm_factory import create_llm

settings = get_settings()
logger = logging.getLogger("santonibot.agents")

class BaseAgent(ABC):
    """Base agent for all department-specific agents."""

    def __init__(self):
        self.llm = create_llm(
            temperature=0.1,
            max_tokens=4096,
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

    def fetch_data(self, message: str, org_ids: list[int] | None = None) -> str | None:
        """
        Fetch relevant data from the database based on the user's message.
        Override in subclasses to provide department-specific data fetching.
        Returns a formatted string with the data, or None if no data found.

        Args:
            message: User's query text
            org_ids: iDempiere organization IDs to filter by (None = all orgs)
        """
        return None

    async def process(
        self,
        message: str,
        history: list[tuple[str, str]] | None = None,
        user_departments: list[str] | None = None,
        org_ids: list[int] | None = None,
    ) -> dict:
        """
        Process a user message and return a response.

        1. Fetch relevant data from the database
        2. Build the prompt with data context
        3. Send to LLM for natural language response
        """
        messages = [SystemMessage(content=self._system_prompt)]

        # RAG: retrieve relevant knowledge-base context (optional)
        try:
            from app.services.rag_service import get_rag_service

            rag = get_rag_service()
            rag_context = rag.get_context_for_agent(self.department, message)
            if rag_context:
                messages.append(SystemMessage(content=rag_context))
        except Exception as exc:
            # RAG is optional -- never block the agent if it fails
            logger.debug("RAG context unavailable for %s: %s", self.name, exc)

        # Fetch real data from the database (filtered by user's org)
        data_context = self.fetch_data(message, org_ids=org_ids)
        if data_context:
            messages.append(
                SystemMessage(
                    content=(
                        "DATOS REALES DE LA BASE DE DATOS:\n"
                        "Usa estos datos para responder la consulta del usuario. "
                        "Presenta la información de forma clara, con tablas markdown si corresponde.\n\n"
                        f"{data_context}"
                    )
                )
            )
        else:
            # Add SQL schema context as fallback
            sql_context = self.get_sql_context()
            if sql_context:
                messages.append(
                    SystemMessage(
                        content=(
                            "No se encontraron datos específicos para esta consulta. "
                            "Informa al usuario que el dato solicitado no está disponible "
                            "o pide más detalles para refinar la búsqueda.\n\n"
                            f"Esquema disponible:\n{sql_context}"
                        )
                    )
                )

        # Add conversation history
        if history:
            for role, content in history[-10:]:
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=message))

        response = await self.llm.ainvoke(messages)

        return {
            "response": response.content,
            "agent_used": self.name,
            "metadata": {
                "department": self.department,
                "has_data": data_context is not None,
            },
        }

    @staticmethod
    def _format_table(data: list[dict], columns: list[str] | None = None) -> str:
        """Format a list of dicts as a markdown table string for LLM context."""
        if not data:
            return "Sin datos disponibles."

        cols = columns or list(data[0].keys())

        # Header
        header = "| " + " | ".join(str(c).replace("_", " ").title() for c in cols) + " |"
        separator = "| " + " | ".join("---" for _ in cols) + " |"

        # Rows
        rows = []
        for row in data[:50]:  # Limit to 50 rows for LLM context
            values = []
            for c in cols:
                v = row.get(c, "")
                if isinstance(v, float):
                    values.append(f"{v:,.2f}")
                else:
                    values.append(str(v) if v is not None else "-")
            rows.append("| " + " | ".join(values) + " |")

        table = "\n".join([header, separator] + rows)
        if len(data) > 50:
            table += f"\n\n*(Mostrando 50 de {len(data)} registros)*"
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

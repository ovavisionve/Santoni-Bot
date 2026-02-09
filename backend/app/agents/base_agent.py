"""
Base class for all SantoniBot specialized agents.
Each department agent inherits from this and implements its own
system prompt, tools, and query processing logic.
"""

from abc import ABC, abstractmethod

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import get_settings

settings = get_settings()


class BaseAgent(ABC):
    """Base agent for all department-specific agents."""

    def __init__(self):
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            temperature=0.1,
            max_tokens=4096,
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

    async def process(
        self,
        message: str,
        history: list[tuple[str, str]] | None = None,
        user_departments: list[str] | None = None,
    ) -> dict:
        """
        Process a user message and return a response.

        Args:
            message: The user's query
            history: List of (role, content) tuples for conversation context
            user_departments: Departments the user has access to

        Returns:
            dict with 'response', 'agent_used', and optional 'metadata'
        """
        messages = [SystemMessage(content=self._system_prompt)]

        # Add SQL context
        sql_context = self.get_sql_context()
        if sql_context:
            messages.append(
                SystemMessage(
                    content=f"Contexto de base de datos disponible:\n{sql_context}"
                )
            )

        # Add conversation history
        if history:
            for role, content in history[-10:]:  # Last 10 messages for context
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=message))

        response = await self.llm.ainvoke(messages)

        return {
            "response": response.content,
            "agent_used": self.name,
            "metadata": {"department": self.department},
        }

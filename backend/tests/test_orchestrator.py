"""
Tests for the Orchestrator: classification of user queries and routing
to the correct department agent.

All LLM calls are mocked - no real Groq/Anthropic API calls are made.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock

from app.agents.orchestrator import Orchestrator, CLASSIFICATION_PROMPT
from app.models.user import User, UserRole, Department


# ---------------------------------------------------------------------------
# Helpers: create a mock User object without DB
# ---------------------------------------------------------------------------

def _make_mock_user(
    role: UserRole = UserRole.USUARIO,
    department: Department = Department.VENTAS,
    extra_departments: str | None = None,
):
    """Create a mock User with the given role and departments."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.role = role
    user.department = department
    user.extra_departments = extra_departments
    user.is_active = True

    # Reproduce allowed_departments logic
    if role == UserRole.ADMINISTRADOR:
        user.allowed_departments = [d.value for d in Department]
    else:
        deps = [department.value]
        if extra_departments:
            deps.extend(d.strip() for d in extra_departments.split(",") if d.strip())
        user.allowed_departments = deps

    return user


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------

class TestOrchestratorClassification:
    """Tests for the classify method of the Orchestrator."""

    @patch("app.agents.orchestrator.ChatGroq")
    def test_classify_ventas(self, mock_groq_cls):
        """Query about sales should classify as 'ventas'."""
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "ventas"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_groq_cls.return_value = mock_llm

        orch = Orchestrator()
        orch.classifier = mock_llm

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.classify("Cuales son las ventas del mes?", ["ventas", "finanzas"])
        )
        assert result == "ventas"

    @patch("app.agents.orchestrator.ChatGroq")
    def test_classify_finanzas(self, mock_groq_cls):
        """Query about finances should classify as 'finanzas'."""
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "finanzas"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_groq_cls.return_value = mock_llm

        orch = Orchestrator()
        orch.classifier = mock_llm

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.classify("Cual es el flujo de caja?", ["ventas", "finanzas"])
        )
        assert result == "finanzas"

    @patch("app.agents.orchestrator.ChatGroq")
    def test_classify_no_access(self, mock_groq_cls):
        """Query to unauthorized department should return 'no_access'."""
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "NO_ACCESS"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_groq_cls.return_value = mock_llm

        orch = Orchestrator()
        orch.classifier = mock_llm

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.classify("Datos de nomina", ["ventas"])
        )
        assert result == "no_access"

    @patch("app.agents.orchestrator.ChatGroq")
    def test_classify_general(self, mock_groq_cls):
        """General greeting should classify as 'general'."""
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "general"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_groq_cls.return_value = mock_llm

        orch = Orchestrator()
        orch.classifier = mock_llm

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.classify("Hola, como estas?", ["ventas"])
        )
        assert result == "general"

    @patch("app.agents.orchestrator.ChatGroq")
    def test_classify_unknown_falls_to_general(self, mock_groq_cls):
        """Unknown agent classification should fallback to 'general'."""
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "unknown_agent"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_groq_cls.return_value = mock_llm

        orch = Orchestrator()
        orch.classifier = mock_llm

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.classify("Something random", ["ventas"])
        )
        assert result == "general"

    @patch("app.agents.orchestrator.ChatGroq")
    def test_classify_strips_quotes(self, mock_groq_cls):
        """Classifier output with quotes should be cleaned."""
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = '"ventas"'
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_groq_cls.return_value = mock_llm

        orch = Orchestrator()
        orch.classifier = mock_llm

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.classify("Ranking de ventas", ["ventas"])
        )
        assert result == "ventas"


# ---------------------------------------------------------------------------
# Process / routing tests
# ---------------------------------------------------------------------------

class TestOrchestratorProcess:
    """Tests for the process method: routing to correct agents."""

    @patch("app.agents.orchestrator.ChatGroq")
    def test_process_routes_to_ventas(self, mock_groq_cls):
        """Process should route a sales query to the ventas agent."""
        # Set up the classifier mock
        mock_llm = AsyncMock()
        classify_response = MagicMock()
        classify_response.content = "ventas"
        mock_llm.ainvoke = AsyncMock(return_value=classify_response)
        mock_groq_cls.return_value = mock_llm

        orch = Orchestrator()
        orch.classifier = mock_llm

        # Mock the ventas agent
        mock_agent = AsyncMock()
        mock_agent.department = "ventas"
        mock_agent.display_name = "Ventas"
        mock_agent.process = AsyncMock(
            return_value={
                "response": "Las ventas son excelentes.",
                "agent_used": "ventas",
                "metadata": {"department": "ventas"},
            }
        )
        orch.agents["ventas"] = mock_agent

        user = _make_mock_user(
            role=UserRole.USUARIO,
            department=Department.VENTAS,
        )

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.process("Cuanto vendimos este mes?", user)
        )

        assert result["agent_used"] == "ventas"
        assert "ventas" in result["response"].lower() or len(result["response"]) > 0
        mock_agent.process.assert_awaited_once()

    @patch("app.agents.orchestrator.ChatGroq")
    def test_process_no_access(self, mock_groq_cls):
        """Process should deny access when classified as no_access."""
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "no_access"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_groq_cls.return_value = mock_llm

        orch = Orchestrator()
        orch.classifier = mock_llm

        user = _make_mock_user(
            role=UserRole.USUARIO,
            department=Department.VENTAS,
        )

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.process("Muestra la nomina", user)
        )

        assert result["agent_used"] == "orchestrator"
        assert "no tienes permisos" in result["response"].lower()

    @patch("app.agents.orchestrator.ChatGroq")
    def test_process_general_query(self, mock_groq_cls):
        """General queries should be handled by the orchestrator itself."""
        mock_llm = AsyncMock()

        # First call: classification returns "general"
        classify_response = MagicMock()
        classify_response.content = "general"

        # Second call: general handler returns greeting
        general_response = MagicMock()
        general_response.content = "Hola! Soy SantoniBot."

        mock_llm.ainvoke = AsyncMock(
            side_effect=[classify_response, general_response]
        )
        mock_groq_cls.return_value = mock_llm

        orch = Orchestrator()
        orch.classifier = mock_llm

        user = _make_mock_user(
            role=UserRole.USUARIO,
            department=Department.VENTAS,
        )

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.process("Hola!", user)
        )

        assert result["agent_used"] == "general"
        assert "SantoniBot" in result["response"]

    @patch("app.agents.orchestrator.ChatGroq")
    def test_process_department_access_check(self, mock_groq_cls):
        """Even if classified correctly, access should be verified against user departments."""
        mock_llm = AsyncMock()
        classify_response = MagicMock()
        classify_response.content = "rrhh"
        mock_llm.ainvoke = AsyncMock(return_value=classify_response)
        mock_groq_cls.return_value = mock_llm

        orch = Orchestrator()
        orch.classifier = mock_llm

        # Mock RRHH agent
        mock_rrhh = MagicMock()
        mock_rrhh.department = "rrhh"
        mock_rrhh.display_name = "RRHH"
        orch.agents["rrhh"] = mock_rrhh

        # User only has ventas access
        user = _make_mock_user(
            role=UserRole.USUARIO,
            department=Department.VENTAS,
        )

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.process("Cuantos empleados hay?", user)
        )

        assert "no tienes acceso" in result["response"].lower()
        assert result["metadata"].get("access_denied") is True

    @patch("app.agents.orchestrator.ChatGroq")
    def test_process_admin_has_all_access(self, mock_groq_cls):
        """Admin users should have access to all departments."""
        mock_llm = AsyncMock()
        classify_response = MagicMock()
        classify_response.content = "rrhh"
        mock_llm.ainvoke = AsyncMock(return_value=classify_response)
        mock_groq_cls.return_value = mock_llm

        orch = Orchestrator()
        orch.classifier = mock_llm

        # Mock RRHH agent
        mock_agent = AsyncMock()
        mock_agent.department = "rrhh"
        mock_agent.process = AsyncMock(
            return_value={
                "response": "Tenemos 150 empleados.",
                "agent_used": "rrhh",
                "metadata": {"department": "rrhh"},
            }
        )
        orch.agents["rrhh"] = mock_agent

        user = _make_mock_user(role=UserRole.ADMINISTRADOR)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.process("Cuantos empleados hay?", user)
        )

        assert result["agent_used"] == "rrhh"
        mock_agent.process.assert_awaited_once()


# ---------------------------------------------------------------------------
# CLASSIFICATION_PROMPT tests
# ---------------------------------------------------------------------------

class TestClassificationPrompt:
    """Tests for the classification prompt template."""

    def test_prompt_includes_departments(self):
        """The prompt should include the user's allowed departments."""
        formatted = CLASSIFICATION_PROMPT.format(
            departments="ventas, finanzas",
            message="test message",
        )
        assert "ventas, finanzas" in formatted

    def test_prompt_includes_message(self):
        """The prompt should include the user's message."""
        formatted = CLASSIFICATION_PROMPT.format(
            departments="ventas",
            message="Cuales son las ventas?",
        )
        assert "Cuales son las ventas?" in formatted

    def test_prompt_lists_all_agents(self):
        """The prompt should list all available agent names."""
        formatted = CLASSIFICATION_PROMPT.format(
            departments="ventas", message="test"
        )
        expected_agents = [
            "finanzas",
            "contabilidad",
            "ventas",
            "rrhh",
            "produccion",
            "compras_insumos",
            "compras_productores",
            "general",
        ]
        for agent in expected_agents:
            assert agent in formatted

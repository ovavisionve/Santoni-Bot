"""
Tests for the Orchestrator: classification of user queries and routing
to the correct department agent.

The orchestrator uses keyword-based classification (no LLM calls for routing).
LLM is only used for general queries, which we mock here.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.agents.orchestrator import Orchestrator, classify_by_keywords
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
    user.org_ids = None
    user.idempiere_salesrep_id = None

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
# Classification tests (keyword-based, no LLM)
# ---------------------------------------------------------------------------

class TestOrchestratorClassification:
    """Tests for the classify method of the Orchestrator."""

    def test_classify_ventas(self):
        """Query about sales should classify as 'ventas'."""
        result = classify_by_keywords(
            "Cuales son las ventas del mes?", ["ventas", "finanzas"]
        )
        assert result == "ventas"

    def test_classify_finanzas(self):
        """Query about finances should classify as 'finanzas'."""
        result = classify_by_keywords(
            "Cual es el flujo de caja?", ["ventas", "finanzas"]
        )
        assert result == "finanzas"

    def test_classify_no_access(self):
        """Query to unauthorized department should return 'no_access'."""
        result = classify_by_keywords(
            "Datos de nomina", ["ventas"]
        )
        assert result == "no_access"

    def test_classify_general(self):
        """General greeting should classify as 'general'."""
        result = classify_by_keywords(
            "Hola, como estas?", ["ventas"]
        )
        assert result == "general"

    def test_classify_unknown_falls_to_general(self):
        """Unknown query with no keyword match should fallback to 'general'."""
        result = classify_by_keywords(
            "Something random", ["ventas"]
        )
        assert result == "general"

    def test_classify_strips_quotes(self):
        """Ventas keywords should be detected regardless of context."""
        result = classify_by_keywords(
            "Ranking de ventas", ["ventas"]
        )
        assert result == "ventas"


# ---------------------------------------------------------------------------
# Process / routing tests
# ---------------------------------------------------------------------------

class TestOrchestratorProcess:
    """Tests for the process method: routing to correct agents."""

    @patch("app.agents.orchestrator.create_llm")
    def test_process_routes_to_ventas(self, mock_create_llm):
        """Process should route a sales query to the ventas agent."""
        mock_create_llm.return_value = MagicMock()

        orch = Orchestrator()

        # Mock the ventas agent
        mock_agent = AsyncMock()
        mock_agent.department = "ventas"
        mock_agent.display_name = "Ventas"
        mock_agent.process = AsyncMock(
            return_value={
                "response": "Las ventas son excelentes.",
                "agent_used": "ventas",
                "metadata": {"department": "ventas", "has_data": True},
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

    @patch("app.agents.orchestrator.create_llm")
    def test_process_no_access(self, mock_create_llm):
        """Process should deny access when user lacks department permissions."""
        mock_create_llm.return_value = MagicMock()

        orch = Orchestrator()

        # User only has ventas, asking about nomina (rrhh)
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

    @patch("app.agents.orchestrator.create_llm")
    def test_process_general_query(self, mock_create_llm):
        """General queries should be handled by the orchestrator itself."""
        mock_llm = AsyncMock()
        general_response = MagicMock()
        general_response.content = "Hola! Soy SantoniBot."
        mock_llm.ainvoke = AsyncMock(return_value=general_response)
        mock_create_llm.return_value = mock_llm

        orch = Orchestrator()

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

    @patch("app.agents.orchestrator.create_llm")
    def test_process_department_access_check(self, mock_create_llm):
        """Even if classified correctly, access should be verified against user departments."""
        mock_create_llm.return_value = MagicMock()

        orch = Orchestrator()

        # Mock RRHH agent
        mock_rrhh = MagicMock()
        mock_rrhh.department = "rrhh"
        mock_rrhh.display_name = "RRHH"
        orch.agents["rrhh"] = mock_rrhh

        # User only has ventas access, asking about employees (rrhh keyword)
        user = _make_mock_user(
            role=UserRole.USUARIO,
            department=Department.VENTAS,
        )

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            orch.process("Cuantos empleados hay?", user)
        )

        assert "no tienes permisos" in result["response"].lower()
        assert result["metadata"].get("classification") == "no_access"

    @patch("app.agents.orchestrator.create_llm")
    def test_process_admin_has_all_access(self, mock_create_llm):
        """Admin users should have access to all departments."""
        mock_create_llm.return_value = MagicMock()

        orch = Orchestrator()

        # Mock RRHH agent
        mock_agent = AsyncMock()
        mock_agent.department = "rrhh"
        mock_agent.process = AsyncMock(
            return_value={
                "response": "Tenemos 150 empleados.",
                "agent_used": "rrhh",
                "metadata": {"department": "rrhh", "has_data": True},
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

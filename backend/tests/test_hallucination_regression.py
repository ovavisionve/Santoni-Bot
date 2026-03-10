"""
Tests de regresión anti-alucinación basados en la conversación real del admin (Mar 2026).

Valida:
1. Routing correcto del orchestrator para los 35 escenarios reales
2. Detección de alucinación en base_agent cuando no hay datos
3. Inyección de fecha/hora en el sistema
4. Declaración de capacidades por agente
5. Keywords de ingreso/contratación en RRHH

Ejecutar:
    cd backend && python -m pytest tests/test_hallucination_regression.py -v

NO requiere API key ni conexión a iDempiere.
"""

import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.orchestrator import classify_by_keywords
from app.agents.base_agent import BaseAgent, _build_datetime_context

ALL_DEPARTMENTS = [
    "ventas", "finanzas", "contabilidad", "rrhh",
    "produccion", "compras_insumos", "compras_productores",
]


# ──────────────────────────────────────────────────────────────
# Section 1: Routing tests from real admin conversation (IDs 301-335)
# ──────────────────────────────────────────────────────────────

# (message, expected_agent, is_followup, last_agent_for_followup)
ROUTING_SCENARIOS = [
    # Ventas
    ("Top 10 clientes de este mes", "ventas", False, None),
    ("Dime el ranking de venta por zona", "ventas", True, "ventas"),
    ("Ranking de ventas por zona del mes de enero 2026", "ventas", False, None),
    ("Top 10 mejores vendedores de InproMaiz", "ventas", False, None),
    ("¿Cuánto se facturó en dólares en febrero 2026?", "ventas", False, None),
    ("Top 20 clientes por ventas del 2025", "ventas", False, None),
    ("Top 20 clientes de InproMaiz en febrero 2026", "ventas", False, None),
    ("Top 10 clientes de InproMaíz en enero 2026", "ventas", False, None),

    # RRHH
    ("¿Cuántos empleados activos hay en INPROA SANTONI?", "rrhh", False, None),
    ("¿Cuántos empleados hay por departamento?", "rrhh", True, "rrhh"),
    ("¿Cuántos obreros integrales hay?", "rrhh", False, None),
    ("¿Cuántos choferes tiene la empresa?", "rrhh", False, None),
    ("Indicadores de ausentismo de INPROA SANTONI de septiembre 2025", "rrhh", False, None),
    ("¿Cuántos empleados ingresaron entre enero y junio 2025?", "rrhh", False, None),
    ("Cumpleañeros del mes de marzo", "rrhh", False, None),

    # Finanzas
    ("¿Cuáles son los saldos bancarios actuales?", "finanzas", False, None),
    ("¿Cuánto tenemos en cuentas por cobrar vencidas?", "finanzas", True, "finanzas"),
    ("¿Cuánto debemos en cuentas por pagar?", "finanzas", True, "finanzas"),
    ("¿Cuál es el banco con mayor disponibilidad actualmente?", "finanzas", False, None),
    ("Cuotas de préstamos vencidos a la fecha", "finanzas", False, None),

    # Producción
    ("¿Cuánto se produjo en enero 2026?", "produccion", False, None),
    ("¿Cuáles son las órdenes de producción del mes?", "produccion", False, None),
    ("¿Cuáles son las órdenes de producción del mes de enero de 2026?", "produccion", True, "produccion"),
    ("Dame el Inventario de materia prima actual", "produccion", False, None),
    ("Producción de arroz blanco en enero 2026", "produccion", False, None),
    ("¿Cuánto desperdicio hubo en empaque este mes?", "produccion", False, None),
    ("Inventario de producto terminado actual", "produccion", False, None),

    # Compras insumos
    ("Dame el historial de compras de azúcar del último trimestre", "compras_insumos", False, None),
]


class TestRoutingRegression:
    """Verify orchestrator routes real admin queries to the correct agent."""

    def test_all_routing_scenarios(self):
        """Each scenario must route to the expected agent."""
        failures = []
        for msg, expected, is_followup, last_agent in ROUTING_SCENARIOS:
            result = classify_by_keywords(
                msg,
                allowed_departments=ALL_DEPARTMENTS,
                last_agent=last_agent if is_followup else None,
            )
            if result != expected:
                failures.append(
                    f"  '{msg[:60]}...' → got '{result}', expected '{expected}'"
                )
        assert not failures, (
            f"{len(failures)} routing failures:\n" + "\n".join(failures)
        )


# ──────────────────────────────────────────────────────────────
# Section 2: Follow-up routing (must inherit last_agent)
# ──────────────────────────────────────────────────────────────

FOLLOWUP_SCENARIOS = [
    # Follow-ups that have no department keywords — must inherit from last_agent
    ("Si, de marzo de 2026", "ventas", "ventas"),
    ("Beuno, de febrero de 2026", "ventas", "ventas"),
    ("Puedes hacer este análisis pero por zona?", "ventas", "ventas"),
    ("Me refería al mes de enero de 2026", "produccion", "produccion"),
    ("Disculpa el trimestre a analizar es de, enero a marzo", "compras_insumos", "compras_insumos"),
]


class TestFollowupRouting:
    """Follow-up messages without department keywords should inherit last_agent."""

    def test_followup_inherits_agent(self):
        failures = []
        for msg, expected, last_agent in FOLLOWUP_SCENARIOS:
            result = classify_by_keywords(
                msg,
                allowed_departments=ALL_DEPARTMENTS,
                last_agent=last_agent,
            )
            if result != expected:
                failures.append(
                    f"  '{msg[:60]}' → got '{result}', expected '{expected}' (last={last_agent})"
                )
        assert not failures, (
            f"{len(failures)} follow-up routing failures:\n" + "\n".join(failures)
        )


# ──────────────────────────────────────────────────────────────
# Section 3: Hallucination detection
# ──────────────────────────────────────────────────────────────

class TestHallucinationDetection:
    """Verify BaseAgent._detect_hallucination catches fabricated data."""

    def test_no_hallucination_when_has_data(self):
        """If agent has real data, never flag as hallucination."""
        text = "| Cliente | Monto |\n|---|---|\n| ACME Corp | 1.234.567,89 |"
        assert BaseAgent._detect_hallucination(text, has_data=True) is False

    def test_detects_table_with_numbers_no_data(self):
        """Markdown table with monetary amounts without real data = hallucination."""
        text = (
            "## Top 10 Clientes\n"
            "| Cliente | Monto |\n|---|---|\n"
            "| Empresa A | 1.234.567,89 |\n"
            "| Empresa B | 987.654,32 |"
        )
        assert BaseAgent._detect_hallucination(text, has_data=False) is True

    def test_detects_currency_in_table_no_data(self):
        """Table with Bs. or USD amounts without real data = hallucination."""
        text = "| Banco | Saldo |\n|---|---|\n| Banesco | Bs. 500000 |"
        assert BaseAgent._detect_hallucination(text, has_data=False) is True

        text2 = "| Banco | Saldo |\n|---|---|\n| BOD | USD 12500 |"
        assert BaseAgent._detect_hallucination(text2, has_data=False) is True

    def test_no_false_positive_text_response(self):
        """Plain text response without tables should NOT be flagged."""
        text = (
            "No tengo datos disponibles para ese período. "
            "Intenta con otro mes o reformula tu consulta."
        )
        assert BaseAgent._detect_hallucination(text, has_data=False) is False

    def test_no_false_positive_suggestions(self):
        """Response with suggested queries but no fake numbers should NOT be flagged."""
        text = (
            "No encontré datos. Puedes intentar:\n"
            "- Top 10 clientes de enero 2026\n"
            "- Facturación de febrero 2026"
        )
        assert BaseAgent._detect_hallucination(text, has_data=False) is False


# ──────────────────────────────────────────────────────────────
# Section 4: Date/time context injection
# ──────────────────────────────────────────────────────────────

class TestDatetimeContext:
    """Verify the virtual clock injects the correct date."""

    def test_datetime_context_has_current_year(self):
        ctx = _build_datetime_context()
        from datetime import datetime
        year = datetime.now().year
        assert str(year) in ctx

    def test_datetime_context_has_current_month(self):
        ctx = _build_datetime_context()
        from datetime import datetime
        now = datetime.now()
        # Month names in Spanish
        meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
        }
        expected_month = meses[now.month]
        assert expected_month in ctx

    def test_datetime_context_has_instructions(self):
        ctx = _build_datetime_context()
        assert "actual" in ctx.lower()
        assert "NUNCA" in ctx


# ──────────────────────────────────────────────────────────────
# Section 5: Agent capability declarations
# ──────────────────────────────────────────────────────────────

class TestAgentCapabilities:
    """Verify all agents declare their capabilities honestly."""

    def _get_agent_class(self, name):
        """Import agent class by name without instantiating (avoids LLM init)."""
        if name == "ventas":
            from app.agents.ventas import VentasAgent
            return VentasAgent
        elif name == "finanzas":
            from app.agents.finanzas import FinanzasAgent
            return FinanzasAgent
        elif name == "contabilidad":
            from app.agents.contabilidad import ContabilidadAgent
            return ContabilidadAgent
        elif name == "rrhh":
            from app.agents.rrhh import RRHHAgent
            return RRHHAgent
        elif name == "produccion":
            from app.agents.produccion import ProduccionAgent
            return ProduccionAgent
        elif name == "compras_insumos":
            from app.agents.compras_insumos import ComprasInsumosAgent
            return ComprasInsumosAgent
        elif name == "compras_productores":
            from app.agents.compras_productores import ComprasProductoresAgent
            return ComprasProductoresAgent
        return None

    def test_all_agents_have_get_capabilities(self):
        """Every agent must override get_capabilities() with non-empty content."""
        for name in ALL_DEPARTMENTS:
            cls = self._get_agent_class(name)
            assert cls is not None, f"Could not import agent: {name}"
            # Check the method exists and is overridden (not just BaseAgent's default)
            method = getattr(cls, "get_capabilities", None)
            assert method is not None, f"{name} has no get_capabilities"
            # We can't call it without instantiating (needs LLM), so check it's overridden
            assert method is not BaseAgent.get_capabilities, (
                f"{name} does not override get_capabilities()"
            )

    def test_capabilities_have_can_and_cannot(self):
        """Capabilities should declare both what agent CAN and CANNOT do."""
        for name in ALL_DEPARTMENTS:
            cls = self._get_agent_class(name)
            # Read the source code of get_capabilities
            import inspect
            source = inspect.getsource(cls.get_capabilities)
            assert "✅" in source, f"{name} capabilities missing ✅ (what it CAN do)"
            assert "❌" in source, f"{name} capabilities missing ❌ (what it CANNOT do)"


# ──────────────────────────────────────────────────────────────
# Section 6: RRHH ingreso/contratación keyword detection
# ──────────────────────────────────────────────────────────────

class TestRRHHIngresoKeywords:
    """Verify RRHH agent triggers employee list for ingreso/contratación queries."""

    INGRESO_MESSAGES = [
        "¿Cuántos empleados ingresaron entre enero y junio 2025?",
        "Nuevos ingresos de este mes",
        "Lista de contrataciones de febrero 2026",
        "¿Cuántas contrataciones hubo en 2025?",
        "Empleados que ingresaron en enero",
    ]

    def test_ingreso_routes_to_rrhh(self):
        """Ingreso/contratación queries must route to RRHH."""
        for msg in self.INGRESO_MESSAGES:
            result = classify_by_keywords(msg, ALL_DEPARTMENTS)
            assert result == "rrhh", (
                f"'{msg}' routed to '{result}' instead of 'rrhh'"
            )

    def test_rrhh_fetch_data_has_ingreso_keywords(self):
        """Verify rrhh.py fetch_data includes ingreso/contratación in keyword list."""
        import inspect
        from app.agents.rrhh import RRHHAgent
        source = inspect.getsource(RRHHAgent.fetch_data)
        for kw in ["ingreso", "ingresos", "ingresaron", "contratación", "contratacion"]:
            assert kw in source, (
                f"RRHH fetch_data missing keyword '{kw}' for employee list trigger"
            )


# ──────────────────────────────────────────────────────────────
# Section 7: Production-specific routing
# ──────────────────────────────────────────────────────────────

class TestProductionRouting:
    """Production queries must NOT go to ventas or finanzas."""

    PRODUCTION_MESSAGES = [
        "¿Cuánto se produjo en enero 2026?",
        "Inventario de materia prima actual",
        "Inventario de producto terminado actual",
        "Producción de arroz blanco en enero 2026",
        "¿Cuánto desperdicio hubo en empaque este mes?",
        "¿Cuáles son las órdenes de producción del mes?",
    ]

    def test_production_never_goes_to_ventas(self):
        for msg in self.PRODUCTION_MESSAGES:
            result = classify_by_keywords(msg, ALL_DEPARTMENTS)
            assert result != "ventas", (
                f"'{msg}' incorrectly routed to 'ventas' instead of 'produccion'"
            )

    def test_production_routes_correctly(self):
        for msg in self.PRODUCTION_MESSAGES:
            result = classify_by_keywords(msg, ALL_DEPARTMENTS)
            assert result == "produccion", (
                f"'{msg}' routed to '{result}' instead of 'produccion'"
            )


# ──────────────────────────────────────────────────────────────
# Allow running without pytest
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))

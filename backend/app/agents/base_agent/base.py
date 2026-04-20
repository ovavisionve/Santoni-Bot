"""BaseAgent class — orchestrates system prompt, data fetch, LLM call, and
hallucination validation for each department agent.

Supports both full-response (process) and streaming (stream) modes.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.config import get_settings
from app.services.llm_factory import create_llm

from .datetime_ctx import _build_datetime_context
from .formatting import MAX_TABLE_ROWS, format_summary, format_table
from .hallucination import HALLUCINATION_REPLACEMENT, detect_hallucination
from .history_sanitize import clean_corrupted_response, strip_tables_from_history

settings = get_settings()
logger = logging.getLogger("santonibot.agents")

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
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        ...

    @property
    @abstractmethod
    def department(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        ...

    @abstractmethod
    def get_sql_context(self) -> str:
        ...

    def fetch_data(
        self,
        message: str,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> str | None:
        """Override in subclasses for department-specific data fetching."""
        return None

    def get_capabilities(self) -> str:
        return ""

    def _build_messages(
        self,
        message: str,
        history: list[tuple[str, str]] | None = None,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
    ) -> tuple[list, bool]:
        """Build the LLM message list. Returns (messages, has_data)."""
        datetime_ctx = _build_datetime_context()

        capabilities = self.get_capabilities()
        capabilities_block = f"\n\n{capabilities}\n" if capabilities else ""

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
            "- Presenta SOLO los datos que recibes en 'DATOS REALES DE LA BASE DE DATOS'. NO agregues datos adicionales.\n"
            "- Si quieres mostrar un porcentaje, CALCÚLALO de los datos reales (ej: valor/total*100).\n"
            "- NUNCA digas 'vs mes anterior' o 'comparativo' si NO tienes datos de ambos períodos.\n"
            "- NUNCA agregues secciones de 'Recomendaciones' o 'Plan de acción' con información inventada.\n"
            "- NUNCA inventes nombres de clientes, proveedores, empleados, productos ni montos.\n"
            "- NUNCA inventes números de factura (FAC-xxxx), números de lote, porcentajes de humedad ni precios.\n"
            "- Las únicas sugerencias permitidas son consultas que el sistema realmente puede ejecutar.\n"
            "- Si los datos muestran un solo período, NO inventes comparativos con otros períodos.\n"
            "- PROHIBIDO copiar nombres o datos del historial de conversación para responder una nueva consulta.\n"
            "- Cada respuesta debe basarse EXCLUSIVAMENTE en los 'DATOS REALES' proporcionados para ESA consulta.\n"
            "- Si los datos muestran 5 empleados, tu tabla debe tener EXACTAMENTE 5 filas, ni más ni menos.\n"
        )
        messages = [SystemMessage(content=enhanced_prompt)]

        try:
            from app.services.data_catalog import get_catalog_service
            catalog = get_catalog_service()
            catalog_context = catalog.get_department_context(self.department)
            if catalog_context:
                messages.append(SystemMessage(content=catalog_context))
        except Exception as exc:
            logger.debug("Data catalog unavailable for %s: %s", self.name, exc)

        try:
            from app.services.rag_service import get_rag_service
            rag = get_rag_service()
            rag_context = rag.get_context_for_agent(self.department, message)
            if rag_context:
                messages.append(SystemMessage(content=rag_context))
        except Exception as exc:
            logger.debug("RAG context unavailable for %s: %s", self.name, exc)

        try:
            from app.utils.sentry_utils import (
                set_agent_context,
                track_query_performance,
            )
            set_agent_context(self.name)
            with track_query_performance(self.name, f"{self.name}.fetch_data"):
                data_context = self.fetch_data(
                    message, org_ids=org_ids,
                    salesrep_id=salesrep_id, history=history,
                )
        except Exception as exc:
            logger.error(
                "Error in %s.fetch_data: %s: %s",
                self.name, type(exc).__name__, exc, exc_info=True,
            )
            try:
                from app.utils.sentry_utils import capture_agent_error
                capture_agent_error(self.name, exc, {
                    "message": message,
                    "department": self.department,
                })
            except Exception:
                pass
            data_context = (
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Informa al usuario que hubo un problema de conexión con la base de datos "
                f"y que intente de nuevo en unos momentos."
            )

        if data_context:
            data_lines = data_context.split("\n")
            data_row_count = sum(
                1 for line in data_lines
                if line.strip().startswith("|")
                and "---" not in line
                and not any(h in line.lower() for h in [
                    "nombre", "codigo", "producto", "proveedor", "concepto",
                    "organizacion", "zona", "banco", "moneda", "cargo",
                    "departamento", "tipo", "estado", "factura", "documento",
                ])
            )
            row_enforcement = ""
            if data_row_count > 0:
                row_enforcement = (
                    f"- CONTEO EXACTO: Los datos contienen {data_row_count} filas de datos. "
                    f"Tu respuesta debe contener EXACTAMENTE {data_row_count} filas de datos, NI UNA MÁS.\n"
                    f"- NUNCA escribas '(Mostrando X de Y registros)' a menos que ESE TEXTO ya aparezca en los datos.\n"
                )

            messages.append(
                SystemMessage(
                    content=(
                        "══════════ DATOS REALES DE LA BASE DE DATOS ══════════\n"
                        "⚠️ INSTRUCCIÓN CRÍTICA: Usa EXCLUSIVAMENTE estos datos para responder.\n"
                        "- NO agregues filas, columnas, nombres, montos ni porcentajes que NO estén aquí.\n"
                        f"{row_enforcement}"
                        "- Si los datos muestran 0 para un campo, muestra 0. NUNCA inventes un valor.\n"
                        "- NO copies datos del historial de conversación para complementar.\n"
                        "- Si falta información que el usuario pidió, di 'no se encontraron datos' y sugiere alternativas.\n"
                        "- PROHIBIDO inventar nombres de personas, empresas, facturas, lotes o buques.\n"
                        "- PROHIBIDO mostrar porcentajes de humedad, proteína o impureza si NO aparecen en los datos.\n"
                        "══════════════════════════════════════════════════════\n\n"
                        f"{data_context}"
                    )
                )
            )
        else:
            sql_context = self.get_sql_context()
            messages.append(
                SystemMessage(
                    content=(
                        "⚠️ INSTRUCCIÓN OBLIGATORIA — LA CONSULTA NO ARROJÓ RESULTADOS ⚠️\n\n"
                        "La consulta a la base de datos se ejecutó correctamente pero no arrojó "
                        "resultados para los filtros aplicados (período, producto, organización, etc.).\n\n"
                        "Tu ÚNICA respuesta permitida es:\n"
                        "1. Informar que la consulta no arrojó resultados para ese período/filtro específico.\n"
                        "2. Sugerir alternativas: otro período, otro filtro, o reformular la pregunta.\n"
                        "3. NUNCA digas 'no tengo acceso' ni 'no puedo consultar' — SÍ tienes acceso, "
                        "simplemente no hay registros que coincidan con los filtros.\n\n"
                        "PROHIBIDO TERMINANTEMENTE:\n"
                        "- NO generes tablas con datos numéricos inventados.\n"
                        "- NO inventes nombres de clientes, proveedores, empleados ni productos.\n"
                        "- NO muestres montos, porcentajes ni cifras que no provengan de los datos.\n"
                        "- NO digas 'no tengo acceso', 'no puedo consultar', 'no dispongo de esa información'.\n"
                        "- La base de datos SÍ está conectada y SÍ se ejecutó la consulta.\n\n"
                        + (f"Esquema disponible para referencia:\n{sql_context}" if sql_context else "")
                    )
                )
            )

        if history:
            for role, content in history[-_MAX_HISTORY_MESSAGES:]:
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    clean = clean_corrupted_response(content)
                    clean = strip_tables_from_history(clean)
                    messages.append(AIMessage(content=clean))

        messages.append(HumanMessage(content=message))
        return messages, data_context is not None

    # --- Static helpers kept on the class for backward compat -----------
    # Tests and other modules call BaseAgent._detect_hallucination,
    # BaseAgent._format_table, self._format_summary, etc. Re-bind as
    # staticmethods so public API is preserved after the split.
    _detect_hallucination = staticmethod(detect_hallucination)
    _clean_corrupted_response = staticmethod(clean_corrupted_response)
    _strip_tables_from_history = staticmethod(strip_tables_from_history)
    _format_table = staticmethod(format_table)
    _format_summary = staticmethod(format_summary)
    _HALLUCINATION_REPLACEMENT = HALLUCINATION_REPLACEMENT

    async def process(
        self,
        message: str,
        history: list[tuple[str, str]] | None = None,
        user_departments: list[str] | None = None,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
    ) -> dict:
        """Process a user message and return a complete response."""
        messages, has_data = self._build_messages(
            message, history, org_ids, salesrep_id,
        )
        response = await self.llm.ainvoke(messages)

        response_text = response.content

        if detect_hallucination(response_text, has_data):
            logger.warning(
                "Hallucination detected in %s (has_data=%s). Replacing response.",
                self.name, has_data,
            )
            try:
                from app.utils.sentry_utils import add_breadcrumb
                add_breadcrumb(
                    category="agent",
                    message=f"Hallucination detected in {self.name}",
                    level="warning",
                    data={"agent": self.name, "has_data": has_data},
                )
            except Exception:
                pass
            response_text = HALLUCINATION_REPLACEMENT

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
        """Stream response tokens for real-time display.

        Includes post-stream hallucination detection: accumulates the full
        response and, if hallucination is detected, logs for monitoring
        (tokens can't be un-sent).
        """
        messages, has_data = self._build_messages(
            message, history, org_ids, salesrep_id,
        )
        accumulated: list[str] = []
        async for chunk in self.llm.astream(messages):
            if chunk.content:
                accumulated.append(chunk.content)
                yield chunk.content

        if not has_data and accumulated:
            full_response = "".join(accumulated)
            if detect_hallucination(full_response, has_data):
                logger.warning(
                    "Hallucination detected in streamed %s (has_data=%s).",
                    self.name, has_data,
                )


# Re-export for external code that imports from app.agents.base_agent
__all__ = ["BaseAgent", "MAX_TABLE_ROWS"]

"""
Orchestrator: Classifies user intent and routes to the appropriate agent.
This is the central brain of SantoniBot that decides which specialist handles each query.

Performance: Uses keyword-based classification (~0ms) instead of LLM classification (~30s).
"""

import logging
import re
from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.config import get_settings
from app.services.llm_factory import create_llm, is_claude_available
from app.models.user import User
from app.agents.finanzas import FinanzasAgent
from app.agents.contabilidad import ContabilidadAgent
from app.agents.ventas import VentasAgent
from app.agents.rrhh import RRHHAgent
from app.agents.produccion import ProduccionAgent
from app.agents.compras_insumos import ComprasInsumosAgent
from app.agents.compras_productores import ComprasProductoresAgent

settings = get_settings()
logger = logging.getLogger("santonibot.orchestrator")

# ──────────────────────────────────────────────────────────────────
# Keyword-based classifier – instant routing, no LLM call needed
# ──────────────────────────────────────────────────────────────────

# Order matters: more specific patterns first, broader ones last.
# Each entry: (agent_name, [keyword_patterns])
# A pattern matches if ANY keyword in it appears in the lowercased message.
_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    # Compras a productores (before generic "compra")
    ("compras_productores", [
        "productor", "productores", "arroz paddy", "maiz blanco",
        "arroz acondicionado", "guia de compra", "guias de compra",
        "compra de arroz", "compra de maiz", "compra de maíz",
        "compras a productor", "precio del arroz", "precio del maiz",
        "precio del maíz", "tonelada", "kilogramo",
    ]),
    # Compras de insumos (before generic "compra")
    ("compras_insumos", [
        "insumo", "proveedor", "proveedores", "orden de compra",
        "ordenes de compra", "inventario de material", "material",
        "compra de insumo", "compras insumo", "suministro",
        "tiempo de entrega",
    ]),
    # Ventas – broad keywords
    ("ventas", [
        "venta", "ventas", "vendedor", "vendedores", "cliente",
        "clientes", "factura", "facturación", "facturacion",
        "cobranza", "cobro", "cobrar", "recaudacion", "recaudación",
        "zona", "zonas", "ranking", "pareto", "top clientes",
        "top 10", "top 20", "top 5", "mejores clientes",
        "metas de venta", "meta de venta", "cotizacion", "cotización",
        "moroso", "morosos", "deuda", "deudas", "vencido", "vencida",
        "pendiente de cobro", "cuentas por cobrar",
    ]),
    # Finanzas
    ("finanzas", [
        "finanza", "financiero", "financiera", "flujo de caja",
        "banco", "bancos", "saldo bancario", "saldos",
        "cuenta por pagar", "cuentas por pagar",
        "presupuesto", "rentabilidad", "liquidez",
        "estado de flujo", "indicador financiero",
    ]),
    # Contabilidad
    ("contabilidad", [
        "contab", "balance general", "balance de comprobacion",
        "estado de resultado", "libro diario", "libro mayor",
        "impuesto", "iva", "islr", "retencion", "retención",
        "activo fijo", "activos fijos", "depreciacion", "depreciación",
        "asiento contable", "plan de cuenta", "partida",
    ]),
    # RRHH
    ("rrhh", [
        "nomina", "nómina", "empleado", "empleados", "personal",
        "vacacion", "vacaciones", "asistencia", "inasistencia",
        "evaluacion", "evaluación", "cumpleaño", "cumpleaños",
        "salario", "sueldo", "recurso humano", "recursos humanos",
        "rrhh", "talento humano", "contrato", "liquidacion",
        "liquidación", "prestacion", "prestación",
    ]),
    # Producción
    ("produccion", [
        "produccion", "producción", "producir", "planta",
        "eficiencia", "oee", "desperdicio", "merma",
        "mantenimiento", "turno", "turnos", "lote", "lotes",
        "orden de produccion", "orden de producción",
        "producto terminado", "empaque", "envasado",
    ]),
]

# Greetings / general patterns
_GENERAL_PATTERNS = [
    "hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches",
    "gracias", "ayuda", "que puedes hacer", "qué puedes hacer",
    "quien eres", "quién eres", "como funciona", "cómo funciona",
]


def classify_by_keywords(message: str, allowed_departments: list[str]) -> str:
    """
    Classify a message by scanning for department-specific keywords.
    Returns the agent name or "general" if no match found.
    Returns "no_access" if the matched department is not in allowed list.
    ~0ms execution time.
    """
    msg = message.lower()

    # Check greetings / general first
    if any(p in msg for p in _GENERAL_PATTERNS) and len(msg) < 60:
        return "general"

    # Scan keyword rules
    for agent_name, keywords in _KEYWORD_RULES:
        if any(kw in msg for kw in keywords):
            # Check access
            dept = agent_name
            if dept == "compras_productores" or dept == "compras_insumos":
                dept_check = dept
            else:
                dept_check = dept

            if dept_check not in allowed_departments:
                return "no_access"
            return agent_name

    # Fallback: if message is a question about data, try ventas as default
    # (most common department at Santoni)
    if any(w in msg for w in ["cuanto", "cuánto", "cuál", "cual", "dame", "muestra", "reporte"]):
        if "ventas" in allowed_departments:
            return "ventas"

    return "general"


class Orchestrator:
    """Routes user queries to the appropriate specialized agent."""

    def __init__(self):
        self.general_llm = create_llm(
            temperature=0.3,
            max_tokens=1024,
            purpose="general",
        )

        # Initialize all agents
        self.agents = {
            "finanzas": FinanzasAgent(),
            "contabilidad": ContabilidadAgent(),
            "ventas": VentasAgent(),
            "rrhh": RRHHAgent(),
            "produccion": ProduccionAgent(),
            "compras_insumos": ComprasInsumosAgent(),
            "compras_productores": ComprasProductoresAgent(),
        }

    async def classify(self, message: str, allowed_departments: list[str]) -> str:
        """Classify user intent using keyword matching (instant)."""
        return classify_by_keywords(message, allowed_departments)

    async def process(
        self,
        message: str,
        user: User,
        history: list[tuple[str, str]] | None = None,
        document: dict | None = None,
    ) -> dict:
        """Process a user message through the appropriate agent."""

        # If a document is attached, route to document handler
        if document:
            return await self._handle_document(message, document, history)

        allowed = user.allowed_departments

        # Classify the query (instant keyword match)
        agent_name = await self.classify(message, allowed)
        logger.info("Classified '%s' → %s", message[:60], agent_name)

        # Handle access denied
        if agent_name == "no_access":
            return {
                "response": (
                    "Lo siento, no tienes permisos para acceder a la información "
                    "de ese departamento. Contacta a tu administrador si necesitas "
                    "acceso adicional."
                ),
                "agent_used": "orchestrator",
                "metadata": {"classification": "no_access"},
            }

        # Handle general queries
        if agent_name == "general":
            return await self._handle_general(message, history)

        # Route to specialized agent
        agent = self.agents[agent_name]

        # Verify department access
        if agent.department not in allowed:
            return {
                "response": (
                    f"No tienes acceso al departamento de {agent.display_name}. "
                    "Contacta a tu administrador."
                ),
                "agent_used": "orchestrator",
                "metadata": {"classification": agent_name, "access_denied": True},
            }

        result = await agent.process(
            message=message,
            history=history,
            user_departments=allowed,
            org_ids=user.org_ids,
            salesrep_id=user.idempiere_salesrep_id,
        )
        return result

    async def stream(
        self,
        message: str,
        user: User,
        history: list[tuple[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens via the appropriate agent."""
        allowed = user.allowed_departments
        agent_name = await self.classify(message, allowed)
        logger.info("Stream classified '%s' → %s", message[:60], agent_name)

        if agent_name == "no_access":
            yield "Lo siento, no tienes permisos para acceder a la información de ese departamento."
            return

        if agent_name == "general":
            async for token in self._stream_general(message, history):
                yield token
            return

        agent = self.agents[agent_name]
        if agent.department not in allowed:
            yield f"No tienes acceso al departamento de {agent.display_name}."
            return

        async for token in agent.stream(
            message=message,
            history=history,
            user_departments=allowed,
            org_ids=user.org_ids,
            salesrep_id=user.idempiere_salesrep_id,
        ):
            yield token

    async def get_stream_agent_name(
        self, message: str, user: User
    ) -> str:
        """Return the agent name for a message (for metadata after streaming)."""
        allowed = user.allowed_departments
        return await self.classify(message, allowed)

    async def _handle_document(
        self,
        message: str,
        document: dict,
        history: list[tuple[str, str]] | None,
    ) -> dict:
        """Analyze an attached document. Tries Claude first, falls back to Groq."""
        log = logging.getLogger("santonibot.orchestrator")

        system_msg = SystemMessage(
            content=(
                "Eres SantoniBot, el asistente inteligente de Alimentos Santoni, C.A. "
                "El usuario te ha adjuntado un documento para análisis. "
                "Analiza el contenido detalladamente y responde la consulta del usuario. "
                "Si hay tablas o datos numéricos, preséntalos en formato de tabla markdown. "
                "Responde siempre en español."
            )
        )

        is_image = document["type"] == "image"
        msgs = [system_msg]

        if history:
            for role, content in history[-4:]:
                if role == "user":
                    msgs.append(HumanMessage(content=content))
                elif role == "assistant":
                    msgs.append(AIMessage(content=content))

        if is_image:
            user_content = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{document['mime_type']};base64,{document['content']}"
                    },
                },
                {"type": "text", "text": message or "Analiza esta imagen."},
            ]
            msgs.append(HumanMessage(content=user_content))
        else:
            doc_text = document["content"]
            if len(doc_text) > 30000:
                doc_text = doc_text[:30000] + "\n\n... (documento truncado por tamaño)"
            user_text = (
                f"DOCUMENTO ADJUNTO ({document.get('filename', 'archivo')}):\n"
                f"---\n{doc_text}\n---\n\n"
                f"Consulta del usuario: {message or 'Analiza este documento.'}"
            )
            msgs.append(HumanMessage(content=user_text))

        # Try Claude first if available
        if is_claude_available():
            try:
                from langchain_anthropic import ChatAnthropic

                claude_kwargs: dict = {
                    "api_key": get_settings().anthropic_api_key,
                    "model": get_settings().anthropic_model,
                    "temperature": 0.1,
                    "max_tokens": 4096,
                }
                if get_settings().anthropic_base_url:
                    claude_kwargs["anthropic_api_url"] = get_settings().anthropic_base_url
                claude_llm = ChatAnthropic(**claude_kwargs)
                log.info("Trying Claude (%s) for document analysis", get_settings().anthropic_model)
                response = await claude_llm.ainvoke(msgs)
                log.info("Claude document analysis succeeded")
                return {
                    "response": response.content,
                    "agent_used": "document_analysis",
                    "metadata": {
                        "classification": "document",
                        "provider": "anthropic",
                        "filename": document.get("filename"),
                    },
                }
            except Exception as e:
                log.warning("Claude failed for document analysis: %s", str(e))
                if is_image:
                    return {
                        "response": (
                            "No se pudo analizar la imagen. El análisis de imágenes "
                            "requiere Claude API. Verifica que tu API Key esté activa."
                        ),
                        "agent_used": "orchestrator",
                        "metadata": {"classification": "document_error"},
                    }
                log.info("Falling back to Groq for document analysis")

        if is_image and not is_claude_available():
            return {
                "response": (
                    "El análisis de imágenes requiere la API de Claude (Anthropic). "
                    "Puedes adjuntar documentos de texto (PDF, Excel, Word, CSV)."
                ),
                "agent_used": "orchestrator",
                "metadata": {"classification": "document_no_image_support"},
            }

        groq_llm = create_llm(temperature=0.1, max_tokens=4096, purpose="document_analysis")
        response = await groq_llm.ainvoke(msgs)

        return {
            "response": response.content,
            "agent_used": "document_analysis",
            "metadata": {"classification": "document", "provider": "groq", "filename": document.get("filename")},
        }

    async def _handle_general(
        self, message: str, history: list[tuple[str, str]] | None
    ) -> dict:
        """Handle general queries that don't map to a specific department."""
        messages = [
            SystemMessage(
                content=(
                    "Eres SantoniBot, el asistente inteligente de Alimentos Santoni. "
                    "Responde de forma amable y profesional en español. "
                    "Si el usuario saluda, preséntate brevemente. "
                    "Si pregunta sobre el sistema, explica que puedes ayudar con consultas "
                    "de Finanzas, Contabilidad, Ventas, RRHH, Producción, Compras de Insumos "
                    "y Compras a Productores. "
                    "Sé conciso."
                )
            )
        ]

        if history:
            for role, content in history[-4:]:
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=message))
        response = await self.general_llm.ainvoke(messages)

        return {
            "response": response.content,
            "agent_used": "general",
            "metadata": {"classification": "general"},
        }

    async def _stream_general(
        self, message: str, history: list[tuple[str, str]] | None
    ) -> AsyncIterator[str]:
        """Stream general responses."""
        messages = [
            SystemMessage(
                content=(
                    "Eres SantoniBot, el asistente inteligente de Alimentos Santoni. "
                    "Responde de forma amable y profesional en español. "
                    "Sé conciso."
                )
            )
        ]
        if history:
            for role, content in history[-4:]:
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=message))

        async for chunk in self.general_llm.astream(messages):
            if chunk.content:
                yield chunk.content

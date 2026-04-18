"""Orchestrator class: routes user messages to specialized agents."""

import logging
from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.config import get_settings
from app.services.llm_factory import create_llm, is_claude_available
from app.models.user import User
from app.agents.base_agent import _build_datetime_context
from app.agents.finanzas import FinanzasAgent
from app.agents.contabilidad import ContabilidadAgent
from app.agents.ventas import VentasAgent
from app.agents.rrhh import RRHHAgent
from app.agents.produccion import ProduccionAgent
from app.agents.compras_insumos import ComprasInsumosAgent
from app.agents.compras_productores import ComprasProductoresAgent

from .classifier import (
    classify_by_keywords,
    classify_with_capabilities,
    classify_with_confidence,
    compute_confidence_score,
    should_try_sql_direct,
)

logger = logging.getLogger("santonibot.orchestrator")
settings = get_settings()


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

    async def _try_sql_direct(
        self,
        message: str,
        user: User,
        history: list[tuple[str, str]] | None,
    ) -> dict | None:
        """Intenta responder con SQL Directo (Claude en modo híbrido).

        Gate único para process() y stream() — antes había duplicación literal
        en ambos métodos que se desincronizaba silenciosamente.

        Retorna:
          - dict con `response`, `metadata`, `confidence_score` si tuvo éxito
          - None si no aplica (saludo/follow-up corto), si el LLM declinó,
            si la validación SQL falló, o si hubo error de ejecución.
            El caller debe caer al flujo de agentes clásicos en ese caso.
        """
        if not should_try_sql_direct(message):
            return None

        try:
            from app.services.sql_direct import process_with_sql_direct
            sql_result = await process_with_sql_direct(
                message=message,
                history=history,
                org_ids=user.org_ids,
            )
        except Exception as exc:
            logger.warning("SQL Direct failed, falling back to agents: %s", exc)
            return None

        if sql_result is None:
            return None

        logger.info(
            "SQL Direct handled: '%s' → %d rows",
            message[:60],
            sql_result.get("metadata", {}).get("rows_returned", 0),
        )
        # Enriquece con confidence score (antes solo process() lo hacía,
        # stream() lo descartaba silenciosamente)
        sql_result["confidence_score"] = 1.0
        sql_result["score_breakdown"] = {
            "routing": 1.0,
            "data": 1.0 if sql_result.get("metadata", {}).get("has_data") else 0.2,
            "overall": 1.0,
            "match_type": "sql_direct",
        }
        return sql_result

    async def classify(
        self, message: str, allowed_departments: list[str], last_agent: str | None = None,
    ) -> str:
        """Classify user intent using keyword matching (instant)."""
        return classify_by_keywords(message, allowed_departments, last_agent=last_agent)

    async def process(
        self,
        message: str,
        user: User,
        history: list[tuple[str, str]] | None = None,
        last_agent: str | None = None,
        document: dict | None = None,
    ) -> dict:
        """Process a user message through the appropriate agent."""

        # If a document is attached, route to document handler
        if document:
            return await self._handle_document(message, document, history)

        # ── SQL DIRECT: intenta responder con SQL generado por el LLM ──
        # Si aplica y tiene éxito, retorna directo. Si no, cae al flujo normal.
        sql_result = await self._try_sql_direct(message, user, history)
        if sql_result is not None:
            return sql_result

        # ── FLUJO NORMAL: routing por keywords → agente especializado ──
        allowed = user.allowed_departments
        user_caps = user.capability_ids  # set[str] | None

        # Use capability-based routing if user has capabilities synced
        if user_caps is not None or user.ad_user_id is not None:
            agent_name, cap_id, routing_score, match_type = classify_with_capabilities(
                message, user_caps, allowed, last_agent=last_agent,
            )
            logger.info(
                "Classified '%s' → %s [cap=%s] (score=%.1f, type=%s)",
                message[:60], agent_name, cap_id, routing_score, match_type,
            )
        else:
            # Legacy: keyword-only routing for users without iDempiere link
            agent_name, routing_score, match_type = classify_with_confidence(
                message, allowed, last_agent=last_agent,
            )
            cap_id = None
            logger.info(
                "Classified '%s' → %s (score=%.1f, type=%s)",
                message[:60], agent_name, routing_score, match_type,
            )

        # Handle access denied
        if agent_name == "no_access":
            score, breakdown = compute_confidence_score(routing_score, False, "orchestrator")
            return {
                "response": (
                    "Lo siento, no tienes permisos para acceder a la información "
                    "de ese departamento. Contacta a tu administrador si necesitas "
                    "acceso adicional."
                ),
                "agent_used": "orchestrator",
                "metadata": {"classification": "no_access", "match_type": match_type},
                "confidence_score": score,
                "score_breakdown": breakdown,
            }

        # Handle general queries
        if agent_name == "general":
            result = await self._handle_general(message, history)
            score, breakdown = compute_confidence_score(routing_score, False, "general")
            result["confidence_score"] = score
            result["score_breakdown"] = {**breakdown, "match_type": match_type}
            return result

        # Route to specialized agent
        agent = self.agents[agent_name]

        # Verify department access
        if agent.department not in allowed:
            score, breakdown = compute_confidence_score(routing_score, False, "orchestrator")
            return {
                "response": (
                    f"No tienes acceso al departamento de {agent.display_name}. "
                    "Contacta a tu administrador."
                ),
                "agent_used": "orchestrator",
                "metadata": {"classification": agent_name, "access_denied": True, "match_type": match_type},
                "confidence_score": score,
                "score_breakdown": breakdown,
            }

        result = await agent.process(
            message=message,
            history=history,
            user_departments=allowed,
            org_ids=user.org_ids,
            salesrep_id=user.idempiere_salesrep_id,
        )

        # Compute confidence score based on routing + data availability
        has_data = result.get("metadata", {}).get("has_data", False)
        score, breakdown = compute_confidence_score(routing_score, has_data, agent_name)
        result["confidence_score"] = score
        result["score_breakdown"] = {**breakdown, "match_type": match_type}
        return result

    async def stream(
        self,
        message: str,
        user: User,
        history: list[tuple[str, str]] | None = None,
        last_agent: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens via the appropriate agent."""

        # ── SQL DIRECT: intenta responder con SQL generado por el LLM ──
        # Usa el mismo helper que process() para garantizar paridad total
        # (pre-checks, score, logging) entre ambos paths.
        sql_result = await self._try_sql_direct(message, user, history)
        if sql_result is not None:
            yield sql_result["response"]
            return


        # ── FLUJO NORMAL: routing por keywords → agente streaming ──
        allowed = user.allowed_departments
        user_caps = user.capability_ids

        if user_caps is not None or user.ad_user_id is not None:
            agent_name, _cap_id, _score, _mt = classify_with_capabilities(
                message, user_caps, allowed, last_agent=last_agent,
            )
        else:
            agent_name = await self.classify(message, allowed, last_agent=last_agent)
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
        self, message: str, user: User, last_agent: str | None = None,
    ) -> tuple[str, float, str]:
        """Return (agent_name, confidence_score, match_type) for a message."""
        allowed = user.allowed_departments
        user_caps = user.capability_ids
        if user_caps is not None or user.ad_user_id is not None:
            agent_name, _cap_id, score, match_type = classify_with_capabilities(
                message, user_caps, allowed, last_agent=last_agent,
            )
            return agent_name, score, match_type
        return classify_with_confidence(message, allowed, last_agent=last_agent)

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
            for role, content in history[-20:]:
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
        datetime_ctx = _build_datetime_context()
        messages = [
            SystemMessage(
                content=(
                    "Eres SantoniBot, el asistente inteligente de Alimentos Santoni, C.A. "
                    "Responde de forma amable y profesional en español. "
                    "Si el usuario saluda, preséntate brevemente y menciona que puedes ayudar con consultas "
                    "de Finanzas, Contabilidad, Ventas, RRHH, Producción, Compras de Insumos "
                    "y Compras a Productores. "
                    f"\n{datetime_ctx}\n"
                    "IMPORTANTE: Si el usuario hace una referencia a algo anterior en la conversación "
                    "(como '¿y por zona?', '¿y del mes pasado?', 'dame más detalle'), "
                    "analiza el historial para entender el contexto completo de lo que pide. "
                    "REGLA CRÍTICA: NUNCA inventes datos, cifras, fechas de fundación, ni información "
                    "que no esté en los datos proporcionados o en el historial de la conversación. "
                    "Si no tienes la información, di claramente: 'No tengo esa información disponible'. "
                    "NO inventes números, porcentajes, ni fechas aproximadas. "
                    # RRHH-101 parte B (09/Abr/2026): regresión del fix RRHH-001 — el agente
                    # general no tenía la prohibición de "no tengo acceso" que sí tienen los
                    # 7 agentes especializados. Cuando el orchestrator rutea mal una pregunta
                    # de cumpleaños/empleados a general, este agente respondía con "no tengo
                    # acceso" y violaba la regla global.
                    "PROHIBIDO decir frases como 'no tengo acceso', 'no puedo acceder', "
                    "'no dispongo de esa información', 'no tengo permisos', 'no tengo "
                    "acceso directo'. Si la pregunta es sobre datos del bot (empleados, "
                    "ventas, compras, finanzas, etc.) y llegó a este agente porque el "
                    "router no la pudo clasificar, responde: 'Esa consulta requiere más "
                    "contexto. Reformúlala mencionando: el agente o tema (ej: empleados, "
                    "facturas, compras), el período (mes/año) y la organización si aplica.' "
                    "Sé conciso."
                )
            )
        ]

        if history:
            for role, content in history[-20:]:
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
        datetime_ctx = _build_datetime_context()
        messages = [
            SystemMessage(
                content=(
                    "Eres SantoniBot, el asistente inteligente de Alimentos Santoni. "
                    "Responde de forma amable y profesional en español. "
                    f"\n{datetime_ctx}\n"
                    "NUNCA inventes datos, cifras ni fechas. Si no tienes la información, "
                    "di claramente que no la tienes disponible. "
                    # RRHH-101 parte B: misma regla que en _handle_general (consistencia).
                    "PROHIBIDO decir frases como 'no tengo acceso', 'no puedo acceder', "
                    "'no dispongo de esa información', 'no tengo permisos', 'no tengo "
                    "acceso directo'. Si la pregunta es sobre datos del bot (empleados, "
                    "ventas, compras, finanzas, etc.), responde: 'Esa consulta requiere "
                    "más contexto. Reformúlala mencionando el tema, período y organización.' "
                    "Sé conciso."
                )
            )
        ]
        if history:
            for role, content in history[-20:]:
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=message))

        async for chunk in self.general_llm.astream(messages):
            if chunk.content:
                yield chunk.content

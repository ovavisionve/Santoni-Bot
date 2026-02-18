"""
Orchestrator: Classifies user intent and routes to the appropriate agent.
This is the central brain of SantoniBot that decides which specialist handles each query.
"""

from langchain_core.messages import HumanMessage, SystemMessage

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

CLASSIFICATION_PROMPT = """Eres el orquestador de SantoniBot, un sistema de IA empresarial para Alimentos Santoni.
Tu trabajo es clasificar la consulta del usuario y determinar a cuál agente especializado debe dirigirse.

Los agentes disponibles son:
- finanzas: Flujo de caja, cuentas por cobrar/pagar, bancos, presupuestos, indicadores financieros, rentabilidad
- contabilidad: Balance general, estado de resultados, libro diario/mayor, impuestos, activos fijos
- ventas: Clientes, facturación, ranking de ventas por zona/vendedor, cobranza, metas, productos vendidos, cotizaciones
- rrhh: Nómina, vacaciones, asistencia, datos de empleados, evaluaciones, cumpleaños
- produccion: Producción diaria, órdenes de producción, eficiencia (OEE), desperdicios, mantenimientos, turnos
- compras_insumos: Órdenes de compra de insumos, proveedores, inventarios de materiales, precios, tiempos de entrega
- compras_productores: Compras a productores agrícolas (arroz, maíz), volúmenes, precios por kilo/tonelada, pagos pendientes, productores registrados
- general: Saludos, preguntas generales sobre el sistema, consultas que no encajan en ningún departamento

El usuario tiene acceso a estos departamentos: {departments}

IMPORTANTE: Si el usuario pregunta sobre un departamento al que NO tiene acceso, responde "NO_ACCESS".

Responde ÚNICAMENTE con el nombre del agente (una sola palabra, todo en minúsculas).
No agregues explicación ni texto adicional.

Consulta del usuario: {message}"""


class Orchestrator:
    """Routes user queries to the appropriate specialized agent."""

    def __init__(self):
        self.classifier = create_llm(
            temperature=0,
            max_tokens=50,
            purpose="classifier",
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
        """Classify user intent and return the target agent name."""
        prompt = CLASSIFICATION_PROMPT.format(
            departments=", ".join(allowed_departments),
            message=message,
        )

        response = await self.classifier.ainvoke(
            [SystemMessage(content=prompt), HumanMessage(content=message)]
        )

        agent_name = response.content.strip().lower().replace('"', "").replace("'", "")

        # Validate classification
        if agent_name == "no_access":
            return "no_access"
        if agent_name in self.agents:
            return agent_name
        return "general"

    async def process(
        self,
        message: str,
        user: User,
        history: list[tuple[str, str]] | None = None,
        document: dict | None = None,
    ) -> dict:
        """Process a user message through the appropriate agent."""

        # If a document is attached, route to document handler
        # (handles Claude → Groq fallback internally)
        if document:
            return await self._handle_document(message, document, history)

        allowed = user.allowed_departments

        # Classify the query
        agent_name = await self.classify(message, allowed)

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
        )
        return result

    async def _handle_document(
        self,
        message: str,
        document: dict,
        history: list[tuple[str, str]] | None,
    ) -> dict:
        """Analyze an attached document. Tries Claude first, falls back to Groq."""
        import logging
        from langchain_core.messages import AIMessage

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

        # Images require Claude (multimodal). Text docs can use either provider.
        is_image = document["type"] == "image"

        # Build text-based messages (works with both Claude and Groq)
        msgs = [system_msg]

        if history:
            for role, content in history[-4:]:
                if role == "user":
                    msgs.append(HumanMessage(content=content))
                elif role == "assistant":
                    msgs.append(AIMessage(content=content))

        if is_image:
            # Multimodal content for Claude only
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

                claude_llm = ChatAnthropic(
                    api_key=get_settings().anthropic_api_key,
                    model=get_settings().anthropic_model,
                    temperature=0.1,
                    max_tokens=4096,
                )
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
                            "requiere Claude API. Verifica que tu API Key esté activa. "
                            "Para documentos de texto (PDF, Excel, Word), puedes seguir "
                            "adjuntándolos y serán analizados con Groq."
                        ),
                        "agent_used": "orchestrator",
                        "metadata": {"classification": "document_error"},
                    }
                log.info("Falling back to Groq for document analysis")

        # Fallback: use Groq for text documents
        if is_image and not is_claude_available():
            return {
                "response": (
                    "El análisis de imágenes requiere la API de Claude (Anthropic). "
                    "Puedes adjuntar documentos de texto (PDF, Excel, Word, CSV) "
                    "que serán analizados con el modelo actual."
                ),
                "agent_used": "orchestrator",
                "metadata": {"classification": "document_no_image_support"},
            }

        groq_llm = create_llm(temperature=0.1, max_tokens=4096, purpose="document_analysis")
        log.info("Using Groq for document analysis (fallback)")
        response = await groq_llm.ainvoke(msgs)

        return {
            "response": response.content,
            "agent_used": "document_analysis",
            "metadata": {
                "classification": "document",
                "provider": "groq",
                "filename": document.get("filename"),
            },
        }

    async def _handle_general(
        self, message: str, history: list[tuple[str, str]] | None
    ) -> dict:
        """Handle general queries that don't map to a specific department."""
        from langchain_core.messages import AIMessage

        messages = [
            SystemMessage(
                content=(
                    "Eres SantoniBot, el asistente inteligente de Alimentos Santoni. "
                    "Responde de forma amable y profesional en español. "
                    "Si el usuario saluda, preséntate brevemente. "
                    "Si pregunta sobre el sistema, explica que puedes ayudar con consultas "
                    "de Finanzas, Contabilidad, Ventas, RRHH, Producción, Compras de Insumos "
                    "y Compras a Productores. "
                    "Si la consulta no es clara, pide más detalles."
                )
            )
        ]

        if history:
            for role, content in history[-6:]:
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=message))
        response = await self.classifier.ainvoke(messages)

        return {
            "response": response.content,
            "agent_used": "general",
            "metadata": {"classification": "general"},
        }

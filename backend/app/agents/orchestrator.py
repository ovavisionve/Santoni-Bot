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
from app.agents.base_agent import _build_datetime_context
from app.services.window_capability_map import CAPABILITIES
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
        "arroz acondicionado", "maiz acondicionado", "maíz acondicionado",
        "guia de compra", "guias de compra",
        "compra de arroz", "compra de maiz", "compra de maíz",
        # AGRI-103 (09/Abr/2026): variantes plurales que faltaban — los keywords
        # solo cubrían "compra de" pero los usuarios escriben "compras de" (con S).
        "compras de arroz", "compras de maiz", "compras de maíz",
        "compras a productor", "precio del arroz", "precio del maiz",
        "precio del maíz", "tonelada", "kilogramo",
        "recepcion de maiz", "recepción de maíz", "recepcion de arroz", "recepción de arroz",
        "buque", "narvi", "maiz seco", "maíz seco",
        # Debt/payment queries related to agricultural products and producers
        "pagar de maiz", "pagar de maíz", "pagar de arroz",
        "deuda de maiz", "deuda de maíz", "deuda de arroz",
        "deuda de productor", "deuda de productores", "deuda productor",
        "pago a productor", "pago a productores", "pagos a productor",
        "pagos pendientes a productor", "pagos pendientes a productores",
        "monto de maiz", "monto de maíz", "monto de arroz",
        "monto a pagar de maiz", "monto a pagar de maíz",
        "por pagar de maiz", "por pagar de maíz", "por pagar de arroz",
        "por pagar a productor", "por pagar a productores",
    ]),
    # Producción — BEFORE compras_insumos to catch "materia prima", "producto terminado"
    # and "producción"-related keywords before they fall through to inventory/compras
    ("produccion", [
        "produccion", "producción", "producir", "produjo", "producido",
        "fabricar", "fabricó", "fabricado", "manufactura",
        "planta", "línea de producción", "linea de produccion",
        "eficiencia", "oee", "desperdicio", "merma", "scrap",
        "mantenimiento", "turno", "turnos", "lote", "lotes",
        "orden de produccion", "orden de producción",
        "ordenes de produccion", "órdenes de producción",
        # COMP-101 (09/Abr/2026): "empaque" removido porque es ambiguo en
        # Santoni — los usuarios usan "empaque" para referirse a materiales de
        # empaque (cartón, polietileno, etc.) que son INSUMOS, no producto
        # terminado. Si en el futuro se necesita matchear "empaque" como etapa
        # de producción, usar "etapa de empaque" o "línea de empaque".
        "producto terminado", "envasado",
        "recepcion de materia", "recepción de materia",
        "despacho de producto", "despachos",
        "cuanto se produjo", "cuánto se produjo",
        "arroz blanco", "harina de maiz", "harina de maíz",
        "materia prima",
    ]),
    # Compras de insumos — after produccion (which catches "materia prima", "producto terminado")
    # and before ventas (to prevent "inventario" matching "venta" substring)
    ("compras_insumos", [
        "insumo", "proveedor", "proveedores", "orden de compra",
        "ordenes de compra", "inventario de material",
        "inventario de insumo", "inventario de repuesto",
        "inventario", "material",
        "compra de insumo", "compras insumo", "suministro",
        "tiempo de entrega", "stock", "existencia", "existencias",
        "almacén", "almacen", "almacenes", "bodega",
        "disponible en almacen", "disponible en almacén",
        "cuánto hay", "cuanto hay", "cuánto queda", "cuanto queda",
        "historial de compra", "historial de compras",
        "compras de", "compra del producto",
        # "compra" catches verb forms: compramos, comprado, compró
        "compra",
    ]),
    # Contabilidad — BEFORE ventas/finanzas to catch accounting terms first
    ("contabilidad", [
        "contab", "contabilidad",
        "balance general", "balance de comprobacion", "balance de comprobación",
        "estado de resultado", "libro diario", "libro mayor",
        "islr",
        "activo fijo", "activos fijos", "depreciacion", "depreciación",
        "asiento contable", "plan de cuenta", "plan de cuentas", "partida",
        # Account-specific (saldos de cuentas, no bancarios)
        "cuenta contable", "cuentas contables",
        "cuentas de ingreso", "cuenta de ingreso",
        "cuentas de gasto", "cuenta de gasto",
        "cuentas de egreso", "cuenta de egreso",
        "cuentas de activo", "cuentas de pasivo",
        "saldo de la cuenta", "saldo de cuenta", "saldo contable",
        "balance de la cuenta", "mayor de la cuenta",
        "periodo contable", "período contable",
        "débito", "debe y haber",
        "cierre contable", "cierre de mes", "cierre de año",
        "conciliacion", "conciliación", "conciliacion bancaria",
        "balanza de comprobacion", "balanza de comprobación", "balanza",
        "patrimonio", "capital social",
        "ingresos por venta", "ingreso por venta",
        "utilidad bruta", "utilidad neta", "ganancia neta",
        "pérdida", "perdida",
    ]),
    # Finanzas — BEFORE ventas so "cuentas por cobrar" routes here
    ("finanzas", [
        "finanza", "financiero", "financiera", "flujo de caja",
        "banco", "bancos", "bancaria", "bancario", "bancarias", "bancarios",
        "saldo bancario", "saldo de banco",
        "cuenta por cobrar", "cuentas por cobrar", "por cobrar",
        "cuenta por pagar", "cuentas por pagar", "por pagar",
        "presupuesto", "rentabilidad", "liquidez",
        "estado de flujo", "indicador financiero",
        "prestamo", "préstamo", "prestamos", "préstamos",
        "cuota", "cuotas",
        "disponibilidad bancaria", "disponibilidad",
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
        "pendiente de cobro",
        "nota de credito", "notas de credito", "nota de crédito", "notas de crédito",
        "producto más vendido", "productos más vendidos",
        "top producto", "ventas por producto", "ventas por categoria",
        "ventas por categoría", "sku",
        "orden de venta", "ordenes de venta", "órdenes de venta",
        "pedido de venta", "pedidos de venta", "pipeline de venta",
        "ventas por sucursal", "sucursal",
        "tasa de cambio", "tipo de cambio",
        "impuesto", "iva", "retencion", "retención",
        "base imponible", "exento", "gravado",
    ]),
    # RRHH
    ("rrhh", [
        "nomina", "nómina", "empleado", "empleados", "personal",
        "trabajador", "trabajadores", "plantilla",
        "obrero", "obreros", "gerente", "gerentes",
        "analista", "supervisor", "supervisora", "coordinador", "coordinadora",
        "operario", "operarios", "operador", "chofer", "choferes",
        "cargo", "cargos", "puesto", "puestos",
        "vacacion", "vacación", "vacaciones", "asistencia", "inasistencia",
        "ausentismo", "ausentimos", "ausencia", "ausencias", "falta", "faltas",
        "evaluacion", "evaluación",
        "cumpleaño", "cumpleaños", "cumpleañero", "cumpleañeros",
        # Variantes verbales de "cumplir años" — RRHH-101 (09/Abr/2026):
        # los keywords sustantivos no matcheaban "cumplen años en abril" porque
        # el matching es substring y "cumpleaños" != "cumple años" / "cumplen años".
        "cumple año", "cumple años", "cumplen año", "cumplen años",
        "cumplir año", "cumplir años", "cumplo año", "cumplo años",
        "nacido", "nacidos", "nacimiento", "fecha de nacimiento",
        "salario", "sueldo", "sueldos", "salarios",
        "recurso humano", "recursos humanos",
        "rrhh", "talento humano",
        "contrato", "contratos", "contratacion", "contratación",
        "ingreso", "ingresos", "ingresaron", "ingresó",
        "liquidacion", "liquidación",
        "prestacion", "prestación", "prestaciones",
        "renuncia", "renunciado", "renuncias",
        "despido", "despidos", "despedido",
        "bono", "bonos", "bonificacion", "bonificación",
        "permiso", "permisos", "reposo", "reposos",
        "incapacidad", "incapacidades",
        "rotacion", "rotación",
        "capacitacion", "capacitación",
    ]),
]

# Greetings / general patterns
_GENERAL_PATTERNS = [
    "hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches",
    "gracias", "ayuda", "que puedes hacer", "qué puedes hacer",
    "quien eres", "quién eres", "como funciona", "cómo funciona",
]

# ── Pre-routing rules ───────────────────────────────────────────────────
# Frases de ALTA ESPECIFICIDAD que se evalúan ANTES del loop genérico de
# _KEYWORD_RULES. Resuelven conflictos donde un keyword genérico de un
# agente (ej "proveedores" en compras_insumos) captura preguntas que
# realmente pertenecen a otro agente (ej "cuentas por pagar a proveedores"
# → finanzas). La frase larga es más específica y se evalúa primero.
#
# FIN-100 (09/Abr/2026): "cuentas por pagar a proveedores" iba a
#   compras_insumos por "proveedores". Pero "cuentas por pagar" es
#   terminología financiera inequívoca.
# FAIL routing_produccion_existencia (09/Abr/2026): "existencia del
#   producto" iba a compras_insumos por "existencia". Pero "existencia
#   del producto [código]" es inventario/produccion.
_PRE_ROUTING_RULES: list[tuple[str, list[str]]] = [
    ("finanzas", [
        "cuentas por pagar a proveedor", "cuentas por pagar a proveedores",
        "saldo de cuentas por pagar", "saldo de las cuentas por pagar",
        "cuentas por cobrar de", "cuentas por cobrar para",
    ]),
    ("produccion", [
        "existencia del producto", "existencia de producto",
        "existencias del producto", "stock del producto",
        "cantidad del producto", "cantidad de producto",
        "en existencia del producto",
    ]),
]


def _has_account_code(msg: str) -> bool:
    """Detect accounting codes like 1.01.04.02, 2.01.01.10 in the message."""
    return bool(re.search(r'\d\.\d{2}\.\d{2}', msg))


def classify_by_keywords(
    message: str,
    allowed_departments: list[str],
    last_agent: str | None = None,
) -> str:
    """
    Classify a message by scanning for department-specific keywords.
    Returns the agent name or "general" if no match found.
    Returns "no_access" if the matched department is not in allowed list.

    If no keyword matches and last_agent is provided, uses the last agent
    as context for follow-up messages (e.g. "¿estás seguro?", "dame más detalle").
    ~0ms execution time.
    """
    msg = message.lower()

    # Check greetings / general first
    if any(p in msg for p in _GENERAL_PATTERNS) and len(msg) < 60:
        return "general"

    # Pre-routing: high-specificity phrases that resolve keyword conflicts.
    # Evaluated BEFORE the main keyword loop so that "cuentas por pagar a
    # proveedores" → finanzas wins over "proveedores" → compras_insumos.
    for agent_name, phrases in _PRE_ROUTING_RULES:
        if any(ph in msg for ph in phrases):
            if agent_name in allowed_departments:
                return agent_name

    # Check for accounting codes (e.g. "2.01.01.10") → always contabilidad
    if _has_account_code(msg):
        if "contabilidad" in allowed_departments:
            return "contabilidad"
        return "no_access"

    # Scan keyword rules (order matters: specific before broad)
    # If a keyword matches but the user lacks access to that department,
    # continue scanning — another keyword might match an allowed department.
    hit_no_access = False
    for agent_name, keywords in _KEYWORD_RULES:
        if any(kw in msg for kw in keywords):
            if agent_name in allowed_departments:
                return agent_name
            # Mark that we found a match but user lacks access; keep scanning
            hit_no_access = True

    # If keywords matched a blocked department, return no_access.
    # Don't fallback to last_agent here — it would route a ventas query
    # to compras_insumos just because the user was last in compras.
    if hit_no_access:
        return "no_access"

    # Fallback 1: continue with last agent for follow-up messages
    # Catches: "¿estás seguro?", "dame más detalle", "ok dame de enero",
    # "y en dólares?", "y por zona?", etc.
    if last_agent and last_agent in allowed_departments and last_agent != "general":
        return last_agent

    # Fallback 2: if message is a question about data, check for production-
    # related words before defaulting to ventas
    if any(w in msg for w in ["cuanto", "cuánto", "dame", "muestra", "reporte"]):
        # Check if the question is about production/inventory topics
        if any(w in msg for w in [
            "produjo", "producido", "producción", "produccion",
            "fabricó", "fabricado", "desperdicio", "merma",
        ]):
            if "produccion" in allowed_departments:
                return "produccion"
        if "ventas" in allowed_departments:
            return "ventas"

    return "general"


def classify_with_capabilities(
    message: str,
    capability_ids: set[str] | None,
    allowed_departments: list[str],
    last_agent: str | None = None,
) -> tuple[str, str | None, float, str]:
    """Classify using granular capability keywords.

    Returns (agent_name, capability_id, confidence_score, match_type).
    If capability_ids is None, user has access to all capabilities (admin).
    """
    msg = message.lower()

    # Greetings
    if any(p in msg for p in _GENERAL_PATTERNS) and len(msg) < 60:
        return "general", None, 1.0, "saludo_directo"

    # Accounting code → contabilidad_cuenta
    if _has_account_code(msg):
        cap_id = "contabilidad_cuenta"
        if capability_ids is None or cap_id in capability_ids:
            return "contabilidad", cap_id, 1.0, "codigo_contable"
        return "no_access", cap_id, 0.9, "codigo_contable_sin_acceso"

    # Pre-routing: high-specificity phrases (same as classify_by_keywords)
    for agent_name, phrases in _PRE_ROUTING_RULES:
        if any(ph in msg for ph in phrases):
            if agent_name in allowed_departments:
                return agent_name, None, 1.0, "pre_routing_rule"

    # Scan ALL capabilities by their keywords (most specific first)
    # Score each capability by how many keywords match
    matches: list[tuple[str, str, int]] = []  # (agent, cap_id, match_count)
    for cap in CAPABILITIES.values():
        match_count = sum(1 for kw in cap.keywords if kw in msg)
        if match_count > 0:
            matches.append((cap.agent, cap.id, match_count))

    # Sort by match count (most matches = best fit)
    matches.sort(key=lambda x: x[2], reverse=True)

    # Try each match in order
    hit_no_access = False
    for agent_name, cap_id, _count in matches:
        if capability_ids is None or cap_id in capability_ids:
            if agent_name in allowed_departments:
                return agent_name, cap_id, 1.0, "capability_match"
            hit_no_access = True
        else:
            hit_no_access = True

    if hit_no_access:
        if last_agent and last_agent in allowed_departments and last_agent != "general":
            return last_agent, None, 0.6, "capability_bloqueado_fallback"
        return "no_access", None, 0.8, "capability_sin_acceso"

    # Fallback to last agent for follow-ups
    if last_agent and last_agent in allowed_departments and last_agent != "general":
        return last_agent, None, 0.7, "followup_last_agent"

    # Generic data question fallback
    if any(w in msg for w in ["cuanto", "cuánto", "dame", "muestra", "reporte"]):
        if "ventas" in allowed_departments:
            return "ventas", None, 0.4, "fallback_ventas"

    return "general", None, 0.3, "sin_match"


def classify_with_confidence(
    message: str,
    allowed_departments: list[str],
    last_agent: str | None = None,
) -> tuple[str, float, str]:
    """Classify a message and return (agent_name, confidence_score, match_type).

    confidence_score: 0.0 to 1.0
    match_type: describes HOW the classification was made, for the report.
    """
    msg = message.lower()

    # Greetings
    if any(p in msg for p in _GENERAL_PATTERNS) and len(msg) < 60:
        return "general", 1.0, "saludo_directo"

    # Accounting code
    if _has_account_code(msg):
        if "contabilidad" in allowed_departments:
            return "contabilidad", 1.0, "codigo_contable"
        return "no_access", 0.9, "codigo_contable_sin_acceso"

    # Pre-routing: high-specificity phrases (same as classify_by_keywords)
    for agent_name, phrases in _PRE_ROUTING_RULES:
        if any(ph in msg for ph in phrases):
            if agent_name in allowed_departments:
                return agent_name, 1.0, "pre_routing_rule"

    # Keyword scan
    hit_no_access = False
    for agent_name, keywords in _KEYWORD_RULES:
        if any(kw in msg for kw in keywords):
            if agent_name in allowed_departments:
                return agent_name, 1.0, "keyword_directo"
            hit_no_access = True

    if hit_no_access:
        if last_agent and last_agent in allowed_departments and last_agent != "general":
            return last_agent, 0.6, "keyword_bloqueado_fallback_last_agent"
        return "no_access", 0.8, "keyword_sin_acceso"

    # Last agent follow-up
    if last_agent and last_agent in allowed_departments and last_agent != "general":
        return last_agent, 0.7, "followup_last_agent"

    # Data question fallback — check production keywords before defaulting to ventas
    if any(w in msg for w in ["cuanto", "cuánto", "dame", "muestra", "reporte"]):
        if any(w in msg for w in [
            "produjo", "producido", "producción", "produccion",
            "fabricó", "fabricado", "desperdicio", "merma",
        ]):
            if "produccion" in allowed_departments:
                return "produccion", 0.5, "fallback_produccion"
        if "ventas" in allowed_departments:
            return "ventas", 0.4, "fallback_ventas"

    return "general", 0.3, "sin_match"


def compute_confidence_score(
    routing_score: float,
    has_data: bool,
    agent_used: str,
) -> tuple[float, dict]:
    """Compute overall confidence score from routing + data availability.

    Returns (overall_score, score_breakdown).

    Weights:
    - routing_confidence: 60% (how sure we are about routing)
    - data_confidence: 40% (did the query return actual data)
    """
    data_score = 1.0 if has_data else 0.2

    # Special cases: no_access and general have fixed scores
    if agent_used == "orchestrator":
        # access denied
        overall = 0.9  # We're confident it was access denied
        breakdown = {
            "routing": routing_score,
            "data": 0.0,
            "overall": overall,
            "nota": "acceso_denegado",
        }
        return overall, breakdown

    if agent_used == "general":
        # General handler: lower confidence overall
        # Use routing_score * 0.5 directly — a greeting (1.0) → 0.5,
        # a sin_match (0.3) → 0.15. No need for min() cap.
        overall = round(routing_score * 0.5, 2)
        breakdown = {
            "routing": routing_score,
            "data": 0.0,
            "overall": overall,
            "nota": "agente_general",
        }
        return overall, breakdown

    # Specialized agent: weighted average
    overall = round(routing_score * 0.6 + data_score * 0.4, 2)
    breakdown = {
        "routing": routing_score,
        "data": data_score,
        "overall": overall,
    }
    return overall, breakdown


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
        # Esto BYPASS el routing por keywords para preguntas de datos.
        # Si funciona, retorna directo. Si falla, cae al flujo normal.
        # Solo para preguntas que "parecen datos" (no saludos, no follow-ups
        # muy cortos que necesitan contexto del agente anterior).
        msg_lower = message.lower().strip()
        is_greeting = any(p in msg_lower for p in _GENERAL_PATTERNS) and len(msg_lower) < 60
        is_short_followup = len(msg_lower) < 25 and not any(
            c in msg_lower for c in ["cuánt", "cuant", "total", "saldo", "emplea", "venta",
                                      "compr", "produc", "factur", "cobr", "banco"]
        )

        if not is_greeting and not is_short_followup:
            try:
                from app.services.sql_direct import process_with_sql_direct
                sql_result = await process_with_sql_direct(
                    message=message,
                    history=history,
                    org_ids=user.org_ids,
                )
                if sql_result is not None:
                    logger.info(
                        "SQL Direct handled: '%s' → %d rows",
                        message[:60],
                        sql_result.get("metadata", {}).get("rows_returned", 0),
                    )
                    # Add confidence score
                    sql_result["confidence_score"] = 1.0
                    sql_result["score_breakdown"] = {
                        "routing": 1.0,
                        "data": 1.0 if sql_result.get("metadata", {}).get("has_data") else 0.2,
                        "overall": 1.0,
                        "match_type": "sql_direct",
                    }
                    return sql_result
            except Exception as exc:
                logger.warning("SQL Direct failed, falling back to agents: %s", exc)

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
        msg_lower = message.lower().strip()
        is_greeting = any(p in msg_lower for p in _GENERAL_PATTERNS) and len(msg_lower) < 60
        is_short_followup = len(msg_lower) < 25 and not any(
            c in msg_lower for c in ["cuánt", "cuant", "total", "saldo", "emplea", "venta",
                                      "compr", "produc", "factur", "cobr", "banco"]
        )

        if not is_greeting and not is_short_followup:
            try:
                from app.services.sql_direct import process_with_sql_direct
                sql_result = await process_with_sql_direct(
                    message=message,
                    history=history,
                    org_ids=user.org_ids,
                )
                if sql_result is not None:
                    logger.info(
                        "SQL Direct (stream) handled: '%s' → %d rows",
                        message[:60],
                        sql_result.get("metadata", {}).get("rows_returned", 0),
                    )
                    yield sql_result["response"]
                    return
            except Exception as exc:
                logger.warning("SQL Direct (stream) failed, falling back: %s", exc)

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

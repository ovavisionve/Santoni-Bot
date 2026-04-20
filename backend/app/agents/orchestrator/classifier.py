"""Classification functions: keyword routing, capability-based routing, confidence."""

import logging

from app.services.window_capability_map import CAPABILITIES

from .keywords import (
    _KEYWORD_RULES,
    _GENERAL_PATTERNS,
    _PRE_ROUTING_RULES,
    _FOLLOWUP_PATTERNS,
    _DOMAIN_KEYWORD_FRAGMENTS,
    _has_account_code,
)

logger = logging.getLogger("santonibot.orchestrator")



def _is_greeting(msg_lower: str) -> bool:
    """True si el mensaje parece un saludo o pregunta general (no de datos)."""
    return any(p in msg_lower for p in _GENERAL_PATTERNS) and len(msg_lower) < 60


def _is_short_followup(msg_lower: str) -> bool:
    """True si el mensaje es un follow-up corto sin keyword de dominio.

    Estos follow-ups ("sí", "ok", "gracias", "más detalle") necesitan el
    contexto del agente anterior y no deben ir a SQL Directo (que los
    interpretaría como preguntas nuevas sin contexto).

    Un mensaje se considera follow-up corto si:
      - tiene menos de 25 caracteres, Y
      - NO contiene ningún fragmento de keyword de dominio
    """
    if len(msg_lower) >= 25:
        return False
    return not any(frag in msg_lower for frag in _DOMAIN_KEYWORD_FRAGMENTS)


def should_try_sql_direct(message: str) -> bool:
    """Decide si vale la pena invocar SQL Directo para este mensaje.

    Retorna False para saludos, chistes, y follow-ups muy cortos sin
    keywords de dominio. En esos casos el flujo va directo al handler
    general (saludos) o hereda el last_agent (follow-ups).
    """
    msg_lower = message.lower().strip()
    if _is_greeting(msg_lower):
        return False
    if _is_short_followup(msg_lower):
        return False
    return True


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

    # VENT-100 / ORCH-101 (14/Abr/2026): short follow-up messages that
    # modify the previous query (e.g., "en dólares", "por zona", "dame en
    # febrero") should route to last_agent instead of re-classifying. This
    # prevents "en dólares" from being classified by keywords and ending up
    # in the wrong agent.
    if last_agent and last_agent in allowed_departments and last_agent != "general":
        if len(msg) < 40 and any(fp in msg for fp in _FOLLOWUP_PATTERNS):
            return last_agent

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

    # VENT-100 / ORCH-101: short follow-ups route to last_agent
    if last_agent and last_agent in allowed_departments and last_agent != "general":
        if len(msg) < 40 and any(fp in msg for fp in _FOLLOWUP_PATTERNS):
            return last_agent, None, 0.9, "followup_pattern_last_agent"

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

    # VENT-100 / ORCH-101: short follow-ups route to last_agent
    if last_agent and last_agent in allowed_departments and last_agent != "general":
        if len(msg) < 40 and any(fp in msg for fp in _FOLLOWUP_PATTERNS):
            return last_agent, 0.9, "followup_pattern_last_agent"

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



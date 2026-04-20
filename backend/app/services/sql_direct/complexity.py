"""Query complexity detection and LLM factory for SQL Direct."""

import logging

from app.config import get_settings
from app.services.llm_factory import create_llm, is_claude_available

logger = logging.getLogger("santonibot.sql_direct")

_COMPLEX_KEYWORDS = frozenset({
    "total", "totales", "suma", "promedio", "ranking", "top ",
    "resumen", "desglose", "desglosado", "agrupado", "agrupada",
    "gasto", "gastos", "ingreso", "ingresos", "devengado", "deducido",
    "deducción", "deduccion", "utilidad", "balance", "saldo",
    "cobranza", "cobrado", "facturado", "facturación", "facturacion",
    "ausentismo", "ausencia",
    "por zona", "por organización", "por organizacion", "por org",
    "por departamento", "por cargo", "por tipología", "por tipologia",
    "por moneda", "por cliente", "por proveedor", "por mes",
    "por tipo", "por categoria", "por categoría",
    "comparar", "comparación", "comparacion", "versus",
    "primer trimestre", "segundo trimestre", "tercer trimestre",
    "cuarto trimestre", "semestre", "año ", "anual", "acumulado",
    "histórico", "historico",
})

_SIMPLE_PATTERNS = frozenset({
    "cumpleañeros", "cumpleaños", "cumple año", "cumplen año", "nacidos",
    "fecha de ingreso", "fecha de nacimiento", "fecha de contratación",
    "cuántos empleados", "cuantos empleados",
    "cuántos activos", "cuantos activos",
    "cuantos trabajadores", "cuántos trabajadores",
    "quién es", "quien es", "quién cumple", "quien cumple",
    "dame la fecha", "dime la fecha",
})


def is_complex_query(message: str, history: list | None = None) -> bool:
    """Clasifica una query como compleja o simple (heurística).

    Lógica:
      1. Si matchea un patrón SIMPLE → simple (prioritario)
      2. Si el historial tiene > 3 turnos → compleja
      3. Si matchea _COMPLEX_KEYWORDS → compleja
      4. Si menciona >= 2 meses → compleja
      5. Default → simple
    """
    msg_lower = message.lower()

    if any(p in msg_lower for p in _SIMPLE_PATTERNS):
        return False

    if history and len(history) > 6:
        return True

    if any(kw in msg_lower for kw in _COMPLEX_KEYWORDS):
        return True

    import re as _re
    meses = _re.findall(
        r"\b(enero|febrero|marzo|abril|mayo|junio|julio|"
        r"agosto|septiembre|octubre|noviembre|diciembre)\b",
        msg_lower,
    )
    if len(meses) >= 2:
        return True

    return False


def create_sql_direct_llm(
    temperature: float = 0.0,
    max_tokens: int = 2048,
    user_message: str = "",
    history: list | None = None,
):
    """Create the LLM for SQL Direct (hybrid mode con opcional fine-grained).

    Modos:
      1. USE_CLAUDE_FOR_SQL=false → AI_PROVIDER default (OpenRouter/DeepSeek).
      2. USE_CLAUDE_FOR_SQL=true + USE_CLAUDE_ONLY_FOR_COMPLEX=false (default) → todas a Claude.
      3. USE_CLAUDE_FOR_SQL=true + USE_CLAUDE_ONLY_FOR_COMPLEX=true → híbrido fino.
    """
    settings = get_settings()
    claude_available = settings.use_claude_for_sql and is_claude_available()

    if claude_available and settings.use_claude_only_for_complex:
        is_complex = is_complex_query(user_message, history)
        if is_complex:
            logger.info(
                "SQL Direct híbrido: Claude (%s) para query compleja: '%s'",
                settings.anthropic_model, user_message[:60],
            )
            return create_llm(
                temperature=temperature,
                max_tokens=max_tokens,
                purpose="sql_direct_complex",
                provider="anthropic",
            )
        logger.info(
            "SQL Direct híbrido: %s para query simple: '%s'",
            settings.openrouter_model, user_message[:60],
        )
        return create_llm(
            temperature=temperature,
            max_tokens=max_tokens,
            purpose="sql_direct_simple",
        )

    if claude_available:
        logger.debug(
            "SQL Direct: usando Claude (%s) por USE_CLAUDE_FOR_SQL=True",
            settings.anthropic_model,
        )
        return create_llm(
            temperature=temperature,
            max_tokens=max_tokens,
            purpose="sql_direct",
            provider="anthropic",
        )

    return create_llm(
        temperature=temperature,
        max_tokens=max_tokens,
        purpose="sql_direct",
    )

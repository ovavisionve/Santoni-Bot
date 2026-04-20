"""
Clasificador de errores macro para el runner de QA.

En vez de solo decir "falló tal check", analiza el patrón de la respuesta y
asigna una categoría de error + explicación. Categorías:

  - pass: todos los checks pasaron
  - agent_misrouting: la pregunta fue a otro agente
  - access_denied: el bot dijo "no tengo acceso"
  - no_data_in_response: el bot dijo que no hay datos para el período
  - bot_short_response: respuesta < 100 chars (probable error interno)
  - missing_currency_split: SQL tiene VES+USD pero bot solo mencionó una
  - hallucination_amounts: hay números pero no matchean (diff > 5%)
  - wrong_period: cifras parecen de otro rango temporal
  - no_numbers_extracted: respuesta larga pero sin números
  - unknown_mismatch: fallback cuando no se identifica patrón claro
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .comparator import CheckResult


@dataclass
class ErrorVerdict:
    category: str
    explanation: str
    suggested_fix: str = ""


_ACCESS_DENIED_PHRASES = [
    "no tengo acceso",
    "no puedo acceder",
    "no dispongo",
    "no tengo la capacidad",
    "no cuento con acceso",
    "no puedo consultar",
    "mis capacidades están limitadas",
]

_NO_DATA_PHRASES = [
    "no se encontraron datos",
    "no hay datos disponibles",
    "no se pudo obtener",
    "error al consultar",
    "no hay registros",
    "no se encontró información",
    "no hay información",
]

_VES_TOKENS = {"ves", "bs.", "bolivares", "bolívares", " bs ", " bs,", " bs:", "bolivar", "bolívar"}
_USD_TOKENS = {"usd", "us$", "$", "dólar", "dolar", "dolares", "dólares"}


def _mentions_currency(text_lower: str, currency: str) -> bool:
    """True si el texto menciona explícitamente VES o USD."""
    tokens = _VES_TOKENS if currency == "VES" else _USD_TOKENS
    return any(tok in text_lower for tok in tokens)


def classify_error(
    expected: dict[str, Any],
    bot_response_text: str,
    bot_agent_used: str | None,
    bot_numbers: list[float],
    checks: list[CheckResult],
    expected_agent: str = "ventas",
) -> ErrorVerdict:
    """Clasifica el error macro y sugiere un fix.

    `expected` es el dict que retorna la SQL de verificación.
    `bot_response_text` es el texto crudo de la respuesta del bot.
    `bot_agent_used` es el valor de metadata.agent_used del response.
    `bot_numbers` son los números extraídos del texto por extract_numbers.
    `checks` son los CheckResult del comparator.
    """
    all_passed = all(c.passed for c in checks)
    if all_passed and checks:
        return ErrorVerdict(
            category="pass",
            explanation="Todos los checks pasaron — bot y SQL coinciden",
        )

    text_lower = bot_response_text.lower()

    # 1. Agent misrouting — la pregunta no llegó al agente correcto
    if bot_agent_used and bot_agent_used != expected_agent:
        return ErrorVerdict(
            category="agent_misrouting",
            explanation=(
                f"La pregunta fue ruteada a '{bot_agent_used}' en vez de "
                f"'{expected_agent}'. El test fuerza agent_name en la request "
                "pero el orchestrator puede ignorarlo."
            ),
            suggested_fix=(
                "Revisar keywords de routing en orchestrator.py. Si la pregunta "
                "tiene palabras ambiguas, agregar reglas explícitas para ventas."
            ),
        )

    # 2. Access denied
    for phrase in _ACCESS_DENIED_PHRASES:
        if phrase in text_lower:
            return ErrorVerdict(
                category="access_denied",
                explanation=f"El bot dijo '{phrase}' — permisos o capability mal asignados",
                suggested_fix=(
                    "Verificar que el usuario admin tenga acceso al dep. ventas "
                    "y que ventas esté en user.allowed_departments. Revisar "
                    "capability_ids del usuario."
                ),
            )

    # 3. No data — el bot reconoce la pregunta pero dice no hay datos
    for phrase in _NO_DATA_PHRASES:
        if phrase in text_lower:
            return ErrorVerdict(
                category="no_data_in_response",
                explanation=f"Bot dijo '{phrase}' pero el SQL sí devuelve datos",
                suggested_fix=(
                    "Comparar filtros del bot (mes/anio/org) con el SQL "
                    "de verificación. Probable: el bot usa rango de fechas "
                    "distinto, o tiene filtro extra (docstatus, currency) "
                    "que excluye los datos reales."
                ),
            )

    # 4. Short response — bot respondió muy poco (error interno probable)
    if len(bot_response_text.strip()) < 100:
        return ErrorVerdict(
            category="bot_short_response",
            explanation=f"Respuesta de solo {len(bot_response_text)} chars: {bot_response_text!r}",
            suggested_fix=(
                "Revisar logs del backend al correr esta pregunta. Probable: "
                "excepción en fetch_data() o el LLM declinó. Ver "
                "'santonibot.agents.ventas' en logs."
            ),
        )

    # 5. Missing currency split — el SQL tiene ambas monedas pero bot solo menciona una
    if isinstance(expected.get("by_currency"), dict):
        expected_currencies = {c for c in expected["by_currency"].keys() if c in {"VES", "USD"}}
        if len(expected_currencies) >= 2:
            mentioned = set()
            if _mentions_currency(text_lower, "VES"):
                mentioned.add("VES")
            if _mentions_currency(text_lower, "USD"):
                mentioned.add("USD")
            missing = expected_currencies - mentioned
            if missing:
                return ErrorVerdict(
                    category="missing_currency_split",
                    explanation=(
                        f"El bot solo mencionó {sorted(mentioned) or 'ninguna'}, "
                        f"esperaba {sorted(expected_currencies)} — falta {sorted(missing)}"
                    ),
                    suggested_fix=(
                        "Verificar que build_sales_summary esté retornando "
                        "separado por moneda y que el agente (ventas.py) "
                        "formatee ambos bloques. Puede ser detección de "
                        "currency en _detect_currency() del agente."
                    ),
                )

    # 6. Sin números — la respuesta existe pero no extrajimos ningún número relevante
    significant = [n for n in bot_numbers if abs(n) >= 100 and not (2020 <= n <= 2030)]
    if not significant:
        return ErrorVerdict(
            category="no_numbers_extracted",
            explanation=(
                f"Respuesta de {len(bot_response_text)} chars pero sin números "
                f"significativos (solo {len(bot_numbers)} chicos o años)"
            ),
            suggested_fix=(
                "El bot puede estar respondiendo con texto explicativo sin datos. "
                "Ver logs: probablemente el query vino vacío y el LLM redactó "
                "una respuesta genérica. Revisar si el rango de fechas o los "
                "filtros del agente devuelven 0 filas."
            ),
        )

    # 7. Hallucination — hay números pero no matchean con SQL
    amount_checks = [
        c for c in checks
        if isinstance(c.expected, (int, float)) and abs(c.expected) >= 100
    ]
    if amount_checks:
        diffs_pct = []
        for c in amount_checks:
            if c.closest_found is not None and c.expected:
                d = abs(c.closest_found - c.expected) / abs(c.expected) * 100
                diffs_pct.append(d)
        if diffs_pct:
            avg = sum(diffs_pct) / len(diffs_pct)
            # Si los números del bot son ~100% distintos, probable scope diferente
            if avg > 50:
                return ErrorVerdict(
                    category="wrong_period_or_scope",
                    explanation=(
                        f"Números difieren {avg:.1f}% en promedio — "
                        "bot probablemente usa otro rango temporal u otro filtro"
                    ),
                    suggested_fix=(
                        "Verificar que el bot interprete bien 'mes actual' / "
                        "el año/mes de la pregunta. Puede estar usando año "
                        "completo cuando pides mes, o viceversa. Revisar "
                        "extract_month_year / extract_date_range."
                    ),
                )
            # Si los números son ~5-50% distintos, es alucinación o filtro cercano
            return ErrorVerdict(
                category="hallucination_amounts",
                explanation=(
                    f"Montos difieren {avg:.1f}% del SQL — cifras inventadas "
                    "o filtros ligeramente distintos"
                ),
                suggested_fix=(
                    "Si diff < 10%: probable diferencia en filtros de demo orgs "
                    "o status de docs. Si diff > 10%: el LLM está reescribiendo "
                    "números (hallucination). Ver detect_hallucination "
                    "en base_agent.py."
                ),
            )

    # 8. Fallback
    return ErrorVerdict(
        category="unknown_mismatch",
        explanation=(
            "Hay números pero no coinciden con el SQL. No se identificó un "
            "patrón de error claro."
        ),
        suggested_fix=(
            "Revisar manualmente la respuesta del bot y el SQL de verificación. "
            "Puede ser un caso edge no contemplado en el clasificador."
        ),
    )

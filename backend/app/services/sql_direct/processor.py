"""Main entry point for SQL Directo: process_with_sql_direct."""

import logging

from app.config import get_settings
from app.agents.base_agent import _build_datetime_context
from app.services.llm_factory import is_claude_available

from .audit import write_audit
from .complexity import create_sql_direct_llm, is_complex_query
from .executor import execute_sql, format_results_as_markdown
from .org_filter import enforce_org_filter
from .prompts import SYSTEM_PROMPT_TEMPLATE, FORMAT_SYSTEM_PROMPT
from .validator import validate_sql

logger = logging.getLogger("santonibot.sql_direct")

MAX_RETRIES = 2  # 1 intento inicial + 2 retries = 3 intentos totales


def _extract_clarification_question(raw: str) -> str | None:
    """Extrae el texto post-NO_SQL si parece una pregunta al usuario.

    REGLA #9: el LLM puede responder `NO_SQL\\n<pregunta para el usuario>`.
    Queremos surfacear esa pregunta en vez de caer al fallback. Si no hay
    texto útil después de NO_SQL, devolvemos None (flujo original).
    """
    if "NO_SQL" not in raw:
        return None
    _, _, after = raw.partition("NO_SQL")
    text = after.strip()
    if not text or len(text) < 10:
        return None
    # Heurística mínima: que contenga signo de pregunta o palabra típica
    # de clarificación. Evita devolver SQL/código pegado después de NO_SQL.
    lower = text.lower()
    if "?" in text or "¿" in text or any(
        w in lower for w in ("querés", "quieres", "referís", "refieres", "aclarame")
    ):
        return text
    return None


async def process_with_sql_direct(
    message: str,
    history: list[tuple[str, str]] | None = None,
    org_ids: list[int] | None = None,
) -> dict | None:
    """Try to answer a user question using LLM-generated SQL.

    Returns a response dict if successful, or None if the approach failed
    (so the caller can fall back to the traditional agent routing).
    """
    llm = create_sql_direct_llm(
        temperature=0.0,
        max_tokens=2048,
        user_message=message,
        history=history or [],
    )
    datetime_ctx = _build_datetime_context()

    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    # Prompt caching (15/Abr/2026): el prefix es estático → cache_control
    # ephemeral con Anthropic ahorra ~90% del costo de input tokens.
    settings = get_settings()
    claude_available = settings.use_claude_for_sql and is_claude_available()
    if settings.use_claude_only_for_complex:
        use_cache = claude_available and is_complex_query(message, history)
    else:
        use_cache = claude_available

    if use_cache:
        system_msg = SystemMessage(content=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT_TEMPLATE,
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": f"\n\n{datetime_ctx}",
            },
        ])
    else:
        system_msg = SystemMessage(
            content=SYSTEM_PROMPT_TEMPLATE + f"\n\n{datetime_ctx}"
        )

    messages = [system_msg]

    # History truncado: assistant 1500 chars (tablas grandes), user 1000.
    if history:
        for role, content in history[-6:]:
            if role == "user":
                messages.append(HumanMessage(content=content[:1000]))
            elif role == "assistant":
                messages.append(AIMessage(content=content[:1500]))

    messages.append(HumanMessage(content=f"Genera el SQL para: {message}"))

    retry_count = 0
    sql_pre_enforce: str | None = None
    validated_sql: str | None = None
    enforced = False
    cols: list[str] = []
    rows: list = []
    elapsed_ms: float = 0.0
    last_error: str | None = None

    while retry_count <= MAX_RETRIES:
        try:
            sql_response = await llm.ainvoke(messages)
            generated_sql = sql_response.content.strip()
        except Exception as exc:
            logger.warning("SQL Direct: LLM error generating SQL: %s", exc)
            write_audit(
                message=message,
                status=f"llm_gen_error{'_retry' + str(retry_count) if retry_count else ''}",
                error_detail=str(exc),
            )
            return None

        sql_upper_check = generated_sql.upper().strip()
        is_valid_start = (
            sql_upper_check.startswith("SELECT")
            or sql_upper_check.startswith("WITH ")
            or sql_upper_check.startswith("(SELECT")
        )
        if "NO_SQL" in generated_sql or not is_valid_start:
            # Si Claude devolvió NO_SQL seguido de una pregunta al usuario
            # (patrón de REGLA #9 para clarificar ambigüedad), surfacearla
            # directamente sin caer a fallback. Los agentes clásicos
            # adivinarían una interpretación y eso es lo que queremos evitar.
            clarification = _extract_clarification_question(generated_sql)
            if clarification:
                logger.info("SQL Direct: LLM pidió clarificación al usuario")
                write_audit(
                    message=message,
                    sql_generated=generated_sql[:500],
                    status="clarification_requested",
                )
                return {
                    "response": clarification,
                    "agent_used": "sql_direct",
                    "metadata": {
                        "classification": "sql_direct_clarification",
                        "has_data": False,
                    },
                }
            logger.info("SQL Direct: LLM declined (NO_SQL or non-SELECT/WITH)")
            write_audit(
                message=message,
                sql_generated=generated_sql[:500],
                status=f"llm_declined{'_retry' + str(retry_count) if retry_count else ''}",
            )
            return None

        generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()

        is_valid, validated_sql = validate_sql(generated_sql)
        if not is_valid:
            last_error = f"VALIDATION_FAILED: {validated_sql}"
            logger.warning(
                "SQL Direct: validation failed (intento %d/%d): %s | SQL: %s",
                retry_count + 1, MAX_RETRIES + 1, validated_sql, generated_sql[:200],
            )
            write_audit(
                message=message,
                sql_generated=generated_sql,
                status=f"validation_failed{'_retry' + str(retry_count) if retry_count else ''}",
                error_detail=validated_sql,
            )
            if retry_count >= MAX_RETRIES:
                return None
            messages.append(AIMessage(content=generated_sql))
            messages.append(HumanMessage(content=(
                f"El SQL que generaste fue RECHAZADO por el validador con este error:\n"
                f"  {validated_sql}\n\n"
                "Regeneralo corrigiendo el problema. Recordá:\n"
                "- Todas las tablas deben tener prefijo 'adempiere.'\n"
                "- Solo podés usar views lve_* y tablas del catálogo\n"
                "- Solo SELECT (no INSERT/UPDATE/DELETE/etc)\n"
                "- Incluye LIMIT 500\n"
                "Devolvé SOLO el SQL corregido, sin explicaciones."
            )))
            retry_count += 1
            continue

        sql_pre_enforce = validated_sql
        validated_sql, enforced = enforce_org_filter(validated_sql)
        if enforced:
            logger.info(
                "SQL Direct: filtro de orgs reales INYECTADO (Claude no lo aplicó)"
            )

        logger.info(
            "SQL Direct: executing (intento %d/%d): %s",
            retry_count + 1, MAX_RETRIES + 1, validated_sql[:300],
        )

        try:
            cols, rows, elapsed_ms = execute_sql(validated_sql)
            if retry_count > 0:
                logger.info(
                    "SQL Direct: éxito en intento %d de %d",
                    retry_count + 1, MAX_RETRIES + 1,
                )
            break
        except Exception as exc:
            last_error = str(exc)
            logger.warning(
                "SQL Direct: execution error (intento %d/%d): %s | SQL: %s",
                retry_count + 1, MAX_RETRIES + 1, exc, validated_sql[:200],
            )
            write_audit(
                message=message,
                sql_generated=sql_pre_enforce,
                sql_final=validated_sql,
                org_filter_injected=enforced,
                status=f"execute_error{'_retry' + str(retry_count) if retry_count else ''}",
                error_detail=str(exc),
            )
            if retry_count >= MAX_RETRIES:
                return None
            messages.append(AIMessage(content=generated_sql))
            messages.append(HumanMessage(content=(
                f"El SQL que generaste falló al ejecutarse contra PostgreSQL con "
                f"este error:\n\n  {str(exc)[:600]}\n\n"
                "Regeneralo corrigiendo el problema específico. El error de "
                "PostgreSQL ya te dice qué está mal (columna inexistente, tipo "
                "incorrecto, etc.) y a veces sugiere la columna correcta con 'HINT:'. "
                "Seguí ese hint si está disponible.\n"
                "Devolvé SOLO el SQL corregido, sin explicaciones."
            )))
            retry_count += 1
            continue

    if not cols and not rows:
        write_audit(
            message=message,
            sql_generated=sql_pre_enforce,
            sql_final=validated_sql,
            org_filter_injected=enforced,
            status="retry_exhausted",
            error_detail=last_error,
        )
        return None

    if not rows and not cols:
        logger.info("SQL Direct: empty result")
        write_audit(
            message=message,
            sql_generated=sql_pre_enforce,
            sql_final=validated_sql,
            org_filter_injected=enforced,
            rows_returned=0,
            elapsed_ms=int(elapsed_ms),
            status="empty_result",
        )
        return {
            "response": (
                "Consulté la base de datos con esta pregunta y no se encontraron "
                "datos. Si crees que debería haber resultados, intenta reformular "
                "la pregunta con más detalle (período, organización, moneda)."
            ),
            "agent_used": "sql_direct",
            "metadata": {
                "sql_generated": validated_sql,
                "rows_returned": 0,
                "elapsed_ms": elapsed_ms,
                "classification": "sql_direct",
                "has_data": False,
            },
        }

    results_md = format_results_as_markdown(cols, rows)

    format_messages = [
        SystemMessage(content=FORMAT_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Pregunta del usuario: {message}\n\n"
            f"Datos obtenidos de iDempiere ({len(rows)} filas, {elapsed_ms:.0f}ms):\n\n"
            f"{results_md}"
        )),
    ]

    format_failed = False
    try:
        format_response = await llm.ainvoke(format_messages)
        final_response = format_response.content
    except Exception as exc:
        logger.error("SQL Direct: LLM format error (usando fallback markdown): %s", exc)
        format_failed = True
        final_response = (
            "⚠️ *(El formateo automático de la respuesta falló — "
            "mostrando datos crudos. Los números SÍ son correctos.)*\n\n"
            f"**Resultado de la consulta** ({len(rows)} filas):\n\n{results_md}"
        )

    logger.info(
        "SQL Direct: success. %d rows in %.0fms. SQL: %s",
        len(rows), elapsed_ms, validated_sql[:100],
    )

    success_status = (
        "success" if retry_count == 0
        else f"success_after_retry{retry_count}"
    )
    audit_id = write_audit(
        message=message,
        sql_generated=sql_pre_enforce,
        sql_final=validated_sql,
        org_filter_injected=enforced,
        rows_returned=len(rows),
        elapsed_ms=int(elapsed_ms),
        format_failed=format_failed,
        status=success_status,
    )

    return {
        "response": final_response,
        "agent_used": "sql_direct",
        "metadata": {
            "sql_generated": validated_sql,
            "rows_returned": len(rows),
            "elapsed_ms": elapsed_ms,
            "classification": "sql_direct",
            "has_data": True,
            "format_failed": format_failed,
            "audit_id": audit_id,
        },
    }

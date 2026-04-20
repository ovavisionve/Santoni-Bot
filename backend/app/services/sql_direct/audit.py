"""Audit log for SQL Direct queries."""

import logging

from app.config import get_settings
from app.database import SessionLocal
from app.services.llm_factory import is_claude_available

logger = logging.getLogger("santonibot.sql_direct")


def write_audit(
    message: str,
    sql_generated: str | None = None,
    sql_final: str | None = None,
    org_filter_injected: bool = False,
    rows_returned: int = 0,
    elapsed_ms: int = 0,
    format_failed: bool = False,
    status: str = "success",
    error_detail: str | None = None,
) -> int | None:
    """Guarda la traza del SQL en la tabla sql_audit de la DB local.

    Silencioso: si falla la escritura del audit log, no afecta la respuesta
    al usuario (la telemetría es best-effort).

    Returns el id de la fila insertada, o None si falló.
    """
    settings = get_settings()
    try:
        from app.models.sql_audit import SqlAudit
        db = SessionLocal()
        try:
            row = SqlAudit(
                message=message[:2000],
                sql_generated=sql_generated,
                sql_final=sql_final,
                org_filter_injected=org_filter_injected,
                rows_returned=rows_returned,
                elapsed_ms=elapsed_ms,
                format_failed=format_failed,
                llm_provider=(
                    "anthropic"
                    if (settings.use_claude_for_sql and is_claude_available())
                    else settings.ai_provider
                ),
                llm_model=(
                    settings.anthropic_model
                    if (settings.use_claude_for_sql and is_claude_available())
                    else settings.openrouter_model
                ),
                status=status,
                error_detail=error_detail[:2000] if error_detail else None,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row.id
        finally:
            db.close()
    except Exception as exc:
        logger.debug("SQL audit write failed (no crítico): %s", exc)
        return None

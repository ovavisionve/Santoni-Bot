"""Admin endpoints: SQL audit log listing and detail."""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, Float, text

from app.database import get_db
from app.middleware.auth import require_admin, require_supervisor_or_admin
from app.models.user import User
from app.services.audit import log_action
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/admin", tags=["Administración"])

@router.get("/sql-audit")
def list_sql_audit(
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = Query(None, description="Buscar en message (ILIKE)"),
    min_rows: int | None = None,
    max_rows: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Lista las últimas queries de SQL Directo con filtros opcionales.

    Filtros:
      - status: success, empty_result, validation_failed, execute_error,
        llm_declined, llm_gen_error
      - q: busca texto en el message del usuario
      - min_rows / max_rows: filtra por cantidad de filas devueltas
        (ej: max_rows=2 para encontrar queries sospechosamente chicas)

    Retorna resumen (sin SQL completo). Para ver el SQL usar /sql-audit/{id}.
    """
    from app.models.sql_audit import SqlAudit
    query = db.query(SqlAudit).order_by(SqlAudit.id.desc())
    if status_filter:
        query = query.filter(SqlAudit.status == status_filter)
    if q:
        query = query.filter(SqlAudit.message.ilike(f"%{q}%"))
    if min_rows is not None:
        query = query.filter(SqlAudit.rows_returned >= min_rows)
    if max_rows is not None:
        query = query.filter(SqlAudit.rows_returned <= max_rows)

    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": r.id,
                "message": r.message[:200],
                "status": r.status,
                "rows_returned": r.rows_returned,
                "elapsed_ms": r.elapsed_ms,
                "org_filter_injected": r.org_filter_injected,
                "format_failed": r.format_failed,
                "llm_provider": r.llm_provider,
                "llm_model": r.llm_model,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/sql-audit/{audit_id}")
def get_sql_audit_detail(
    audit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Devuelve el detalle completo de una entrada del audit log,
    incluyendo el SQL crudo generado por el LLM y el SQL final ejecutado.

    Útil para diagnosticar:
      - sql_generated ≠ sql_final → el enforcement inyectó algo
      - rows_returned chico para pregunta agregada → SQL restrictivo
      - format_failed=True → Claude falló formateando
    """
    from app.models.sql_audit import SqlAudit
    row = db.query(SqlAudit).filter(SqlAudit.id == audit_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Entrada no encontrada")
    return {
        "id": row.id,
        "message": row.message,
        "sql_generated": row.sql_generated,
        "sql_final": row.sql_final,
        "org_filter_injected": row.org_filter_injected,
        "rows_returned": row.rows_returned,
        "elapsed_ms": row.elapsed_ms,
        "format_failed": row.format_failed,
        "llm_provider": row.llm_provider,
        "llm_model": row.llm_model,
        "status": row.status,
        "error_detail": row.error_detail,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }

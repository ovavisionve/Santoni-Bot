"""
Audit log específico para SQL Directo.

Cada query que pasa por `sql_direct.process_with_sql_direct()` se guarda
acá con: la pregunta del usuario, el SQL que generó Claude, el SQL final
(post-enforcement), cuántas filas devolvió, cuánto tardó y si falló el
formateo.

Propósito: diagnosticar bugs en producción sin depender de logs truncados.
Cuando una pregunta devuelve datos raros, consultar esta tabla para ver:
  1. ¿Qué SQL generó Claude exactamente?
  2. ¿El enforcement modificó el SQL?
  3. ¿Cuántas filas volvieron? (1-2 filas para una pregunta agregada puede
     indicar SQL demasiado restrictivo — ver los bugs del 14/Abr/2026)
  4. ¿Claude recibió los datos y los formateó? (format_failed = True indica
     que cayó al fallback markdown crudo)

Retención: esta tabla crece 1-2 filas por query. Si llega a gigabytes,
agregar un proceso que borre filas > 90 días. Por ahora sin rotación.

Consulta típica desde psql:
  SELECT id, message, rows_returned, elapsed_ms, created_at
  FROM sql_audit ORDER BY id DESC LIMIT 20;

Para ver el SQL completo de una query específica:
  SELECT sql_generated, sql_final, format_failed
  FROM sql_audit WHERE id = XX;
"""
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SqlAudit(Base):
    __tablename__ = "sql_audit"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Pregunta original del usuario (puede ser larga, truncamos a 2000 chars)
    message: Mapped[str] = mapped_column(Text)
    # SQL que Claude generó (antes del enforcement)
    sql_generated: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SQL final que se ejecutó (después de enforcement, si aplicó)
    sql_final: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Si el enforcement inyectó el filtro de orgs
    org_filter_injected: Mapped[bool] = mapped_column(Boolean, default=False)
    # Filas retornadas
    rows_returned: Mapped[int] = mapped_column(Integer, default=0)
    # Tiempo de ejecución del SQL (no incluye LLM)
    elapsed_ms: Mapped[int] = mapped_column(Integer, default=0)
    # Si el formateo por Claude falló y cayó al markdown crudo
    format_failed: Mapped[bool] = mapped_column(Boolean, default=False)
    # LLM provider usado (anthropic / openrouter / groq)
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Modelo específico (claude-sonnet-4-6, etc.)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Razón de falla si no hubo datos (validación, execute_error, empty, etc.)
    status: Mapped[str] = mapped_column(String(30), default="success")
    # Detalle adicional (mensaje de error, ej)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

"""DataCatalogService — orchestrates schema discovery, profiling and indexing."""

import logging
from datetime import datetime
from typing import Any

from app.database import IdempiereSession

from .constants import DEPARTMENT_TABLES
from .department_stats import build_department_stats
from .discovery import (
    discover_relationships,
    discover_schema,
    profile_data,
    sample_data,
)
from .documents import build_catalog_documents

logger = logging.getLogger("santonibot.data_catalog")


class DataCatalogService:
    """Extrae y gestiona el catálogo de metadata de iDempiere."""

    def __init__(self):
        self._last_sync: datetime | None = None
        self._catalog: dict[str, Any] = {}
        self._sync_errors: list[str] = []

    @property
    def last_sync(self) -> datetime | None:
        return self._last_sync

    @property
    def catalog(self) -> dict[str, Any]:
        return self._catalog

    @property
    def sync_errors(self) -> list[str]:
        return self._sync_errors

    # ──────────────────────────────────────────────────────────────
    # Sync principal
    # ──────────────────────────────────────────────────────────────

    def sync(self) -> dict:
        """Ejecuta la sincronización completa:
        1. Descubre schema
        2. Perfila datos
        3. Muestrea datos
        4. Descubre relaciones
        5. Genera estadísticas departamentales
        6. Indexa todo en ChromaDB
        """
        self._sync_errors = []
        start_time = datetime.now()
        logger.info("Iniciando sincronización del catálogo de datos...")

        session = IdempiereSession()
        try:
            logger.info("Paso 1/5: Descubriendo schema...")
            schema = discover_schema(session, self._sync_errors)
            logger.info("  → %d tablas descubiertas", len(schema))

            logger.info("Paso 2/5: Perfilando datos...")
            profiles = profile_data(session, schema)
            logger.info("  → %d tablas perfiladas", len(profiles))

            logger.info("Paso 3/5: Muestreando datos...")
            samples = sample_data(session, schema)
            logger.info("  → %d tablas muestreadas", len(samples))

            logger.info("Paso 4/5: Descubriendo relaciones...")
            relationships = discover_relationships(session, self._sync_errors)
            logger.info("  → %d relaciones encontradas", len(relationships))

            logger.info("Paso 5/5: Generando estadísticas departamentales...")
            dept_stats = build_department_stats(session)

        except Exception as e:
            logger.error("Error fatal durante sincronización: %s", e, exc_info=True)
            self._sync_errors.append(f"fatal: {e}")
            return {
                "ok": False,
                "error": str(e),
                "errors": self._sync_errors,
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
            }
        finally:
            session.close()

        logger.info("Indexando en ChromaDB...")
        docs_by_dept = build_catalog_documents(
            schema, profiles, samples, relationships, dept_stats
        )
        try:
            index_result = self._index_to_chromadb(docs_by_dept)
        except Exception as e:
            logger.warning(
                "ChromaDB indexación falló (%s). El catálogo en memoria sigue disponible.", e
            )
            self._sync_errors.append(f"chromadb_index: {e}")
            index_result = {"total_docs": 0, "departments_updated": []}

        self._catalog = {
            "schema": schema,
            "profiles": profiles,
            "relationships": relationships,
            "dept_stats": dept_stats,
            "tables_count": len(schema),
            "total_rows": sum(t.get("row_count", 0) for t in schema.values()),
        }
        self._last_sync = datetime.now()

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            "Sincronización completada en %.1fs. %d tablas, %d documentos indexados.",
            duration, len(schema), index_result.get("total_docs", 0),
        )

        return {
            "ok": True,
            "duration_seconds": round(duration, 1),
            "tables_discovered": len(schema),
            "tables_profiled": len(profiles),
            "relationships_found": len(relationships),
            "documents_indexed": index_result.get("total_docs", 0),
            "departments_updated": index_result.get("departments_updated", []),
            "errors": self._sync_errors if self._sync_errors else None,
            "last_sync": self._last_sync.isoformat(),
        }

    def _index_to_chromadb(self, docs_by_dept: dict[str, list[str]]) -> dict:
        """Indexa los documentos generados en ChromaDB via RAGService."""
        try:
            from app.services.rag_service import get_rag_service
            rag = get_rag_service()
        except Exception as e:
            logger.warning("ChromaDB no disponible para indexación: %s", e)
            return {"total_docs": 0, "departments_updated": []}

        total_docs = 0
        departments_updated = []

        for dept, docs in docs_by_dept.items():
            for i, doc in enumerate(docs):
                result = rag.add_document(
                    department=dept,
                    text=doc,
                    metadata={
                        "source": "data_catalog",
                        "catalog_doc_index": str(i),
                        "sync_time": datetime.now().isoformat(),
                    },
                )
                if result.get("ok"):
                    total_docs += result.get("chunks_stored", 0)

            departments_updated.append(dept)

        return {
            "total_docs": total_docs,
            "departments_updated": departments_updated,
        }

    # ──────────────────────────────────────────────────────────────
    # Consulta del catálogo en memoria
    # ──────────────────────────────────────────────────────────────

    def get_table_info(self, table_name: str) -> dict | None:
        """Retorna información del schema de una tabla específica."""
        return self._catalog.get("schema", {}).get(table_name)

    def get_department_context(self, department: str) -> str | None:
        """Genera un contexto resumido del catálogo para un departamento.

        Útil para inyectar en el prompt del agente.
        """
        if not self._catalog or not self._last_sync:
            return None

        schema = self._catalog.get("schema", {})
        profiles = self._catalog.get("profiles", {})
        dept_stats = self._catalog.get("dept_stats", {})
        tables = DEPARTMENT_TABLES.get(department, [])

        if not tables:
            return None

        parts = [
            f"CATÁLOGO DE DATOS iDEMPIERE (sincronizado: {self._last_sync.strftime('%Y-%m-%d %H:%M')})",
            "",
        ]

        for table in tables:
            if table not in schema:
                continue
            info = schema[table]
            parts.append(f"• {table}: {info['row_count']:,} registros, "
                         f"{len(info['columns'])} columnas")

            if table in profiles and "date_range" in profiles[table]:
                dr = profiles[table]["date_range"]
                parts.append(f"  Datos desde {dr['min_date']} hasta {dr['max_date']}")

        if department in dept_stats:
            parts.append("")
            parts.append(f"Estadísticas {department}:")
            for key, val in dept_stats[department].items():
                if isinstance(val, list) and len(val) > 10:
                    parts.append(f"  {key}: {len(val)} elementos")
                elif isinstance(val, list):
                    parts.append(f"  {key}: {', '.join(str(v) for v in val)}")
                else:
                    parts.append(f"  {key}: {val}")

        return "\n".join(parts)

    def get_status(self) -> dict:
        """Retorna el estado actual del catálogo."""
        return {
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "tables_count": self._catalog.get("tables_count", 0),
            "total_rows": self._catalog.get("total_rows", 0),
            "relationships_count": len(self._catalog.get("relationships", [])),
            "errors": self._sync_errors if self._sync_errors else None,
            "is_synced": self._last_sync is not None,
        }


# ──────────────────────────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────────────────────────

_catalog_service: DataCatalogService | None = None


def get_catalog_service() -> DataCatalogService:
    """Retorna la instancia singleton del servicio de catálogo."""
    global _catalog_service
    if _catalog_service is None:
        _catalog_service = DataCatalogService()
    return _catalog_service

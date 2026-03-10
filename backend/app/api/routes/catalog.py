"""
API routes para el catálogo de datos de iDempiere.

Permite consultar el estado del catálogo y disparar sincronizaciones manuales.
Requiere autenticación de administrador.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.middleware.auth import require_admin
from app.models.user import User

router = APIRouter(prefix="/catalog", tags=["Catálogo de Datos"])


# ------------------------------------------------------------------
# Response schemas
# ------------------------------------------------------------------

class CatalogStatusResponse(BaseModel):
    ok: bool
    last_sync: str | None = None
    tables_count: int = 0
    total_rows: int = 0
    relationships_count: int = 0
    is_synced: bool = False
    errors: list[str] | None = None


class SyncResponse(BaseModel):
    ok: bool
    duration_seconds: float | None = None
    tables_discovered: int | None = None
    tables_profiled: int | None = None
    relationships_found: int | None = None
    documents_indexed: int | None = None
    departments_updated: list[str] | None = None
    errors: list[str] | None = None
    error: str | None = None
    last_sync: str | None = None


class DepartmentContextResponse(BaseModel):
    ok: bool
    department: str
    context: str | None = None
    error: str | None = None


class TableInfoResponse(BaseModel):
    ok: bool
    table_name: str
    row_count: int | None = None
    columns: list[dict] | None = None
    column_names: list[str] | None = None
    error: str | None = None


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@router.get("/status", response_model=CatalogStatusResponse)
def catalog_status(
    admin: User = Depends(require_admin),
):
    """Consultar el estado actual del catálogo de datos."""
    from app.services.data_catalog import get_catalog_service

    catalog = get_catalog_service()
    status = catalog.get_status()

    return CatalogStatusResponse(ok=True, **status)


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    admin: User = Depends(require_admin),
):
    """
    Disparar una sincronización manual del catálogo de datos.

    Extrae metadata de iDempiere (schema, perfiles, relaciones,
    estadísticas) y la indexa en ChromaDB para que los agentes
    puedan consultarla.
    """
    from app.services.catalog_sync import trigger_manual_sync

    result = await trigger_manual_sync()

    if not result.get("ok"):
        raise HTTPException(
            status_code=503,
            detail=result.get("error", "Error durante la sincronización"),
        )

    return SyncResponse(**result)


@router.get("/department/{department}", response_model=DepartmentContextResponse)
def get_department_context(
    department: str,
    admin: User = Depends(require_admin),
):
    """
    Obtener el contexto del catálogo para un departamento específico.

    Retorna un resumen de las tablas, registros y estadísticas
    que el agente de ese departamento tiene disponible.
    """
    from app.services.data_catalog import get_catalog_service, DEPARTMENT_TABLES

    if department not in DEPARTMENT_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Departamento inválido. Opciones: {', '.join(DEPARTMENT_TABLES.keys())}",
        )

    catalog = get_catalog_service()
    context = catalog.get_department_context(department)

    if context is None:
        return DepartmentContextResponse(
            ok=True,
            department=department,
            context=None,
            error="Catálogo no sincronizado aún. Ejecute POST /api/catalog/sync",
        )

    return DepartmentContextResponse(
        ok=True,
        department=department,
        context=context,
    )


@router.get("/table/{table_name}", response_model=TableInfoResponse)
def get_table_info(
    table_name: str,
    admin: User = Depends(require_admin),
):
    """Obtener información detallada de una tabla específica del catálogo."""
    from app.services.data_catalog import get_catalog_service

    catalog = get_catalog_service()
    info = catalog.get_table_info(table_name)

    if info is None:
        return TableInfoResponse(
            ok=False,
            table_name=table_name,
            error="Tabla no encontrada en el catálogo. ¿Se ha ejecutado la sincronización?",
        )

    return TableInfoResponse(
        ok=True,
        table_name=table_name,
        row_count=info.get("row_count"),
        columns=info.get("columns"),
        column_names=info.get("column_names"),
    )

"""
API routes for managing the RAG knowledge base.

All routes require administrator authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.middleware.auth import require_admin
from app.models.user import User
from app.services.rag_service import get_rag_service, DEPARTMENTS

router = APIRouter(prefix="/knowledge", tags=["Base de Conocimiento"])


# ------------------------------------------------------------------
# Request / response schemas
# ------------------------------------------------------------------

class UploadDocumentRequest(BaseModel):
    department: str = Field(
        ...,
        description="Departamento destino (ventas, finanzas, contabilidad, rrhh, produccion, compras_insumos, compras_productores, general)",
    )
    text: str = Field(
        ...,
        min_length=10,
        description="Texto del documento a agregar a la base de conocimiento",
    )
    title: str | None = Field(
        None,
        description="Título opcional del documento",
    )
    source: str | None = Field(
        None,
        description="Fuente u origen del documento",
    )


class UploadDocumentResponse(BaseModel):
    ok: bool
    department: str | None = None
    doc_id: str | None = None
    chunks_stored: int | None = None
    error: str | None = None


class CollectionInfo(BaseModel):
    department: str
    collection_name: str
    document_count: int


class CollectionsResponse(BaseModel):
    ok: bool
    collections: list[CollectionInfo] = []
    error: str | None = None


class ClearCollectionResponse(BaseModel):
    ok: bool
    department: str | None = None
    message: str | None = None
    error: str | None = None


class QueryRequest(BaseModel):
    department: str = Field(
        ...,
        description="Departamento a consultar",
    )
    question: str = Field(
        ...,
        min_length=3,
        description="Pregunta para buscar en la base de conocimiento",
    )
    n_results: int = Field(
        3,
        ge=1,
        le=10,
        description="Cantidad de resultados a retornar",
    )


class QueryResponse(BaseModel):
    ok: bool
    results: list[str] = []
    error: str | None = None


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@router.post("/upload", response_model=UploadDocumentResponse)
def upload_document(
    body: UploadDocumentRequest,
    admin: User = Depends(require_admin),
):
    """
    Upload a text document to a department's knowledge base.

    The text is automatically split into chunks, embedded, and stored
    in ChromaDB for later retrieval by the department agents.
    """
    if body.department not in DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Departamento inválido. Opciones: {', '.join(DEPARTMENTS)}",
        )

    metadata: dict[str, str] = {}
    if body.title:
        metadata["title"] = body.title
    if body.source:
        metadata["source"] = body.source
    metadata["uploaded_by"] = admin.username

    rag = get_rag_service()
    result = rag.add_document(
        department=body.department,
        text=body.text,
        metadata=metadata,
    )

    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("error", "Error al procesar el documento"),
        )

    return UploadDocumentResponse(**result)


@router.get("/collections", response_model=CollectionsResponse)
def list_collections(
    admin: User = Depends(require_admin),
):
    """List all knowledge-base collections with their document counts."""
    rag = get_rag_service()
    collections = rag.list_collections()

    if not collections:
        return CollectionsResponse(
            ok=True,
            collections=[],
            error="ChromaDB no disponible o sin colecciones" if not collections else None,
        )

    return CollectionsResponse(
        ok=True,
        collections=[CollectionInfo(**c) for c in collections],
    )


@router.delete("/collection/{department}", response_model=ClearCollectionResponse)
def clear_collection(
    department: str,
    admin: User = Depends(require_admin),
):
    """Clear all documents from a department's knowledge-base collection."""
    if department not in DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Departamento inválido. Opciones: {', '.join(DEPARTMENTS)}",
        )

    rag = get_rag_service()
    result = rag.clear_collection(department)

    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.get("error", "Error al limpiar la colección"),
        )

    return ClearCollectionResponse(**result)


@router.post("/query", response_model=QueryResponse)
def query_knowledge_base(
    body: QueryRequest,
    admin: User = Depends(require_admin),
):
    """
    Search the knowledge base for a department.

    Useful for testing and verifying what the RAG system returns
    before agents use it.
    """
    if body.department not in DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Departamento inválido. Opciones: {', '.join(DEPARTMENTS)}",
        )

    rag = get_rag_service()
    results = rag.query(
        department=body.department,
        question=body.question,
        n_results=body.n_results,
    )

    return QueryResponse(ok=True, results=results)

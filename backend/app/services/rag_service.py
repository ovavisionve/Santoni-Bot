"""
RAG (Retrieval-Augmented Generation) service using ChromaDB.

Provides document storage and semantic retrieval for each department's
knowledge base. Used by agents to enrich their responses with
company policies, procedures, and contextual business information.

ChromaDB is optional -- if the service is unavailable the rest of
the application continues to work normally.
"""

import logging
import uuid
from typing import Any

import chromadb
from chromadb.errors import ChromaError

from app.config import get_settings

logger = logging.getLogger("santonibot.rag")

settings = get_settings()

# All valid collection (department) names
DEPARTMENTS = [
    "general",
    "finanzas",
    "contabilidad",
    "ventas",
    "rrhh",
    "produccion",
    "compras_insumos",
    "compras_productores",
]

# Chunking parameters
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split *text* into chunks of approximately *chunk_size* characters,
    with *overlap* characters shared between consecutive chunks.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # Try to break at a sentence or word boundary
        if end < len(text):
            # Look for the last period, newline, or space within the chunk
            for sep in ("\n\n", "\n", ". ", " "):
                boundary = text.rfind(sep, start + chunk_size // 2, end)
                if boundary != -1:
                    end = boundary + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap
        # Avoid infinite loop on edge cases
        if start >= len(text) or end >= len(text):
            break

    return chunks


class RAGService:
    """Manages ChromaDB collections and provides RAG operations."""

    def __init__(self) -> None:
        self._client: chromadb.HttpClient | None = None
        self._available: bool = False
        self._unavailable_warned: bool = False
        self._connect()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        """Attempt to connect to ChromaDB. Fail silently if unavailable."""
        try:
            self._client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            # Quick heartbeat to validate the connection
            self._client.heartbeat()
            self._available = True
            self._unavailable_warned = False
            logger.info(
                "ChromaDB connected at %s:%s",
                settings.chroma_host,
                settings.chroma_port,
            )
        except Exception as exc:
            self._client = None
            self._available = False
            if not self._unavailable_warned:
                logger.warning(
                    "ChromaDB not available (%s). RAG features disabled.",
                    exc,
                )
                self._unavailable_warned = True

    def _ensure_connection(self) -> bool:
        """Return True if ChromaDB is reachable, attempting reconnect if needed."""
        if self._available and self._client is not None:
            try:
                self._client.heartbeat()
                return True
            except Exception:
                self._available = False

        # Try to reconnect
        self._connect()
        return self._available

    def _get_collection(self, department: str) -> Any:
        """
        Get or create a ChromaDB collection for the given department.
        Returns ``None`` if ChromaDB is unavailable.
        """
        if not self._ensure_connection() or self._client is None:
            return None

        collection_name = f"santonibot_{department}"
        try:
            return self._client.get_or_create_collection(
                name=collection_name,
                metadata={"department": department},
            )
        except (ChromaError, KeyError) as exc:
            logger.error("Error getting collection '%s': %s", collection_name, exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_document(
        self,
        department: str,
        text: str,
        metadata: dict[str, str] | None = None,
    ) -> dict:
        """
        Split *text* into chunks, embed them, and store in the
        department's ChromaDB collection.

        Returns a summary dict with the number of chunks stored.
        """
        if department not in DEPARTMENTS:
            return {"ok": False, "error": f"Departamento inválido: {department}"}

        collection = self._get_collection(department)
        if collection is None:
            return {"ok": False, "error": "ChromaDB no disponible"}

        chunks = _chunk_text(text)
        if not chunks:
            return {"ok": False, "error": "El documento está vacío"}

        base_metadata = metadata or {}
        base_metadata["department"] = department

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, str]] = []

        doc_id = uuid.uuid4().hex[:12]

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{department}_{doc_id}_{idx}"
            chunk_meta = {**base_metadata, "chunk_index": str(idx), "doc_id": doc_id}
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append(chunk_meta)

        try:
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info(
                "Added %d chunks to collection '%s' (doc_id=%s)",
                len(chunks),
                department,
                doc_id,
            )
            return {
                "ok": True,
                "department": department,
                "doc_id": doc_id,
                "chunks_stored": len(chunks),
            }
        except ChromaError as exc:
            logger.error("Error adding document to '%s': %s", department, exc)
            return {"ok": False, "error": str(exc)}

    def query(
        self,
        department: str,
        question: str,
        n_results: int = 3,
    ) -> list[str]:
        """
        Query the department's collection for chunks relevant to *question*.

        Returns a list of document strings (may be empty).
        """
        if department not in DEPARTMENTS:
            return []

        collection = self._get_collection(department)
        if collection is None:
            return []

        try:
            # Only query if the collection actually has documents
            if collection.count() == 0:
                return []

            results = collection.query(
                query_texts=[question],
                n_results=min(n_results, collection.count()),
            )
            documents = results.get("documents", [[]])[0]
            return [doc for doc in documents if doc]
        except ChromaError as exc:
            logger.error("Error querying collection '%s': %s", department, exc)
            return []
        except Exception as exc:
            logger.warning("Unexpected error querying RAG for '%s': %s", department, exc)
            return []

    def get_context_for_agent(self, department: str, question: str) -> str | None:
        """
        Retrieve relevant context for an agent and return it as a
        formatted string ready to be injected into the prompt.

        Also queries the ``general`` collection in addition to the
        department-specific one, so company-wide policies are always
        available.

        Returns ``None`` when no relevant context is found.
        """
        all_chunks: list[str] = []

        # Department-specific context
        dept_chunks = self.query(department, question, n_results=3)
        all_chunks.extend(dept_chunks)

        # General / company-wide context (skip if already querying general)
        if department != "general":
            general_chunks = self.query("general", question, n_results=2)
            all_chunks.extend(general_chunks)

        if not all_chunks:
            return None

        context_parts = "\n---\n".join(all_chunks)
        return (
            "CONTEXTO DE LA BASE DE CONOCIMIENTO INTERNA:\n"
            "Usa la siguiente información como referencia adicional "
            "para responder la consulta del usuario. "
            "Si la información no es relevante, ignórala.\n\n"
            f"{context_parts}"
        )

    def list_collections(self) -> list[dict]:
        """
        Return a list of dicts with collection name, department, and
        document count for every department collection.
        """
        if not self._ensure_connection() or self._client is None:
            return []

        result: list[dict] = []
        for dept in DEPARTMENTS:
            collection = self._get_collection(dept)
            if collection is not None:
                try:
                    count = collection.count()
                except ChromaError:
                    count = -1
                result.append({
                    "department": dept,
                    "collection_name": f"santonibot_{dept}",
                    "document_count": count,
                })
        return result

    def clear_collection(self, department: str) -> dict:
        """Delete all documents in a department's collection."""
        if department not in DEPARTMENTS:
            return {"ok": False, "error": f"Departamento inválido: {department}"}

        if not self._ensure_connection() or self._client is None:
            return {"ok": False, "error": "ChromaDB no disponible"}

        collection_name = f"santonibot_{department}"
        try:
            self._client.delete_collection(name=collection_name)
            logger.info("Cleared collection '%s'", collection_name)
            return {"ok": True, "department": department, "message": "Colección eliminada"}
        except ChromaError as exc:
            logger.error("Error clearing collection '%s': %s", collection_name, exc)
            return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    """Return the module-level RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service

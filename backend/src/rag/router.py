"""RAG and Data Bank API endpoints"""

from fastapi import APIRouter, Query, status

from src.core.config import settings
from src.core.exceptions import ConflictError
from src.core.logging.logger_config import get_logger
from src.core.schemas import PaginatedResponse, collection_response
from src.rag.dependencies import DataBankServiceDep, RetrievalServiceDep
from src.rag.models import DataBankEntry
from src.rag.retrieval_service import RetrievalService
from src.rag.schemas import (
    DataBankCreate,
    DataBankResponse,
    DataBankUpdate,
    RAGSearchRequest,
    RagStatusResponse,
    RerankStatus,
    RetrievedChunk,
)

logger = get_logger(__name__)

data_bank_router = APIRouter(prefix="/api/data-bank", tags=["data-bank"])
rag_router = APIRouter(prefix="/api/rag", tags=["rag"])


async def _index_entry(retrieval: RetrievalService | None, entry: DataBankEntry) -> None:
    """Chunk and embed a data-bank entry for retrieval (best-effort; already saved).

    No-op when RAG is disabled (retrieval is None). A failed embed must not fail
    the CRUD request — the entry persists and can be re-indexed on next update.
    """
    if retrieval is None:
        return
    try:
        await retrieval.vectorize_data_bank_entry(
            entry_id=entry.id,
            content=entry.content,
            model_name=settings.rag.embedding.model,
            dimensions=settings.rag.embedding.dimensions,
            chunk_size=settings.rag.chunk_size,
            chunk_overlap=settings.rag.chunk_overlap,
        )
    except Exception:
        logger.warning("data_bank_vectorize_failed", entry_id=entry.id, exc_info=True)


# -- Data Bank CRUD --


@data_bank_router.get("/", response_model=PaginatedResponse[DataBankResponse])
def list_entries(
    service: DataBankServiceDep,
    scope: str | None = Query(None, description="Filter by scope: global, character, chat"),
    character_id: str | None = Query(None, description="Filter by character ID"),
    chat_id: str | None = Query(None, description="Filter by chat ID"),
):
    """List data bank entries with optional filtering"""
    return collection_response(
        service.list_entries(scope=scope, character_id=character_id, chat_id=chat_id)
    )


@data_bank_router.post("/", response_model=DataBankResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    body: DataBankCreate,
    service: DataBankServiceDep,
    retrieval: RetrievalServiceDep,
):
    """Create a new data bank entry (indexed for RAG when enabled)."""
    entry = service.create(
        name=body.name,
        content=body.content,
        scope=body.scope,
        character_id=body.character_id,
        chat_id=body.chat_id,
    )
    await _index_entry(retrieval, entry)
    return entry


@data_bank_router.get("/{entry_id}", response_model=DataBankResponse)
def get_entry(entry_id: str, service: DataBankServiceDep):
    """Get data bank entry by ID"""
    return service.get_by_id(entry_id)


@data_bank_router.put("/{entry_id}", response_model=DataBankResponse)
async def update_entry(
    entry_id: str,
    body: DataBankUpdate,
    service: DataBankServiceDep,
    retrieval: RetrievalServiceDep,
):
    """Update a data bank entry (re-indexed for RAG when enabled)."""
    entry = service.update(
        entry_id=entry_id,
        name=body.name,
        content=body.content,
        scope=body.scope,
    )
    # vectorize_data_bank_entry purges the old chunks first, so this re-indexes cleanly.
    await _index_entry(retrieval, entry)
    return entry


@data_bank_router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    service: DataBankServiceDep,
    retrieval: RetrievalServiceDep,
):
    """Delete a data bank entry and purge its embeddings."""
    service.delete(entry_id)
    if retrieval is not None:
        try:
            await retrieval.remove_embeddings("data_bank", entry_id)
        except Exception:
            logger.warning("data_bank_embedding_purge_failed", entry_id=entry_id, exc_info=True)
    return None


# -- RAG Search --


@rag_router.post("/search", response_model=list[RetrievedChunk])
async def search(
    body: RAGSearchRequest,
    retrieval: RetrievalServiceDep,
):
    """Manual semantic search across embeddings"""
    if retrieval is None:
        raise ConflictError("RAG is disabled. Set RAG__ENABLED=true to use semantic search.")
    return await retrieval.retrieve(
        chat_id=body.chat_id or "",
        query_text=body.query,
        character_id=body.character_id,
        max_results=body.max_results,
        threshold=body.threshold,
    )


@rag_router.get("/status", response_model=RagStatusResponse)
def rag_status():
    """Return RAG system status and embedding provider info"""
    rag = settings.rag
    return RagStatusResponse(
        enabled=rag.enabled,
        provider=rag.embedding.provider,
        model=rag.embedding.model,
        dimensions=rag.embedding.dimensions,
        chunk_size=rag.chunk_size,
        chunk_overlap=rag.chunk_overlap,
        similarity_threshold=rag.similarity_threshold,
        max_results=rag.max_results,
        rerank=RerankStatus(
            enabled=rag.rerank.enabled,
            model=rag.rerank.model,
            candidates=rag.rerank.candidates,
            score_threshold=rag.rerank.score_threshold,
        ),
    )

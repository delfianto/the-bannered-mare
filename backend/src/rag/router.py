"""RAG and Data Bank API endpoints"""

from fastapi import APIRouter, Query, status

from src.core.config import settings
from src.core.exceptions import ConflictError
from src.core.schemas import PaginatedResponse, collection_response
from src.rag.dependencies import (
    DataBankServiceDep,
    DataBankWriteServiceDep,
    RetrievalServiceDep,
)
from src.rag.schemas import (
    DataBankCreate,
    DataBankResponse,
    DataBankUpdate,
    RAGSearchRequest,
    RagStatusResponse,
    RerankStatus,
    RetrievedChunk,
)

data_bank_router = APIRouter(prefix="/api/data-bank", tags=["data-bank"])
rag_router = APIRouter(prefix="/api/rag", tags=["rag"])


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
async def create_entry(body: DataBankCreate, service: DataBankWriteServiceDep):
    """Create a new data bank entry (indexed for RAG when enabled)."""
    return await service.create(
        name=body.name,
        content=body.content,
        scope=body.scope,
        character_id=body.character_id,
        chat_id=body.chat_id,
    )


@data_bank_router.get("/{entry_id}", response_model=DataBankResponse)
def get_entry(entry_id: str, service: DataBankServiceDep):
    """Get data bank entry by ID"""
    return service.get_by_id(entry_id)


@data_bank_router.put("/{entry_id}", response_model=DataBankResponse)
async def update_entry(entry_id: str, body: DataBankUpdate, service: DataBankWriteServiceDep):
    """Update a data bank entry (re-indexed for RAG when enabled)."""
    return await service.update(
        entry_id=entry_id,
        name=body.name,
        content=body.content,
        scope=body.scope,
    )


@data_bank_router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(entry_id: str, service: DataBankWriteServiceDep):
    """Delete a data bank entry and purge its embeddings."""
    await service.delete(entry_id)
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

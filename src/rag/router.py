"""RAG and Data Bank API endpoints"""

from fastapi import APIRouter, HTTPException, Query, status

from src.core.config import settings
from src.rag.dependencies import DataBankServiceDep, RetrievalServiceDep
from src.rag.schemas import (
    DataBankCreate,
    DataBankResponse,
    DataBankUpdate,
    RAGSearchRequest,
    RetrievedChunk,
)

data_bank_router = APIRouter(prefix="/api/data-bank", tags=["data-bank"])
rag_router = APIRouter(prefix="/api/rag", tags=["rag"])


# -- Data Bank CRUD --


@data_bank_router.get("/", response_model=list[DataBankResponse])
def list_entries(
    service: DataBankServiceDep,
    scope: str | None = Query(None, description="Filter by scope: global, character, chat"),
    character_id: str | None = Query(None, description="Filter by character ID"),
    chat_id: str | None = Query(None, description="Filter by chat ID"),
):
    """List data bank entries with optional filtering"""
    return service.list_entries(scope=scope, character_id=character_id, chat_id=chat_id)


@data_bank_router.post("/", response_model=DataBankResponse, status_code=status.HTTP_201_CREATED)
def create_entry(
    body: DataBankCreate,
    service: DataBankServiceDep,
):
    """Create a new data bank entry"""
    return service.create(
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
def update_entry(
    entry_id: str,
    body: DataBankUpdate,
    service: DataBankServiceDep,
):
    """Update data bank entry"""
    return service.update(
        entry_id=entry_id,
        name=body.name,
        content=body.content,
        scope=body.scope,
    )


@data_bank_router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: str, service: DataBankServiceDep):
    """Delete data bank entry"""
    service.delete(entry_id)
    return None


# -- RAG Search --


@rag_router.post("/search", response_model=list[RetrievedChunk])
async def search(
    body: RAGSearchRequest,
    retrieval: RetrievalServiceDep,
):
    """Manual semantic search across embeddings"""
    if retrieval is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="RAG is disabled. Set RAG__ENABLED=true to use semantic search.",
        )
    return await retrieval.retrieve(
        chat_id=body.chat_id or "",
        query_text=body.query,
        character_id=body.character_id,
        max_results=body.max_results,
        threshold=body.threshold,
    )


@rag_router.get("/status")
def rag_status():
    """Return RAG system status and embedding provider info"""
    rag = settings.rag
    return {
        "enabled": rag.enabled,
        "provider": rag.embedding.provider,
        "model": rag.embedding.model,
        "dimensions": rag.embedding.dimensions,
        "chunk_size": rag.chunk_size,
        "chunk_overlap": rag.chunk_overlap,
        "similarity_threshold": rag.similarity_threshold,
        "max_results": rag.max_results,
    }

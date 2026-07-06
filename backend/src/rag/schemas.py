"""Pydantic schemas for RAG and Data Bank API"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DataBankCreate(BaseModel):
    """Schema for creating a data bank entry"""

    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    scope: str = Field("global", max_length=20)
    character_id: str | None = None
    chat_id: str | None = None


class DataBankUpdate(BaseModel):
    """Schema for updating a data bank entry"""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    scope: str | None = Field(default=None, max_length=20)


class DataBankResponse(DataBankCreate):
    """Schema for data bank entry response"""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RAGSearchRequest(BaseModel):
    """Schema for manual RAG search"""

    query: str = Field(..., min_length=1)
    chat_id: str | None = None
    character_id: str | None = None
    max_results: int = Field(5, ge=1, le=50)
    threshold: float = Field(0.3, ge=0.0, le=1.0)


class RetrievedChunk(BaseModel):
    """Schema for a retrieved RAG chunk"""

    content: str
    source_type: str
    source_id: str
    score: float
    chunk_index: int

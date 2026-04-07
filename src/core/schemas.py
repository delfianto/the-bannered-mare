"""Common schemas for API responses"""

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    """
    Standard metadata for all paginated responses.
    Fields are optional to support both Cursor (infinite scroll) and Offset (page numbers) strategies.
    """

    limit: int = Field(..., description="The limit applied to the query")
    has_more: bool = Field(..., description="Whether there are more items available")

    # Cursor-specific
    cursor: str | None = Field(None, description="Cursor for the next page (for infinite scroll)")

    # Offset-specific (Page Numbers)
    total: int | None = Field(None, description="Total count of items (for page-based pagination)")
    page: int | None = Field(None, description="Current page number (for page-based pagination)")


class PaginatedResponse[T](BaseModel):
    """
    Generic wrapper for list responses.
    Usage: PaginatedResponse[MessageResponse] or PaginatedResponse[ChatSessionResponse]
    """

    items: list[T]
    meta: PaginationMeta

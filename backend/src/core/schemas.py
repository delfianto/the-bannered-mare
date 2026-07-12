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
    cursor: str | None = Field(
        default=None, description="Cursor for the next page (for infinite scroll)"
    )

    # Offset-specific (Page Numbers)
    total: int | None = Field(
        default=None, description="Total count of items (for page-based pagination)"
    )
    page: int | None = Field(
        default=None, description="Current page number (for page-based pagination)"
    )


class PaginatedResponse[T](BaseModel):
    """
    Generic wrapper for list responses.
    Usage: PaginatedResponse[MessageResponse] or PaginatedResponse[ChatSessionResponse]
    """

    items: list[T]
    meta: PaginationMeta


def page_response[T](items: list[T], total: int, page: int, limit: int) -> PaginatedResponse[T]:
    """Build an offset/page-based PaginatedResponse.

    Collapses the identical has_more/meta construction duplicated across the
    list routers. ``has_more`` is ``page * limit < total`` (offset + limit).
    """
    return PaginatedResponse(
        items=items,
        meta=PaginationMeta(
            limit=limit, has_more=(page * limit) < total, total=total, page=page, cursor=None
        ),
    )

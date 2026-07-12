"""Common schemas for API responses"""

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, Field, FieldSerializationInfo, field_serializer


class BaseFilterParams(BaseModel):
    """Base for query-parameter models that become a repository filter dict.

    Subclasses declare their allowed filter fields (all optional); ``to_filter_dict``
    drops the unset (``None``) ones so only the filters the caller actually provided
    reach the repository.
    """

    def to_filter_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class AvatarUrlMixin(BaseModel):
    """Serialize stored avatar filenames to their API URL.

    Mixed into the character / persona / chat response schemas whose avatar columns
    hold a bare stored filename that must be exposed as
    ``/api/<resource>/<id>/<field>``. A value that is already an absolute URL
    (``http``/``https``) or a root-relative path is passed through untouched (e.g.
    imported-card avatars or external URLs). Subclasses set ``avatar_resource`` to the
    API path segment and provide an ``id`` plus any of the three avatar fields.
    """

    avatar_resource: ClassVar[str] = ""

    if TYPE_CHECKING:
        # Provided by every concrete subclass; declared here only so the shared
        # serializer type-checks. Not a pydantic field (no runtime effect, so it
        # cannot reorder subclass fields / change the schema).
        id: str

    @field_serializer("avatar", "avatar_large", "avatar_thumbnail", check_fields=False)
    def _serialize_avatar(self, value: str | None, info: FieldSerializationInfo) -> str | None:
        if value and not value.startswith(("http://", "https://", "/")):
            return f"/api/{self.avatar_resource}/{self.id}/{info.field_name}"
        return value


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

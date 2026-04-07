"""Common schemas for pagination and responses"""

from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse[T](BaseModel):
    """
    Generic paginated response wrapper.

    Includes data, total count, and pagination metadata.
    """

    items: list[T] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items across all pages")
    limit: int = Field(..., description="Number of items per page")
    offset: int = Field(..., description="Number of items skipped")
    has_more: bool = Field(..., description="Whether there are more items available")

    @classmethod
    def create(cls, items: list[T], total: int, limit: int, offset: int) -> "PaginatedResponse[T]":
        """
        Factory method to create paginated response.

        Args:
            items: List of items for current page
            total: Total count of items
            limit: Items per page
            offset: Items skipped

        Returns:
            PaginatedResponse instance
        """
        return cls(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(items)) < total,
        )

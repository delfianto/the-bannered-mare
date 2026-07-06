"""Tests for core schemas"""

from src.core.schemas import PaginatedResponse, PaginationMeta


def test_paginated_response_cursor_based() -> None:
    """Test creating paginated response for cursor-based pagination"""
    items = ["a", "b", "c"]
    meta = PaginationMeta(
        limit=20, has_more=True, cursor="2023-10-27T10:00:00Z", total=None, page=None
    )

    response = PaginatedResponse(items=items, meta=meta)

    assert response.items == items
    assert response.meta.limit == 20
    assert response.meta.has_more is True
    assert response.meta.cursor == "2023-10-27T10:00:00Z"
    assert response.meta.total is None  # Not used in cursor-based
    assert response.meta.page is None  # Not used in cursor-based


def test_paginated_response_offset_based() -> None:
    """Test creating paginated response for offset-based pagination"""
    items = ["a", "b"]
    meta = PaginationMeta(limit=10, has_more=True, total=100, page=1, cursor=None)

    response = PaginatedResponse(items=items, meta=meta)

    assert response.items == items
    assert response.meta.limit == 10
    assert response.meta.has_more is True
    assert response.meta.total == 100
    assert response.meta.page == 1
    assert response.meta.cursor is None  # Not used in offset-based


def test_paginated_response_empty_cursor() -> None:
    """Test creating paginated response for empty results with cursor strategy"""
    items: list[str] = []
    meta = PaginationMeta(limit=20, has_more=False, cursor=None, total=None, page=None)

    response = PaginatedResponse(items=items, meta=meta)

    assert response.items == []
    assert response.meta.limit == 20
    assert response.meta.has_more is False
    assert response.meta.cursor is None


def test_paginated_response_empty_offset() -> None:
    """Test creating paginated response for empty results with offset strategy"""
    items: list[str] = []
    meta = PaginationMeta(limit=10, has_more=False, total=0, page=1, cursor=None)

    response = PaginatedResponse(items=items, meta=meta)

    assert response.items == []
    assert response.meta.limit == 10
    assert response.meta.has_more is False
    assert response.meta.total == 0
    assert response.meta.page == 1

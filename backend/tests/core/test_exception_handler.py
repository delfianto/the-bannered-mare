"""Tests for the global domain-exception handler registered in src.main."""

import json
from typing import Any

import pytest
from src.core.exceptions import (
    BanneredMareException,
    ConflictError,
    NotFoundError,
    ProviderException,
    ValidationError,
)
from src.main import _domain_exception_handler
from starlette.requests import Request


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (NotFoundError("nope"), 404),
        (ConflictError("dup"), 409),
        (ValidationError("bad"), 422),
        (BanneredMareException("generic"), 400),
        (ProviderException("upstream"), 502),
        (ProviderException("rate", status_code=429), 429),
    ],
)
async def test_domain_exception_maps_to_status_and_detail_shape(
    exc: BanneredMareException, expected_status: int
) -> None:
    resp = await _domain_exception_handler(_request(), exc)
    assert resp.status_code == expected_status
    # Body must keep FastAPI's {"detail": ...} shape (the frontend reads err.detail).
    body: dict[str, Any] = json.loads(bytes(resp.body))
    assert body == {"detail": exc.message}

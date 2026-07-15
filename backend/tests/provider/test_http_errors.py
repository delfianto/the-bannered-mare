"""Unit tests for pure HTTP-error → domain-exception mapping."""

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from src.core.exceptions import (
    ProviderAuthError,
    ProviderException,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
)
from src.provider.http_errors import map_http_error

_NO_JSON = object()


def _status_error(
    status_code: int, *, json_body: Any = _NO_JSON, text: str = ""
) -> httpx.HTTPStatusError:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.reason_phrase = "Error"
    if json_body is _NO_JSON:
        response.json.side_effect = ValueError("no json")
        response.text = text
    else:
        response.json.return_value = json_body
    return httpx.HTTPStatusError("err", request=MagicMock(), response=response)


def test_maps_401_to_auth_error() -> None:
    with pytest.raises(ProviderAuthError, match="Invalid API key"):
        map_http_error(_status_error(401, json_body={"error": {"message": "Invalid API key"}}))


def test_maps_429_to_rate_limit() -> None:
    """A string ``error`` body is used verbatim as the message."""
    with pytest.raises(ProviderRateLimitError, match="Rate limit exceeded"):
        map_http_error(_status_error(429, json_body={"error": "Rate limit exceeded"}))


def test_maps_400_to_invalid_request() -> None:
    with pytest.raises(ProviderInvalidRequestError, match="bad request"):
        map_http_error(_status_error(400, json_body={"error": {"message": "bad request"}}))


def test_maps_other_status_to_provider_exception() -> None:
    with pytest.raises(ProviderException):
        map_http_error(_status_error(503, json_body={}))


def test_falls_back_to_reason_phrase_when_body_not_json() -> None:
    """A non-JSON body doesn't blow up; the reason-phrase message is used."""
    with pytest.raises(ProviderException, match="Provider API error"):
        map_http_error(_status_error(500, text="upstream down"))

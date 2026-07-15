"""Map httpx transport errors to domain provider exceptions.

Extracted from ``ProviderGateway`` so the status → exception mapping is a pure
function, testable from a constructed ``HTTPStatusError`` with no HTTP round-trip.
"""

from typing import NoReturn

import httpx

from src.core.exceptions import (
    ProviderAuthError,
    ProviderException,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
)


def map_http_error(exc: httpx.HTTPStatusError) -> NoReturn:
    """Translate an HTTP status error into the matching ``Provider*`` exception."""
    status_code = exc.response.status_code
    try:
        error_detail = exc.response.json()
    except Exception:
        error_detail = exc.response.text

    message = f"Provider API error: {exc.response.reason_phrase}"
    if isinstance(error_detail, dict) and "error" in error_detail:
        err = error_detail["error"]
        if isinstance(err, dict) and "message" in err:
            message = err["message"]
        elif isinstance(err, str):
            message = err

    if status_code == 401:
        raise ProviderAuthError(message, status_code, error_detail) from exc
    elif status_code == 429:
        raise ProviderRateLimitError(message, status_code, error_detail) from exc
    elif status_code == 400:
        raise ProviderInvalidRequestError(message, status_code, error_detail) from exc
    else:
        raise ProviderException(message, status_code, error_detail) from exc

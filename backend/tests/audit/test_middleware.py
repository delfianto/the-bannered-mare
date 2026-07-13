"""Tests for the request-logging middleware (audit slice)"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response
from src.audit.middleware import RequestLoggingMiddleware


@pytest.mark.asyncio
async def test_middleware_logging() -> None:
    """Test that middleware logs and records an HTTP audit row"""
    app = MagicMock()
    middleware = RequestLoggingMiddleware(app)

    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    request.client.host = "127.0.0.1"
    request.headers = {}
    request.state = MagicMock()

    response = MagicMock(spec=Response)
    response.status_code = 200
    response.headers = {}

    call_next = AsyncMock(return_value=response)

    with (
        patch("src.audit.middleware.logger") as mock_logger,
        patch("src.audit.middleware.audit_logger") as mock_audit_logger,
    ):
        mock_audit_logger.log_http_request = AsyncMock()

        _ = await middleware.dispatch(request, call_next)

        assert mock_logger.info.call_count >= 2
        mock_audit_logger.log_http_request.assert_called_once()
        assert "X-Request-ID" in response.headers

"""Tests for request logging middleware"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response
from src.core.logging.request_logging import RequestLoggingMiddleware


@pytest.mark.asyncio
async def test_middleware_logging() -> None:
    """Test that middleware calls logger and mongo_logger"""
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
        patch("src.core.logging.request_logging.logger") as mock_logger,
        patch("src.core.logging.request_logging.mongo_logger") as mock_mongo_logger,
    ):
        mock_mongo_logger.log_http_request = AsyncMock()

        _ = await middleware.dispatch(request, call_next)

        assert mock_logger.info.call_count >= 2
        mock_mongo_logger.log_http_request.assert_called_once()
        assert "X-Request-ID" in response.headers

"""HTTP request/response logging middleware"""

import time
from collections.abc import Awaitable, Callable
from typing import override
from uuid import uuid4

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.logging.logger_config import get_logger
from src.core.logging.mongo_logger import mongo_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    @override
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and log details"""

        # Generate unique request ID
        request_id = str(uuid4())
        request.state.request_id = request_id

        # Bind request_id to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Start timer
        start_time = time.time()

        # Extract request info
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Log request start
        logger.info(
            "http_request_started",
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
        )

        # Process request
        try:
            response: Response = await call_next(request)
            status_code = response.status_code

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Log request completion
            logger.info(
                "http_request_completed",
                request_id=request_id,
                method=method,
                path=path,
                status_code=status_code,
                latency_ms=round(latency_ms, 2),
            )

            # Log to MongoDB (async, fire-and-forget)
            await mongo_logger.log_http_request(
                request_id=request_id,
                method=method,
                path=path,
                status_code=status_code,
                latency_ms=round(latency_ms, 2),
                client_ip=client_ip,
                user_agent=user_agent,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate latency even on error
            latency_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                "http_request_failed",
                request_id=request_id,
                method=method,
                path=path,
                error=str(e),
                latency_ms=round(latency_ms, 2),
            )

            # Log error to MongoDB
            await mongo_logger.log_error(
                error_type=type(e).__name__,
                message=str(e),
                context={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "client_ip": client_ip,
                },
            )

            # Re-raise to let FastAPI handle it
            raise

"""MongoDB logger for structured log storage"""

from datetime import UTC, datetime
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from src.core.config import settings
from src.core.logging.logger_config import get_logger, redact_sensitive_data

logger = get_logger(__name__)


class MongoLogger:
    """Async MongoDB logger for storing structured logs"""

    def __init__(self):
        self.client: AsyncMongoClient[dict[str, Any]] | None = None
        self.db: AsyncDatabase[dict[str, Any]] | None = None
        self.initialized = False

    async def initialize(self):
        """Initialize MongoDB connection and create collections with TTL indexes"""
        if not settings.logging.mongo_enabled:
            logger.info("mongodb_logging_disabled")
            return

        try:
            self.client = AsyncMongoClient(settings.logging.mongo_uri)
            self.db = self.client[settings.logging.mongo_database]

            # Test connection
            _ = await self.client.admin.command("ping")
            logger.info(
                "mongodb_connected",
                uri=settings.logging.mongo_uri,
                database=settings.logging.mongo_database,
            )

            # Mark as initialized even if index creation fails
            # Indexes are nice-to-have for TTL, but not required for basic logging
            self.initialized = True

            # Create collections with TTL indexes (best effort)
            await self._ensure_collections()

        except Exception as e:
            logger.error("mongodb_connection_failed", error=str(e))
            self.initialized = False

    async def _ensure_collections(self):
        """Create collections and TTL indexes if they don't exist"""
        if self.db is None:
            logger.error("mongodb_db_not_initialized")
            return

        collections = {
            "http_logs": settings.logging.http_logs_ttl,
            "llm_audit": settings.logging.llm_audit_ttl,
            "error_logs": settings.logging.error_logs_ttl,
        }

        for collection_name, ttl_seconds in collections.items():
            try:
                # Create TTL index on timestamp field
                _ = await self.db[collection_name].create_index(
                    "timestamp", expireAfterSeconds=ttl_seconds
                )
                logger.info(
                    "mongodb_collection_ensured",
                    collection=collection_name,
                    ttl_seconds=ttl_seconds,
                )
            except Exception as e:
                logger.warning(
                    "mongodb_index_creation_failed",
                    collection=collection_name,
                    error=str(e),
                    hint="Collections will still work, but TTL may not be enforced. Configure MongoDB authentication or disable auth for development.",
                )

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            await self.client.close()
            logger.info("mongodb_connection_closed")

    async def log_http_request(
        self,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        client_ip: str | None = None,
        user_agent: str | None = None,
        request_body: dict[str, Any] | None = None,
        response_body: dict[str, Any] | None = None,
    ):
        """Log HTTP request/response to MongoDB"""
        if not self.initialized or not settings.logging.log_http_requests or self.db is None:
            return

        document: dict[str, Any] = {
            "timestamp": datetime.now(UTC),
            "request_id": request_id,
            "method": method,
            "path": path,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "client_ip": client_ip,
            "user_agent": user_agent,
        }

        # Add request/response bodies if enabled
        if settings.logging.log_request_body and request_body:
            document["request_body"] = redact_sensitive_data(request_body)

        if settings.logging.log_response_body and response_body:
            document["response_body"] = redact_sensitive_data(response_body)

        try:
            _ = await self.db["http_logs"].insert_one(document)
        except Exception as e:
            logger.error("mongodb_insert_failed", collection="http_logs", error=str(e))

    async def log_llm_call(
        self,
        chat_id: str | None,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: float,
        status: str,
        estimated_cost_usd: float | None = None,
        error_message: str | None = None,
        request_messages: list[dict[str, Any]] | None = None,
        response_content: str | None = None,
    ):
        """Log LLM API call to MongoDB"""
        if not self.initialized or not settings.logging.log_llm_calls or self.db is None:
            return

        document: dict[str, Any] = {
            "timestamp": datetime.now(UTC),
            "chat_id": chat_id,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "latency_ms": latency_ms,
            "status": status,
            "estimated_cost_usd": estimated_cost_usd,
            "error_message": error_message,
        }

        # Optionally include request/response details
        if request_messages:
            document["request_messages"] = request_messages

        if response_content:
            # Truncate long responses
            document["response_content"] = (
                response_content[:1000] + "..."
                if len(response_content) > 1000
                else response_content
            )

        try:
            _ = await self.db["llm_audit"].insert_one(document)
        except Exception as e:
            logger.error("mongodb_insert_failed", collection="llm_audit", error=str(e))

    async def log_error(
        self,
        error_type: str,
        message: str,
        stack_trace: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        """Log application error to MongoDB"""
        if not self.initialized or self.db is None:
            return

        document: dict[str, Any] = {
            "timestamp": datetime.now(UTC),
            "error_type": error_type,
            "message": message,
            "stack_trace": stack_trace,
            "context": context or {},
        }

        try:
            _ = await self.db["error_logs"].insert_one(document)
        except Exception as e:
            logger.error("mongodb_insert_failed", collection="error_logs", error=str(e))


# Global MongoLogger instance
mongo_logger = MongoLogger()

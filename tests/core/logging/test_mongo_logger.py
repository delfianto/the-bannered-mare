"""Tests for MongoLogger"""

from unittest.mock import AsyncMock, patch

import pytest
from src.core.logging.mongo_logger import MongoLogger


@pytest.mark.asyncio
async def test_mongo_logger_initialization_disabled() -> None:
    """Test logger initialization when disabled"""
    with patch("src.core.logging.mongo_logger.settings") as mock_settings:
        mock_settings.logging.mongo_enabled = False

        logger = MongoLogger()
        await logger.initialize()

        assert logger.initialized is False


@pytest.mark.asyncio
async def test_mongo_logger_initialization_success() -> None:
    """Test logger initialization when enabled"""
    with (
        patch("src.core.logging.mongo_logger.settings") as mock_settings,
        patch("src.core.logging.mongo_logger.AsyncMongoClient") as mock_client_class,
    ):
        mock_settings.logging.mongo_enabled = True
        mock_settings.logging.mongo_uri = "mongodb://localhost:27017"
        mock_settings.logging.mongo_database = "test_db"

        mock_client = mock_client_class.return_value
        mock_client.admin.command = AsyncMock()

        logger = MongoLogger()
        # Mock _ensure_collections to avoid index creation in tests
        logger._ensure_collections = AsyncMock()  # pyright: ignore[reportPrivateUsage]

        await logger.initialize()

        assert logger.initialized is True
        mock_client_class.assert_called_once_with("mongodb://localhost:27017")

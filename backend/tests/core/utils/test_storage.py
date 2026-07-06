"""Tests for storage utility functions"""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from src.core.utils.storage import (
    delete_character_files,
    ensure_storage_directories,
    save_character_avatar,
)


@pytest.fixture
def mock_settings(tmp_path: Any) -> Any:
    """Mock settings to use a temporary storage path"""
    with patch("src.core.utils.storage.settings") as mock:
        mock.storage_path = str(tmp_path)
        yield mock


def test_ensure_storage_directories(mock_settings: Any) -> None:
    """Test storage directory creation"""
    ensure_storage_directories()

    assert os.path.exists(os.path.join(mock_settings.storage_path, "characters"))
    assert os.path.exists(os.path.join(mock_settings.storage_path, "personas"))
    assert os.path.exists(os.path.join(mock_settings.storage_path, "temp"))


@pytest.mark.asyncio
async def test_save_character_avatar(mock_settings: Any) -> None:
    """Test saving character avatar (minimal mock)"""
    # Create a simple mock for UploadFile
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.png"
    mock_file.read.return_value = b"dummy image content"
    mock_file.seek = AsyncMock()  # validate_avatar calls seek

    # Mock validate_avatar to skip real validation
    with (
        patch("src.core.utils.storage.validate_avatar", new_callable=AsyncMock),
        patch("src.core.utils.storage.Image.open") as mock_image_open,
    ):
        mock_img = MagicMock()
        mock_img.width = 100
        mock_img.height = 100
        mock_img.mode = "RGB"
        # Setup context manager correctly
        mock_image_open.return_value.__enter__.return_value = mock_img

        orig_path, thumb_path = await save_character_avatar("char123", mock_file)

        assert "characters/char123/avatar_original.png" in orig_path
        assert "characters/char123/avatar_thumbnail.jpg" in thumb_path  # We save thumbnails as jpg

        # Verify directories were created
        assert os.path.exists(os.path.join(mock_settings.storage_path, "characters", "char123"))


def test_delete_character_files(mock_settings: Any) -> None:
    """Test character file deletion"""
    char_id = "char123"
    char_dir = os.path.join(mock_settings.storage_path, "characters", char_id)
    os.makedirs(char_dir, exist_ok=True)

    delete_character_files(char_id)

    assert not os.path.exists(char_dir)

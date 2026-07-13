"""Tests for storage utility functions"""

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from src.core.utils.storage import (
    delete_character_files,
    ensure_storage_directories,
    save_character_avatar,
)
from src.core.utils.upload import UploadedFile


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
    avatar = UploadedFile(b"dummy image content", "test.png")

    # Mock validate_avatar (sync) to skip real validation
    with (
        patch("src.core.utils.storage.validate_avatar"),
        patch("src.core.utils.storage.Image.open") as mock_image_open,
    ):
        mock_img = MagicMock()
        mock_img.width = 100
        mock_img.height = 100
        mock_img.mode = "RGB"
        mock_img.size = (100, 100)
        # Image ops return the same mock so the derivation pipeline is a no-op
        mock_img.convert.return_value = mock_img
        mock_img.copy.return_value = mock_img
        mock_img.crop.return_value = mock_img
        mock_img.resize.return_value = mock_img
        # Setup context manager correctly
        mock_image_open.return_value.__enter__.return_value = mock_img

        orig_path, large_path, thumb_path = await save_character_avatar("char123", avatar)

        assert "characters/char123/avatar_original.png" in orig_path
        assert "characters/char123/avatar_large.jpg" in large_path  # <=512px full portrait
        assert "characters/char123/avatar_thumbnail.jpg" in thumb_path  # 256px head crop (jpg)

        # Verify directories were created
        assert os.path.exists(os.path.join(mock_settings.storage_path, "characters", "char123"))


def test_delete_character_files(mock_settings: Any) -> None:
    """Test character file deletion"""
    char_id = "char123"
    char_dir = os.path.join(mock_settings.storage_path, "characters", char_id)
    os.makedirs(char_dir, exist_ok=True)

    delete_character_files(char_id)

    assert not os.path.exists(char_dir)

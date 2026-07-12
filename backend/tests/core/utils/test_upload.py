"""Tests for the bounded upload-read helper."""

import io

import pytest
from fastapi import HTTPException, UploadFile
from src.core.utils.upload import read_upload_capped


@pytest.mark.asyncio
async def test_accepts_within_limit() -> None:
    file = UploadFile(filename="card.json", file=io.BytesIO(b"hello world"))
    data = await read_upload_capped(file, max_bytes=1024)
    assert data == b"hello world"


@pytest.mark.asyncio
async def test_rejects_oversize_before_full_read() -> None:
    file = UploadFile(filename="huge.png", file=io.BytesIO(b"x" * 5000))
    with pytest.raises(HTTPException) as exc_info:
        await read_upload_capped(file, max_bytes=1024)
    assert exc_info.value.status_code == 413

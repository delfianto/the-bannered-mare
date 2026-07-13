"""Shared helpers for bounded file uploads."""

from typing import NamedTuple

from fastapi import UploadFile

from src.core.exceptions import PayloadTooLargeError

# Character cards (PNG with embedded JSON) and ST presets are read fully into
# memory before parsing, so cap them to avoid a trivial memory-exhaustion DoS.
# Mirrors MAX_AVATAR_SIZE in storage.py.
MAX_IMPORT_SIZE = 20 * 1024 * 1024  # 20 MB


class UploadedFile(NamedTuple):
    """A read, transport-agnostic upload: raw bytes + original filename.

    Lets the service and storage layers stay free of FastAPI's ``UploadFile`` —
    the router reads the multipart file (bounded) and hands down one of these.
    """

    data: bytes
    filename: str


async def read_upload_capped(file: UploadFile, max_bytes: int = MAX_IMPORT_SIZE) -> bytes:
    """Read an upload fully, rejecting anything over ``max_bytes``.

    Reads ``max_bytes + 1`` so an oversize file is detected without loading the
    whole payload into memory.
    """
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise PayloadTooLargeError(f"File too large. Max size: {max_bytes // (1024 * 1024)}MB")
    return data


async def read_upload(file: UploadFile, max_bytes: int = MAX_IMPORT_SIZE) -> UploadedFile:
    """Read a capped upload into an ``UploadedFile`` (bytes + original filename)."""
    return UploadedFile(await read_upload_capped(file, max_bytes), file.filename or "")

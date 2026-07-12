"""Shared helpers for bounded file uploads."""

from fastapi import HTTPException, UploadFile, status

# Character cards (PNG with embedded JSON) and ST presets are read fully into
# memory before parsing, so cap them to avoid a trivial memory-exhaustion DoS.
# Mirrors MAX_AVATAR_SIZE in storage.py.
MAX_IMPORT_SIZE = 20 * 1024 * 1024  # 20 MB


async def read_upload_capped(file: UploadFile, max_bytes: int = MAX_IMPORT_SIZE) -> bytes:
    """Read an upload fully, rejecting anything over ``max_bytes``.

    Reads ``max_bytes + 1`` so an oversize file is detected without loading the
    whole payload into memory.
    """
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large. Max size: {max_bytes // (1024 * 1024)}MB",
        )
    return data

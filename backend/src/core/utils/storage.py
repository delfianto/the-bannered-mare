"""File storage service for handling character avatars and assets"""

import io
import os
import shutil

import aiofiles
from anyio import to_thread
from fastapi import HTTPException, UploadFile, status
from PIL import Image

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Derived avatar tiers generated from every upload:
#   - large: bounded full portrait for the detail preview, home banner, grid.
#   - head:  square crop of the head, shown as a circle for chat / small avatars.
LARGE_SIZE = (512, 512)  # bounding box (aspect preserved, never upscaled)
HEAD_SIZE = (256, 256)  # final square size of the head crop

LARGE_FILENAME = "avatar_large.jpg"
# Head crop keeps the historical filename so the existing column/endpoint still
# points at it — the tier's meaning changed (128px full -> 256px head crop), the
# path did not.
HEAD_FILENAME = "avatar_thumbnail.jpg"

MAX_AVATAR_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_DIMENSIONS = (4096, 4096)


async def validate_avatar(file: UploadFile) -> None:
    """
    Validate uploaded avatar file.

    Checks:
    - Extension
    - File size
    - Image format/integrity
    - Dimensions
    """
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # We read first 5MB + 1 byte to check if it exceeds limit without loading everything
    content = await file.read(MAX_AVATAR_SIZE + 1)
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {MAX_AVATAR_SIZE // (1024 * 1024)}MB",
        )

    # Reset file pointer for subsequent reads
    await file.seek(0)

    try:
        # Load small part of the image to check header
        img = Image.open(io.BytesIO(content))
        img.verify()  # Verifies integrity

        # Need to reopen because verify() closes the file pointer in some versions
        img = Image.open(io.BytesIO(content))
        if img.width > MAX_DIMENSIONS[0] or img.height > MAX_DIMENSIONS[1]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image dimensions too large. Max: {MAX_DIMENSIONS[0]}x{MAX_DIMENSIONS[1]}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {str(e)}",
        ) from e
    finally:
        await file.seek(0)


def _crop_head_square(img: Image.Image) -> Image.Image:
    """
    Crop a square focused on the head.

    Heads sit in the upper portion of a portrait, so we take the largest square
    that fits, centre it horizontally, and anchor it near the top — nudged down
    ~8% of the surplus height so the crown of the head isn't clipped. This is a
    deliberately dependency-free heuristic: face detection is unreliable on the
    stylised (anime) card art this app commonly imports.
    """
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = int((h - side) * 0.08) if h > side else 0
    return img.crop((left, top, left + side, top + side))


def _find_original(entity_dir: str) -> str | None:
    """Return the stored original avatar path (any extension), if present."""
    if not os.path.isdir(entity_dir):
        return None
    for name in os.listdir(entity_dir):
        if name.startswith("avatar_original"):
            return os.path.join(entity_dir, name)
    return None


def generate_avatar_derivatives(entity_type: str, entity_id: str) -> tuple[str, str]:
    """
    (Re)generate the large + head-crop tiers from the stored original.

    Reads ``avatar_original.*`` under the entity's storage dir and writes
    ``avatar_large.jpg`` and ``avatar_thumbnail.jpg`` beside it. Returns their
    storage-relative paths, or ``("", "")`` if the original is missing or
    processing fails. Safe to call for a one-off backfill of existing avatars.
    """
    entity_dir = os.path.join(settings.storage_path, entity_type, entity_id)
    original_full = _find_original(entity_dir)
    if not original_full or not os.path.exists(original_full):
        return "", ""

    large_full = os.path.join(entity_dir, LARGE_FILENAME)
    head_full = os.path.join(entity_dir, HEAD_FILENAME)

    with Image.open(original_full) as src:
        # JPEG has no alpha; flatten anything with transparency/palette to RGB.
        rgb = src.convert("RGB") if src.mode != "RGB" else src

        large = rgb.copy()
        large.thumbnail(LARGE_SIZE)  # aspect preserved, never upscales
        large.save(large_full, "JPEG", quality=88, optimize=True)

        head = _crop_head_square(rgb)
        if head.size != HEAD_SIZE:
            head = head.resize(HEAD_SIZE, Image.Resampling.LANCZOS)
        head.save(head_full, "JPEG", quality=85, optimize=True)

    large_rel = f"{entity_type}/{entity_id}/{LARGE_FILENAME}"
    head_rel = f"{entity_type}/{entity_id}/{HEAD_FILENAME}"
    return large_rel, head_rel


async def _save_avatar(entity_type: str, entity_id: str, file: UploadFile) -> tuple[str, str, str]:
    """
    Save an avatar and generate its derived sizes.

    Returns ``(original_path, large_path, head_path)`` as storage-relative paths;
    the derived paths are empty strings if generation failed (the original is
    still saved so a later backfill can retry).
    """
    # Validate before saving
    await validate_avatar(file)

    entity_dir = os.path.join(settings.storage_path, entity_type, entity_id)
    os.makedirs(entity_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    if file_ext.lower() not in ALLOWED_EXTENSIONS:
        file_ext = ".png"

    original_filename = f"avatar_original{file_ext}"
    original_full_path = os.path.join(entity_dir, original_filename)

    # Save original image as-is (validated, EXIF kept) — it backs export/download
    # and every derived size is regenerated from it.
    file_content = await file.read()
    async with aiofiles.open(original_full_path, "wb") as f:
        _ = await f.write(file_content)

    original_relative_path = f"{entity_type}/{entity_id}/{original_filename}"

    try:
        # PIL decode/resize/encode is CPU-bound — run it off the event loop.
        large_relative_path, head_relative_path = await to_thread.run_sync(
            generate_avatar_derivatives, entity_type, entity_id
        )
    except Exception:
        logger.warning(
            "avatar_derivative_failed",
            entity_type=entity_type,
            entity_id=entity_id,
            exc_info=True,
        )
        large_relative_path, head_relative_path = "", ""

    return original_relative_path, large_relative_path, head_relative_path


async def save_character_avatar(character_id: str, file: UploadFile) -> tuple[str, str, str]:
    """
    Save character avatar to storage and generate its derived sizes.

    Returns ``(original_path, large_path, head_path)``.
    """
    return await _save_avatar("characters", character_id, file)


async def save_persona_avatar(persona_id: str, file: UploadFile) -> tuple[str, str, str]:
    """
    Save persona avatar to storage and generate its derived sizes.

    Returns ``(original_path, large_path, head_path)``.
    """
    return await _save_avatar("personas", persona_id, file)


def _delete_entity_files(entity_type: str, entity_id: str) -> None:
    """
    Generic function to delete all files associated with an entity.

    Args:
        entity_type: "characters" or "personas"
        entity_id: The ID of the character or persona
    """
    entity_dir = os.path.join(settings.storage_path, entity_type, entity_id)

    if os.path.exists(entity_dir):
        shutil.rmtree(entity_dir)


def delete_character_files(character_id: str) -> None:
    """
    Delete all files associated with a character.
    """
    _delete_entity_files("characters", character_id)


def delete_persona_files(persona_id: str) -> None:
    """
    Delete all files associated with a persona.
    """
    _delete_entity_files("personas", persona_id)


def ensure_storage_directories() -> None:
    """
    Ensure all required storage directories exist.
    Called on application startup.
    """
    directories = [
        os.path.join(settings.storage_path, "characters"),
        os.path.join(settings.storage_path, "personas"),
        os.path.join(settings.storage_path, "temp"),
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

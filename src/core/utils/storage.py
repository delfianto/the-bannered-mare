"""File storage service for handling character avatars and assets"""

import io
import os
import shutil

import aiofiles
from fastapi import HTTPException, UploadFile, status
from PIL import Image

from src.core.config import settings

THUMBNAIL_SIZE = (128, 128)
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_DIMENSIONS = (2048, 2048)


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


async def _save_avatar(entity_type: str, entity_id: str, file: UploadFile) -> tuple[str, str]:
    """
    Generic function to save an avatar and generate a thumbnail.
    """
    # Validate before saving
    await validate_avatar(file)

    entity_dir = os.path.join(settings.storage_path, entity_type, entity_id)
    os.makedirs(entity_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    if file_ext.lower() not in ALLOWED_EXTENSIONS:
        file_ext = ".png"

    original_avatar_filename = f"avatar_original{file_ext}"
    thumbnail_avatar_filename = f"avatar_thumbnail{file_ext}"

    original_avatar_full_path = os.path.join(entity_dir, original_avatar_filename)
    thumbnail_avatar_full_path = os.path.join(entity_dir, thumbnail_avatar_filename)

    # Save original image (without EXIF stripping - we keep original as is but validated)
    file_content = await file.read()
    async with aiofiles.open(original_avatar_full_path, "wb") as f:
        _ = await f.write(file_content)

    # Generate and save thumbnail (always strips EXIF by default when resizing/saving)
    try:
        with Image.open(original_avatar_full_path) as img:
            # Convert to RGB if necessary (e.g. for PNG with transparency being saved as JPEG)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.thumbnail(THUMBNAIL_SIZE)
            # Saving as JPEG for thumbnail efficiency
            thumbnail_path_jpg = thumbnail_avatar_full_path.rsplit(".", 1)[0] + ".jpg"
            img.save(thumbnail_path_jpg, "JPEG", quality=85, optimize=True)

            thumbnail_relative_path = (
                f"{entity_type}/{entity_id}/{os.path.basename(thumbnail_path_jpg)}"
            )
    except Exception as e:
        print(f"Error generating thumbnail for {entity_type} {entity_id}: {e}")
        return "", ""

    original_relative_path = f"{entity_type}/{entity_id}/{original_avatar_filename}"

    return original_relative_path, thumbnail_relative_path


async def save_character_avatar(character_id: str, file: UploadFile) -> tuple[str, str]:
    """
    Save character avatar to storage and generate a thumbnail.
    """
    return await _save_avatar("characters", character_id, file)


async def save_persona_avatar(persona_id: str, file: UploadFile) -> tuple[str, str]:
    """
    Save persona avatar to storage and generate a thumbnail.
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

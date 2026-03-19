"""
Photo Storage Service — Supabase Storage integration.

Handles upload/download/URL generation for production photos:
- Packing photos: photos/{factory_id}/packing/{order_id}/{filename}
- Batch photos: photos/{factory_id}/batches/{batch_id}/{filename}
- Telegram photos: photos/{factory_id}/telegram/{date}/{filename}
- Quality photos: photos/{factory_id}/quality/{position_id}/{filename}

Falls back to local filesystem if SUPABASE_URL is not configured.
"""

import os
import hashlib
import logging
from pathlib import Path
from uuid import UUID, uuid4
from datetime import date, datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("moonjar.photo_storage")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET_NAME = "moonjar-photos"

# Local fallback directory (relative to project root)
LOCAL_UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "uploads"))

# Valid categories for photo organization
VALID_CATEGORIES = {"packing", "batch", "telegram", "quality"}


def _generate_filename(image_bytes: bytes, original_filename: Optional[str] = None) -> str:
    """Generate a unique filename using content hash + uuid suffix."""
    content_hash = hashlib.md5(image_bytes[:4096]).hexdigest()[:8]
    unique_id = uuid4().hex[:8]

    if original_filename:
        # Preserve extension from original filename
        ext = Path(original_filename).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".heic"):
            ext = ".jpg"
    else:
        ext = ".jpg"

    return f"{content_hash}_{unique_id}{ext}"


def _build_storage_path(
    category: str,
    factory_id: UUID,
    related_id: UUID | str,
    filename: str,
) -> str:
    """Build the hierarchical storage path for a photo."""
    if category == "telegram":
        # Telegram photos use date-based subfolder
        today = date.today().isoformat()
        return f"photos/{factory_id}/telegram/{today}/{filename}"
    return f"photos/{factory_id}/{category}/{related_id}/{filename}"


def _detect_content_type(filename: str) -> str:
    """Detect content type from filename extension."""
    ext = Path(filename).suffix.lower()
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".heic": "image/heic",
    }
    return mapping.get(ext, "image/jpeg")


async def upload_photo(
    image_bytes: bytes,
    category: str,
    factory_id: UUID,
    related_id: UUID | str,
    filename: Optional[str] = None,
) -> dict:
    """
    Upload photo to Supabase Storage (or local fallback).

    Args:
        image_bytes: Raw image bytes
        category: "packing" | "batch" | "telegram" | "quality"
        factory_id: Factory UUID for path organization
        related_id: Order ID, batch ID, position ID, or date string
        filename: Optional original filename (auto-generated if None)

    Returns:
        {"url": "https://...", "path": "photos/...", "storage": "supabase"|"local"}

    Raises:
        ValueError: If category is invalid or image_bytes is empty
    """
    if not image_bytes:
        raise ValueError("image_bytes cannot be empty")

    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {VALID_CATEGORIES}")

    # Generate filename if not provided
    if not filename:
        filename = _generate_filename(image_bytes)

    if SUPABASE_URL and SUPABASE_KEY:
        return await _upload_to_supabase(image_bytes, category, factory_id, related_id, filename)
    else:
        return _save_locally(image_bytes, category, factory_id, related_id, filename)


async def _upload_to_supabase(
    image_bytes: bytes,
    category: str,
    factory_id: UUID,
    related_id: UUID | str,
    filename: str,
) -> dict:
    """Upload to Supabase Storage via REST API."""
    path = _build_storage_path(category, factory_id, related_id, filename)
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{path}"
    content_type = _detect_content_type(filename)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                content=image_bytes,
                headers={
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": content_type,
                    "x-upsert": "true",  # Overwrite if exists
                },
            )
            if response.status_code in (200, 201):
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{path}"
                logger.info(f"Photo uploaded to Supabase: {path}")
                return {"url": public_url, "path": path, "storage": "supabase"}
            else:
                logger.error(
                    f"Supabase upload failed: {response.status_code} {response.text} — "
                    f"falling back to local storage"
                )
                return _save_locally(image_bytes, category, factory_id, related_id, filename)
    except Exception as e:
        logger.error(f"Supabase upload error: {e} — falling back to local storage")
        return _save_locally(image_bytes, category, factory_id, related_id, filename)


def _save_locally(
    image_bytes: bytes,
    category: str,
    factory_id: UUID,
    related_id: UUID | str,
    filename: str,
) -> dict:
    """Fallback: save to local uploads/ directory."""
    # Build local directory path mirroring Supabase structure
    if category == "telegram":
        today = date.today().isoformat()
        local_dir = LOCAL_UPLOADS_DIR / str(factory_id) / "telegram" / today
    else:
        local_dir = LOCAL_UPLOADS_DIR / str(factory_id) / category / str(related_id)

    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / filename

    local_path.write_bytes(image_bytes)

    # Build a relative path for storage reference
    rel_path = str(local_path.relative_to(LOCAL_UPLOADS_DIR))
    # Build a local URL that can be served by the API
    local_url = f"/api/uploads/{rel_path}"

    logger.info(f"Photo saved locally: {local_path}")
    return {"url": local_url, "path": rel_path, "storage": "local"}


def _validate_path(path: str) -> Path:
    """
    Validate that a path stays within LOCAL_UPLOADS_DIR.
    Prevents path traversal attacks (e.g., ../../etc/passwd).
    """
    resolved = (LOCAL_UPLOADS_DIR / path).resolve()
    if not str(resolved).startswith(str(LOCAL_UPLOADS_DIR.resolve())):
        raise ValueError(f"Path traversal detected: {path}")
    return resolved


def get_public_url(path: str) -> str:
    """
    Get public URL for a stored photo.

    Args:
        path: The storage path (as returned by upload_photo)

    Returns:
        Full public URL for the photo
    """
    _validate_path(path)  # Prevent path traversal
    if SUPABASE_URL:
        return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{path}"
    else:
        return f"/api/uploads/{path}"


async def delete_photo(path: str) -> bool:
    """
    Delete a photo from storage.

    Args:
        path: The storage path (as returned by upload_photo)

    Returns:
        True if deletion succeeded, False otherwise
    """
    if SUPABASE_URL and SUPABASE_KEY:
        return await _delete_from_supabase(path)
    else:
        return _delete_locally(path)


async def _delete_from_supabase(path: str) -> bool:
    """Delete a file from Supabase Storage."""
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{path}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.delete(
                url,
                headers={"Authorization": f"Bearer {SUPABASE_KEY}"},
            )
            if response.status_code in (200, 204):
                logger.info(f"Photo deleted from Supabase: {path}")
                return True
            else:
                logger.error(f"Supabase delete failed: {response.status_code} {response.text}")
                return False
    except Exception as e:
        logger.error(f"Supabase delete error: {e}")
        return False


def _delete_locally(path: str) -> bool:
    """Delete a file from local storage."""
    local_path = _validate_path(path)  # Prevent path traversal

    try:
        if local_path.exists():
            local_path.unlink()
            logger.info(f"Photo deleted locally: {local_path}")
            return True
        else:
            logger.warning(f"Local file not found for deletion: {local_path}")
            return False
    except Exception as e:
        logger.error(f"Local delete error: {e}")
        return False

"""Local-disk file storage for applicant documents and proctoring snapshots.

Files are written under Settings.UPLOAD_DIR and served back by main.py's
StaticFiles mount at /uploads/*. Swap this module for an S3/GCS-backed
version later without touching callers — they only depend on save_upload()
returning a relative path and file_url() turning that into a servable URL.
"""
import mimetypes
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from core.settings import Settings

# Keep this list conservative — these are the only file types the exam flow
# ever needs to accept (marksheets/age-proof as image or PDF, snapshots as
# image only).
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}
_MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB


def _ensure_dir(subdir: str) -> Path:
    target = Path(Settings.UPLOAD_DIR) / subdir
    target.mkdir(parents=True, exist_ok=True)
    return target


async def save_upload(upload: UploadFile, *, subdir: str) -> tuple[str, str, str]:
    """Validates and persists an UploadFile under UPLOAD_DIR/subdir.

    Returns (relative_path, original_filename, content_type). relative_path
    is what gets stored in the DB; pass it to file_url() to render a link.
    """
    content_type = upload.content_type or mimetypes.guess_type(upload.filename or "")[0] or ""
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only JPEG/PNG/WEBP images or PDF files are accepted",
        )

    data = await upload.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is larger than 8 MB")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")

    ext = mimetypes.guess_extension(content_type) or os.path.splitext(upload.filename or "")[1] or ""
    filename = f"{uuid.uuid4().hex}{ext}"
    target_dir = _ensure_dir(subdir)
    target_path = target_dir / filename
    target_path.write_bytes(data)

    relative_path = f"{subdir}/{filename}"
    return relative_path, (upload.filename or filename), content_type


def save_bytes(data: bytes, *, subdir: str, content_type: str) -> str:
    """Same as save_upload but for raw bytes (used by the proctoring
    snapshot endpoint, which receives a base64 data URL, not multipart)."""
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only JPEG/PNG/WEBP snapshots are accepted")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Snapshot is larger than 8 MB")

    ext = mimetypes.guess_extension(content_type) or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    target_dir = _ensure_dir(subdir)
    (target_dir / filename).write_bytes(data)
    return f"{subdir}/{filename}"


def file_url(relative_path: str) -> str:
    return f"{Settings.BACKEND_PUBLIC_URL.rstrip('/')}/uploads/{relative_path}"

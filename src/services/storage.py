"""Supabase Storage backend for note attachments.

Talks to the Storage REST API directly with ``requests`` -- no heavyweight SDK
needed. Credentials come from ``.env`` at the repository root:

    SUPABASE_URL=https://<project-ref>.supabase.co
    SUPABASE_SERVICE_KEY=sb_secret_...
    SUPABASE_BUCKET=note-attachments
    MAX_UPLOAD_MB=4

The bucket is public, so every uploaded object gets a stable URL the browser
can load straight from an <img> tag or a download link.
"""

import mimetypes
import os
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "note-attachments")

# Keep this under Vercel's ~4.5 MB serverless request-body limit, so an upload
# that works locally also works once deployed.
MAX_UPLOAD_MB = float(os.getenv("MAX_UPLOAD_MB", "4"))
MAX_UPLOAD_BYTES = int(MAX_UPLOAD_MB * 1024 * 1024)

REQUEST_TIMEOUT = 60

# mimetype -> canonical extension. Anything not listed here is rejected.
ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/zip": ".zip",
}

# Set once the bucket has been confirmed to exist, so we don't hit the API on
# every single upload (and on every serverless cold start).
_bucket_ready = False


class StorageError(Exception):
    """Raised when an upload or delete cannot be completed."""


def is_configured() -> bool:
    """True when the storage credentials are present."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def _headers(extra=None):
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
    }
    if extra:
        headers.update(extra)
    return headers


def _require_config():
    if not is_configured():
        raise StorageError(
            "Supabase Storage is not configured. Set SUPABASE_URL and "
            "SUPABASE_SERVICE_KEY in .env (see .env.example)."
        )


def ensure_bucket() -> None:
    """Create the bucket if it does not exist yet. Idempotent."""
    global _bucket_ready
    if _bucket_ready:
        return
    _require_config()

    try:
        response = requests.post(
            f"{SUPABASE_URL}/storage/v1/bucket",
            headers=_headers({"Content-Type": "application/json"}),
            json={"id": SUPABASE_BUCKET, "name": SUPABASE_BUCKET, "public": True},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise StorageError(f"Could not reach Supabase Storage: {exc}") from exc

    # 400/409 -> already exists, which is exactly what we want.
    if response.status_code not in (200, 201, 400, 409):
        raise StorageError(
            f"Could not create bucket {SUPABASE_BUCKET!r}: "
            f"{response.status_code} {response.text[:200]}"
        )

    _bucket_ready = True


def resolve_content_type(filename: str, provided: str | None) -> str:
    """Work out the file's MIME type, falling back to the extension.

    Browsers send ``application/octet-stream`` for unknown types, so the
    extension is consulted when the provided value is not recognised.
    """
    if provided and provided in ALLOWED_TYPES:
        return provided

    guessed, _ = mimetypes.guess_type(filename)
    if guessed in ALLOWED_TYPES:
        return guessed

    raise StorageError(
        "Unsupported file type. Allowed: images, PDF, text, "
        "Office documents and zip archives."
    )


def public_url(storage_path: str) -> str:
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{storage_path}"


def upload(data: bytes, filename: str, content_type: str | None, note_id: int) -> dict:
    """Store ``data`` and return ``{'storage_path': ..., 'url': ...}``.

    Objects are laid out per note: ``notes/<note_id>/<uuid><ext>``.
    """
    _require_config()

    if not data:
        raise StorageError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise StorageError(
            f"File is too large. Maximum size is {MAX_UPLOAD_MB:g} MB."
        )

    mime = resolve_content_type(filename, content_type)
    extension = ALLOWED_TYPES[mime]
    storage_path = f"notes/{note_id}/{uuid.uuid4().hex}{extension}"

    ensure_bucket()

    try:
        response = requests.post(
            f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{storage_path}",
            headers=_headers({
                "Content-Type": mime,
                "x-upsert": "true",
                # Store the original name so the file downloads with a sane name.
                "cache-control": "3600",
            }),
            data=data,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise StorageError(f"Upload failed: {exc}") from exc

    if response.status_code not in (200, 201):
        raise StorageError(
            f"Upload rejected by Supabase: {response.status_code} "
            f"{response.text[:200]}"
        )

    return {"storage_path": storage_path, "url": public_url(storage_path)}


def delete(storage_path: str) -> None:
    """Remove an object from the bucket. Missing objects are not an error."""
    _require_config()

    try:
        response = requests.delete(
            f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{storage_path}",
            headers=_headers(),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise StorageError(f"Delete failed: {exc}") from exc

    if response.status_code not in (200, 204, 404):
        raise StorageError(
            f"Delete rejected by Supabase: {response.status_code} "
            f"{response.text[:200]}"
        )

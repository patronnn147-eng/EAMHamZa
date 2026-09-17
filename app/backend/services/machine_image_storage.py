"""
Machine photo storage on MinIO/S3 (bucket: attachments — already public-read,
see docker-compose.yml minio_init). Mirrors services.rag_storage's pattern.
"""

import io
import logging
import mimetypes
import os
import uuid
from typing import Optional, Union
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

BUCKET = os.getenv("ATTACHMENTS_BUCKET", "attachments")
PREFIX = "machines"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BYTES = 8 * 1024 * 1024


def _get_minio_client() -> Optional[Minio]:
    url = os.getenv("OSS_SERVICE_URL", "") or "http://minio:9000"
    access_key = os.getenv("OSS_API_KEY", "") or os.getenv("MINIO_ROOT_USER", "")
    secret_key = os.getenv("OSS_SECRET_KEY", "") or os.getenv("MINIO_ROOT_PASSWORD", "")

    if not (access_key and secret_key):
        logger.warning("[machine_image_storage] MinIO credentials missing.")
        return None

    try:
        parsed = urlparse(url)
        endpoint = parsed.netloc or parsed.path
        secure = parsed.scheme == "https"
        return Minio(
            endpoint, access_key=access_key, secret_key=secret_key,
            secure=secure, region="us-east-1",
        )
    except Exception:
        logger.exception("[machine_image_storage] Failed to build MinIO client")
        return None


def _ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(BUCKET):
        client.make_bucket(BUCKET)


def build_object_key(machine_id: Union[int, str], filename: str) -> str:
    safe_name = os.path.basename(filename).replace("/", "_").replace("\\", "_")
    return f"{PREFIX}/{machine_id}/{uuid.uuid4().hex}_{safe_name}"


def upload_machine_image(
    machine_id: Union[int, str], filename: str, file_bytes: bytes, content_type: Optional[str] = None
) -> str:
    """Upload bytes to the attachments bucket. Returns the public object key."""
    client = _get_minio_client()
    if not client:
        raise RuntimeError("MinIO/S3 not configured — cannot store machine image.")

    if len(file_bytes) > MAX_BYTES:
        raise ValueError(f"Image exceeds {MAX_BYTES // (1024 * 1024)}MB limit.")

    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Unsupported image type: {content_type}")

    _ensure_bucket(client)
    object_key = build_object_key(machine_id, filename)

    try:
        client.put_object(
            bucket_name=BUCKET,
            object_name=object_key,
            data=io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type,
        )
        logger.info(f"[machine_image_storage] Uploaded {object_key} ({len(file_bytes)} bytes)")
        return object_key
    except S3Error:
        logger.exception(f"[machine_image_storage] Upload failed for {object_key}")
        raise


def public_url(object_key: str) -> str:
    """Public URL for a machine image (bucket has anonymous download enabled)."""
    base = os.getenv("OSS_PUBLIC_URL", "") or "http://localhost:9000"
    return f"{base.rstrip('/')}/{BUCKET}/{object_key}"


def delete_by_url(url: Optional[str]) -> bool:
    """Best-effort delete of a previously uploaded machine image, given its public URL."""
    if not url or f"/{BUCKET}/{PREFIX}/" not in url:
        return False  # not one of ours (external URL) — leave it alone

    client = _get_minio_client()
    if not client:
        return False

    object_key = url.split(f"/{BUCKET}/", 1)[1]
    try:
        client.remove_object(BUCKET, object_key)
        return True
    except S3Error:
        logger.warning(f"[machine_image_storage] Delete failed for {object_key}")
        return False

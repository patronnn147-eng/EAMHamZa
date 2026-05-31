"""
RAG document storage on MinIO/S3 (bucket: rag-docs).

Server-side upload/download/delete + presigned URL generation for the
admin UI. Falls back gracefully if MinIO is not configured.
"""
import io
import logging
import mimetypes
import os
import uuid
from datetime import timedelta, datetime, timezone
from typing import Optional, Tuple
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

RAG_BUCKET = os.getenv("RAG_BUCKET", "rag-docs")


def _get_minio_client() -> Optional[Minio]:
    """Build a MinIO client from env vars (same vars as services.storage)."""
    url        = os.getenv("OSS_SERVICE_URL", "")
    access_key = os.getenv("OSS_API_KEY", "")
    secret_key = os.getenv("OSS_SECRET_KEY", "")

    if not (url and access_key and secret_key):
        # Fall back to MINIO_ROOT_* (typical compose setup)
        url        = url        or "http://minio:9000"
        access_key = access_key or os.getenv("MINIO_ROOT_USER", "")
        secret_key = secret_key or os.getenv("MINIO_ROOT_PASSWORD", "")

    if not (access_key and secret_key):
        logger.warning("[rag_storage] MinIO credentials missing — RAG S3 storage disabled.")
        return None

    try:
        parsed = urlparse(url)
        endpoint = parsed.netloc or parsed.path
        secure   = parsed.scheme == "https"
        return Minio(endpoint, access_key=access_key, secret_key=secret_key,
                     secure=secure, region="us-east-1")
    except Exception as e:
        logger.error(f"[rag_storage] Failed to build MinIO client: {e}")
        return None


def _ensure_bucket(client: Minio) -> None:
    try:
        if not client.bucket_exists(RAG_BUCKET):
            client.make_bucket(RAG_BUCKET)
            logger.info(f"[rag_storage] Created bucket '{RAG_BUCKET}'")
    except S3Error as e:
        logger.error(f"[rag_storage] Bucket check/create failed: {e}")
        raise


def build_object_key(doc_id: str, filename: str) -> str:
    """Generate a deterministic S3 key: {doc_id}/{safe_filename}."""
    safe_name = os.path.basename(filename).replace("/", "_").replace("\\", "_")
    return f"{doc_id}/{safe_name}"


def upload_bytes(file_bytes: bytes, object_key: str, content_type: Optional[str] = None) -> str:
    """
    Upload bytes to the rag-docs bucket. Returns the S3 object key on success.
    Raises on failure — caller decides whether to abort ingest.
    """
    client = _get_minio_client()
    if not client:
        raise RuntimeError("MinIO/S3 not configured — cannot store RAG document.")

    _ensure_bucket(client)
    if not content_type:
        content_type, _ = mimetypes.guess_type(object_key)
        content_type = content_type or "application/octet-stream"

    try:
        client.put_object(
            bucket_name=RAG_BUCKET,
            object_name=object_key,
            data=io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type,
        )
        logger.info(f"[rag_storage] Uploaded {object_key} ({len(file_bytes)} bytes)")
        return object_key
    except S3Error as e:
        logger.error(f"[rag_storage] Upload failed for {object_key}: {e}")
        raise


def delete_object(object_key: str) -> bool:
    """Delete object from rag-docs bucket. Returns True on success, False if missing."""
    client = _get_minio_client()
    if not client:
        return False
    try:
        client.remove_object(RAG_BUCKET, object_key)
        logger.info(f"[rag_storage] Deleted {object_key}")
        return True
    except S3Error as e:
        if "NoSuchKey" in str(e):
            return False
        logger.error(f"[rag_storage] Delete failed for {object_key}: {e}")
        return False


def get_object_bytes(object_key: str) -> Optional[bytes]:
    """Download object bytes (for re-ingest on replace)."""
    client = _get_minio_client()
    if not client:
        return None
    try:
        response = client.get_object(RAG_BUCKET, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except S3Error as e:
        logger.error(f"[rag_storage] Download failed for {object_key}: {e}")
        return None


def presigned_download_url(object_key: str, expires_hours: int = 1) -> Optional[str]:
    """Generate a temporary download URL for the admin UI."""
    client = _get_minio_client()
    if not client:
        return None
    try:
        # Build a separate client that signs using the public-facing host if set
        public_url = os.getenv("OSS_PUBLIC_URL", "")
        if public_url:
            parsed = urlparse(public_url)
            endpoint = parsed.netloc or parsed.path
            secure   = parsed.scheme == "https"
            access_key = os.getenv("OSS_API_KEY", "") or os.getenv("MINIO_ROOT_USER", "")
            secret_key = os.getenv("OSS_SECRET_KEY", "") or os.getenv("MINIO_ROOT_PASSWORD", "")
            client = Minio(endpoint, access_key=access_key, secret_key=secret_key,
                           secure=secure, region="us-east-1")
        return client.presigned_get_object(
            RAG_BUCKET, object_key, expires=timedelta(hours=expires_hours)
        )
    except S3Error as e:
        logger.error(f"[rag_storage] Presign failed for {object_key}: {e}")
        return None

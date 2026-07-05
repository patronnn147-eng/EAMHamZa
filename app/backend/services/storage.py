import logging
from typing import Literal, Optional, Union
from urllib.parse import urljoin
from urllib.parse import urlparse

import httpx
import mimetypes
from datetime import datetime, timedelta, timezone

from minio import Minio
from minio.error import S3Error
from core.config import settings
from schemas.storage import (
    BucketInfo,
    BucketListResponse,
    BucketRequest,
    BucketResponse,
    DeleteResponse,
    FileUpDownRequest,
    FileUpDownResponse,
    ObjectInfo,
    ObjectListResponse,
    ObjectRequest,
    OSSBaseModel,
    RenameRequest,
    RenameResponse,
)

logger = logging.getLogger(__name__)


class StorageService:
    """Service for handling file upload and display with ObjectStorage service integration."""

    def __init__(self):
        if not settings.oss_service_url or not settings.oss_api_key:
            raise ValueError(
                "OSS service not configured. Set OSS_SERVICE_URL and OSS_API_KEY."
            )

        # If OSS_SECRET_KEY is provided, we assume S3/MinIO mode for presigned URLs.
        # The existing code path that calls `/api/v1/infra/client/oss/...` is for a custom OSS gateway,
        # not for MinIO itself.
        self._minio_client: Optional[Minio] = None
        if getattr(settings, "oss_secret_key", ""):
            parsed = urlparse(settings.oss_service_url)
            endpoint = parsed.netloc or parsed.path
            secure = parsed.scheme == "https"
            if not endpoint:
                raise ValueError(
                    "Invalid OSS_SERVICE_URL. Expected something like http://minio:9000/"
                )
            self._minio_client = Minio(
                endpoint,
                access_key=settings.oss_api_key,
                secret_key=settings.oss_secret_key,
                secure=secure,
                region="us-east-1",
            )

        self.headers = {
            "Authorization": f"Bearer {settings.oss_api_key}",
            "Content-Type": "application/json",
        }

    def _get_presign_client(self) -> Optional[Minio]:
        """Return a MinIO client configured for presigning URLs.

        Important: For AWS SigV4, the request Host is part of the signature.
        Rewriting the host *after* presigning will often lead to 403 SignatureDoesNotMatch.

        If OSS_PUBLIC_URL is provided, we sign using that host (e.g. localhost:9000)
        so the browser can use the URL as-is.
        """

        if not getattr(settings, "oss_secret_key", ""):
            return None

        public_base = getattr(settings, "oss_public_url", "")
        if not public_base:
            return self._minio_client

        parsed = urlparse(public_base)
        endpoint = parsed.netloc or parsed.path
        if not endpoint:
            return self._minio_client

        secure = parsed.scheme == "https"
        return Minio(
            endpoint,
            access_key=settings.oss_api_key,
            secret_key=settings.oss_secret_key,
            secure=secure,
            region="us-east-1",
        )

    def _ensure_bucket_exists(self, bucket_name: str) -> None:
        if not self._minio_client:
            return

        try:
            if not self._minio_client.bucket_exists(bucket_name):
                self._minio_client.make_bucket(bucket_name)
        except S3Error as e:
            logger.exception(f"Failed to ensure bucket exists '{bucket_name}': {e}")
            raise

    async def create_bucket(self, request: BucketRequest) -> BucketResponse:
        """
        Create a bucket name
        """
        endpoint = "api/v1/infra/client/oss/buckets"
        payload = {"bucket_name": request.bucket_name, "visibility": request.visibility}
        try:
            result = await self._apost_oss_service(endpoint, payload)
            return BucketResponse(
                bucket_name=result.get("bucket_name"),
                created_at=result.get("created_at"),
            )
        except Exception as e:
            logger.exception(f"Failed to create bucket: {e}")
            raise

    async def list_buckets(self) -> BucketListResponse:
        """
        List buckets of the user
        """
        endpoint = "api/v1/infra/client/oss/buckets"
        try:
            result = await self._aget_oss_service(endpoint=endpoint, params={})
            list_buckets = BucketListResponse()
            for item in result["buckets"]:
                list_buckets.buckets.append(
                    BucketInfo(
                        bucket_name=item["bucket_name"], visibility=item["visibility"]
                    )
                )
            return list_buckets
        except Exception as e:
            logger.exception(f"Failed to list buckets: {e}")
            raise

    async def list_objects(self, request: OSSBaseModel) -> ObjectListResponse:
        """
        List objests from the bucket
        """
        endpoint = f"api/v1/infra/client/oss/buckets/{request.bucket_name}/objects"
        try:
            result = await self._aget_oss_service(endpoint=endpoint, params={})
            list_objs = ObjectListResponse()
            for item in result["objects"]:
                list_objs.objects.append(
                    ObjectInfo(
                        bucket_name=request.bucket_name,
                        object_key=item["key"],
                        size=item["size"],
                        last_modified=item["last_modified"],
                        etag=item["etag"],
                    )
                )
            return list_objs
        except Exception as e:
            logger.exception(f"Failed to list bucket objects: {e}")
            raise

    async def get_object_info(self, request: ObjectRequest) -> ObjectInfo:
        """
        Get object metadata from the bucket
        """
        try:
            endpoint = f"api/v1/infra/client/oss/buckets/{request.bucket_name}/objects/metadata"
            params = {"object_key": request.object_key}
            result = await self._aget_oss_service(endpoint, params)
            return ObjectInfo(
                bucket_name=request.bucket_name,
                object_key=result["key"],
                size=result["size"],
                last_modified=result["last_modified"],
                etag=result["etag"],
            )
        except Exception as e:
            logger.exception(f"Failed to get object metadata: {e}")
            raise

    async def rename_object(self, request: RenameRequest) -> dict:
        endpoint = (
            f"api/v1/infra/client/oss/buckets/{request.bucket_name}/objects/rename"
        )
        payload = {
            "overwrite_key": request.overwrite_key,
            "source_key": request.source_key,
            "target_key": request.target_key,
        }
        try:
            await self._apost_oss_service(endpoint, payload)
            return RenameResponse(success=True)
        except Exception as e:
            logger.exception(f"Failed to rename object: {e}")
            raise

    async def delete_object(self, request: ObjectRequest) -> DeleteResponse:
        endpoint = f"api/v1/infra/client/oss/buckets/{request.bucket_name}/objects"
        payload = {"object_keys": [request.object_key]}
        try:
            await self._adelete_oss_service(endpoint, payload)
            return DeleteResponse(success=True)
        except Exception as e:
            logger.exception(f"Failed to rename object: {e}")
            raise

    async def create_upload_url(self, request: FileUpDownRequest) -> FileUpDownResponse:
        """
        Create presigned URL for file upload with access URL.
        """
        if not self._minio_client:
            endpoint = f"/api/v1/infra/client/oss/buckets/{request.bucket_name}/objects/upload_url"
            payload = {"expires_in": 0, "object_key": request.object_key}
            try:
                result = await self._apost_oss_service(endpoint, payload)
                return FileUpDownResponse(
                    upload_url=result.get("upload_url"),
                    expires_at=result.get("expires_at"),
                )
            except Exception as e:
                logger.exception(f"Failed to create upload URL: {e}")
                raise

        try:
            self._ensure_bucket_exists(request.bucket_name)
            expires = timedelta(hours=1)
            presign_client = self._get_presign_client()
            if not presign_client:
                raise ValueError("OSS presign client not configured")

            url = presign_client.presigned_put_object(
                request.bucket_name,
                request.object_key,
                expires=expires,
            )
            expires_at = (datetime.now(timezone.utc) + expires).isoformat()
            return FileUpDownResponse(upload_url=url, expires_at=expires_at)
        except S3Error as e:
            logger.exception(f"Failed to create MinIO upload URL: {e}")
            raise

    async def create_download_url(
        self, request: FileUpDownRequest
    ) -> FileUpDownResponse:
        """
        Create presigned URL for file download with access URL.
        """
        if not self._minio_client:
            endpoint = f"/api/v1/infra/client/oss/buckets/{request.bucket_name}/objects/download_url"
            content_type, _ = mimetypes.guess_type(str(request.object_key))
            if not content_type:
                content_type = "application/octet-stream"
            payload = {
                "content_type": content_type,
                "expires_in": 0,
                "object_key": request.object_key,
            }
            try:
                result = await self._apost_oss_service(endpoint, payload)
                return FileUpDownResponse(
                    download_url=result.get("download_url"),
                    expires_at=result.get("expires_at"),
                )
            except Exception as e:
                logger.exception(f"Failed to create upload URL: {e}")
                raise

        try:
            self._ensure_bucket_exists(request.bucket_name)
            expires = timedelta(hours=1)
            presign_client = self._get_presign_client()
            if not presign_client:
                raise ValueError("OSS presign client not configured")

            url = presign_client.presigned_get_object(
                request.bucket_name,
                request.object_key,
                expires=expires,
            )
            expires_at = (datetime.now(timezone.utc) + expires).isoformat()
            return FileUpDownResponse(download_url=url, expires_at=expires_at)
        except S3Error as e:
            logger.exception(f"Failed to create MinIO download URL: {e}")
            raise

    async def _aget_oss_service(self, endpoint: str, params: dict) -> dict:
        return await self._arequest_oss_service("GET", endpoint, params=params)

    async def _apost_oss_service(
        self, endpoint: str, payload: dict
    ) -> Union[dict, list]:
        return await self._arequest_oss_service("POST", endpoint, payload=payload)

    async def _adelete_oss_service(
        self, endpoint: str, payload: dict
    ) -> Union[dict, list]:
        return await self._arequest_oss_service("DELETE", endpoint, payload=payload)

    async def _arequest_oss_service(
        self,
        method: Literal["GET", "POST", "DELETE"],
        endpoint: str,
        params: Optional[dict] = None,
        payload: Optional[dict] = None,
    ) -> Union[dict, list]:
        """统一的 OSS 服务请求方法"""
        url = urljoin(settings.oss_service_url, endpoint)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()

                if result.get("code") != 0:
                    logger.warning(f"ObjectStorage service error: {result}")
                    error_msg = result.get("error", "Unknown error")
                    message = result.get("message", "")
                    raise ValueError(
                        f"ObjectStorage service error: {error_msg}. {message}"
                    )

                return result.get("data", [])
        except httpx.HTTPStatusError as e:
            error_msg = f"ObjectStorage service HTTP error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            logger.exception(f"Failed to call ObjectStorage service: {e}")
            raise

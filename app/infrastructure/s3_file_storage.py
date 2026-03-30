from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Protocol, cast

import aioboto3
from aioboto3 import Session
from botocore.config import Config

from app.core.config import S3Config
from app.domain.storage import AbstractFileStorage, StoredObjectMetadata
from app.services.exceptions import DocumentStorageError


class S3ClientProtocol(Protocol):
    def generate_presigned_url(
        self,
        client_method: str,
        **kwargs: object,
    ) -> str | Awaitable[str]: ...

    async def head_object(self, **kwargs: object) -> dict[str, object]: ...

    async def delete_object(self, **kwargs: object) -> dict[str, object]: ...


class S3SessionProtocol(Protocol):
    def client(
        self,
        service_name: str,
        *,
        region_name: str,
        endpoint_url: str | None,
        config: Config | None = None,
    ) -> AbstractAsyncContextManager[S3ClientProtocol]: ...


type SessionFactory = Callable[[], S3SessionProtocol]


class S3FileStorage(AbstractFileStorage):
    def __init__(
        self,
        config: S3Config,
        *,
        session_factory: SessionFactory | None = None,
    ) -> None:
        self._bucket = config.bucket
        self._region = config.region
        self._endpoint_url = config.endpoint_url
        self._presign_expire_seconds = config.presign_expire_seconds
        self._key_prefix = self._normalize_key_prefix(config.key_prefix)
        self._session_factory = session_factory or _default_session_factory

    async def generate_presigned_put_url(
        self,
        storage_key: str,
        content_type: str,
        max_size: int,
    ) -> str:
        _ = max_size
        object_key = self._build_object_key(storage_key)

        try:
            async with self._client() as s3_client:
                presigned_url = s3_client.generate_presigned_url(
                    "put_object",
                    Params={
                        "Bucket": self._bucket,
                        "Key": object_key,
                        "ContentType": content_type,
                    },
                    ExpiresIn=self._presign_expire_seconds,
                )
        except Exception as err:
            msg = f"Failed to generate S3 upload URL for key '{object_key}'."
            raise DocumentStorageError(msg) from err

        return await _resolve_awaitable_str(presigned_url)

    async def generate_presigned_get_url(self, storage_key: str) -> str:
        object_key = self._build_object_key(storage_key)
        try:
            async with self._client() as s3_client:
                presigned_url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self._bucket,
                        "Key": object_key,
                    },
                    ExpiresIn=self._presign_expire_seconds,
                )
        except Exception as err:
            msg = f"Failed to generate S3 download URL for key '{object_key}'."
            raise DocumentStorageError(msg) from err

        return await _resolve_awaitable_str(presigned_url)

    async def get_file_metadata(self, storage_key: str) -> StoredObjectMetadata | None:
        object_key = self._build_object_key(storage_key)

        try:
            async with self._client() as s3_client:
                head_response = await s3_client.head_object(
                    Bucket=self._bucket,
                    Key=object_key,
                )
        except Exception as err:
            if _is_object_not_found_error(err):
                return None

            msg = f"Failed to fetch metadata for S3 key '{object_key}'."
            raise DocumentStorageError(msg) from err

        size_bytes = _parse_content_length(head_response.get("ContentLength"))
        etag = _normalize_optional_etag(head_response.get("ETag"))
        content_type = cast("str | None", head_response.get("ContentType"))
        return StoredObjectMetadata(
            size_bytes=size_bytes,
            etag=etag,
            content_type=content_type,
        )

    async def delete(self, storage_key: str) -> None:
        object_key = self._build_object_key(storage_key)

        try:
            async with self._client() as s3_client:
                await s3_client.delete_object(
                    Bucket=self._bucket,
                    Key=object_key,
                )
        except Exception as err:
            msg = f"Failed to delete S3 object '{object_key}'."
            raise DocumentStorageError(msg) from err

    @asynccontextmanager
    async def _client(self) -> AsyncIterator[S3ClientProtocol]:
        session = self._session_factory()

        addressing_style = "path" if self._endpoint_url else "virtual"

        boto_config = Config(
            signature_version="s3v4",
            s3={"addressing_style": addressing_style},
        )

        async with session.client(
            "s3",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            config=boto_config,
        ) as s3_client:
            yield s3_client

    @staticmethod
    def _normalize_key_prefix(key_prefix: str) -> str:
        normalized_prefix = key_prefix.strip("/")
        if not normalized_prefix:
            return ""
        return f"{normalized_prefix}/"

    def _build_object_key(self, storage_key: str) -> str:
        normalized_storage_key = storage_key.strip("/")
        if not normalized_storage_key:
            msg = "Storage key cannot be empty."
            raise DocumentStorageError(msg)
        return f"{self._key_prefix}{normalized_storage_key}"


def _default_session_factory() -> Session:
    return aioboto3.Session()


async def _resolve_awaitable_str(value: str | Awaitable[str]) -> str:
    if isinstance(value, str):
        return value
    return await value


def _normalize_optional_etag(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip('"')


def _parse_content_length(value: object) -> int:
    if isinstance(value, int):
        return value

    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as err:
            msg = "S3 metadata contains invalid ContentLength."
            raise DocumentStorageError(msg) from err

    msg = "S3 metadata is missing ContentLength."
    raise DocumentStorageError(msg)


def _is_object_not_found_error(err: Exception) -> bool:
    response = getattr(err, "response", None)
    if not isinstance(response, dict):
        return False

    error_data = response.get("Error")
    if not isinstance(error_data, dict):
        return False

    error_code = error_data.get("Code")
    if not isinstance(error_code, str):
        return False

    return error_code in {"404", "NoSuchKey", "NotFound"}

import pytest
from botocore.config import Config

from app.core.config import S3Config
from app.infrastructure import S3FileStorage
from app.services import DocumentStorageError

pytestmark = pytest.mark.anyio


class FakeClientError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3Client:
    def __init__(self) -> None:
        self.presign_calls: list[dict[str, object]] = []
        self.head_calls: list[dict[str, str]] = []
        self.delete_calls: list[dict[str, str]] = []

        self.presign_url = "https://example.com/presigned"
        self.presign_error: Exception | None = None
        self.head_response: dict[str, object] = {
            "ContentLength": 123,
            "ETag": '"etag-123"',
            "ContentType": "application/pdf",
        }
        self.head_error: Exception | None = None
        self.delete_error: Exception | None = None

    def generate_presigned_url(
        self,
        operation_name: str,
        **kwargs: object,
    ) -> str:
        if self.presign_error is not None:
            raise self.presign_error

        params = kwargs["Params"]
        expires_in = kwargs["ExpiresIn"]
        if not isinstance(params, dict):
            msg = "Expected Params to be a dict"
            raise TypeError(msg)
        if not isinstance(expires_in, int):
            msg = "Expected ExpiresIn to be an int"
            raise TypeError(msg)

        self.presign_calls.append(
            {
                "operation_name": operation_name,
                "params": params,
                "expires_in": expires_in,
            }
        )
        return self.presign_url

    async def head_object(self, **kwargs: object) -> dict[str, object]:
        if self.head_error is not None:
            raise self.head_error

        bucket = kwargs["Bucket"]
        key = kwargs["Key"]
        if not isinstance(bucket, str):
            msg = "Expected Bucket to be a string"
            raise TypeError(msg)
        if not isinstance(key, str):
            msg = "Expected Key to be a string"
            raise TypeError(msg)

        self.head_calls.append({"bucket": bucket, "key": key})
        return self.head_response

    async def delete_object(self, **kwargs: object) -> None:
        if self.delete_error is not None:
            raise self.delete_error

        bucket = kwargs["Bucket"]
        key = kwargs["Key"]
        if not isinstance(bucket, str):
            msg = "Expected Bucket to be a string"
            raise TypeError(msg)
        if not isinstance(key, str):
            msg = "Expected Key to be a string"
            raise TypeError(msg)

        self.delete_calls.append({"bucket": bucket, "key": key})


class FakeClientContextManager:
    def __init__(self, client: FakeS3Client) -> None:
        self.client = client

    async def __aenter__(self) -> FakeS3Client:
        return self.client

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeSession:
    def __init__(self, client: FakeS3Client) -> None:
        self._client = client
        self.client_calls: list[dict[str, object]] = []

    def client(
        self,
        service_name: str,
        *,
        region_name: str,
        endpoint_url: str | None,
        config: Config | None = None,
    ) -> FakeClientContextManager:
        self.client_calls.append(
            {
                "service_name": service_name,
                "region_name": region_name,
                "endpoint_url": endpoint_url,
                "config": config,
            }
        )
        return FakeClientContextManager(self._client)


@pytest.fixture
def fake_client() -> FakeS3Client:
    return FakeS3Client()


@pytest.fixture
def fake_session(fake_client: FakeS3Client) -> FakeSession:
    return FakeSession(fake_client)


@pytest.fixture
def storage(fake_session: FakeSession) -> S3FileStorage:
    return S3FileStorage(
        config=S3Config(
            bucket="flow-docs-dev",
            region="eu-north-1",
            presign_expire_seconds=600,
            endpoint_url="http://localstack:4566",
            key_prefix="documents",
        ),
        session_factory=lambda: fake_session,
    )


async def test_generate_presigned_put_url_uses_expected_s3_params(
    storage: S3FileStorage,
    fake_client: FakeS3Client,
    fake_session: FakeSession,
) -> None:
    url = await storage.generate_presigned_put_url(
        storage_key="projects/1/documents/report.pdf",
        content_type="application/pdf",
        max_size=10 * 1024 * 1024,
    )

    assert url == "https://example.com/presigned"
    assert fake_client.presign_calls == [
        {
            "operation_name": "put_object",
            "params": {
                "Bucket": "flow-docs-dev",
                "Key": "documents/projects/1/documents/report.pdf",
                "ContentType": "application/pdf",
            },
            "expires_in": 600,
        }
    ]
    assert len(fake_session.client_calls) == 1
    client_call = fake_session.client_calls[0]
    assert client_call["service_name"] == "s3"
    assert client_call["region_name"] == "eu-north-1"
    assert client_call["endpoint_url"] == "http://localstack:4566"
    assert isinstance(client_call["config"], Config)


async def test_generate_presigned_get_url_uses_expected_s3_params(
    storage: S3FileStorage,
    fake_client: FakeS3Client,
    fake_session: FakeSession,
) -> None:
    url = await storage.generate_presigned_get_url("projects/1/documents/report.pdf")

    assert url == "https://example.com/presigned"
    assert fake_client.presign_calls == [
        {
            "operation_name": "get_object",
            "params": {
                "Bucket": "flow-docs-dev",
                "Key": "documents/projects/1/documents/report.pdf",
            },
            "expires_in": 600,
        }
    ]
    assert len(fake_session.client_calls) == 1
    assert isinstance(fake_session.client_calls[0]["config"], Config)


async def test_get_file_metadata_returns_expected_metadata(
    storage: S3FileStorage,
    fake_client: FakeS3Client,
) -> None:
    metadata = await storage.get_file_metadata("projects/1/documents/report.pdf")

    assert metadata is not None
    assert metadata.size_bytes == 123
    assert metadata.etag == "etag-123"
    assert metadata.content_type == "application/pdf"
    assert fake_client.head_calls == [
        {
            "bucket": "flow-docs-dev",
            "key": "documents/projects/1/documents/report.pdf",
        }
    ]


async def test_get_file_metadata_returns_none_for_missing_object(
    storage: S3FileStorage,
    fake_client: FakeS3Client,
) -> None:
    fake_client.head_error = FakeClientError("NoSuchKey")

    metadata = await storage.get_file_metadata("projects/1/documents/report.pdf")

    assert metadata is None


async def test_delete_raises_storage_error_when_s3_delete_fails(
    storage: S3FileStorage,
    fake_client: FakeS3Client,
) -> None:
    fake_client.delete_error = RuntimeError("boom")

    with pytest.raises(DocumentStorageError):
        await storage.delete("projects/1/documents/report.pdf")

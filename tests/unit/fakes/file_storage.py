from app.services import AbstractFileStorage, DocumentStorageError, StoredObjectMetadata


class InMemoryFileStorage(AbstractFileStorage):
    def __init__(self) -> None:
        self.files: dict[str, StoredObjectMetadata] = {}
        self.deleted_keys: list[str] = []
        self.presigned_put_requests: list[tuple[str, str, int]] = []
        self.presigned_get_requests: list[str] = []
        self.put_url_error: DocumentStorageError | None = None
        self.get_url_error: DocumentStorageError | None = None
        self.metadata_error: DocumentStorageError | None = None
        self.delete_error: DocumentStorageError | None = None
        self.put_url = "https://storage.example.com/upload"
        self.get_url = "https://storage.example.com/download"

    async def generate_presigned_put_url(
        self,
        storage_key: str,
        content_type: str,
        max_size: int,
    ) -> str:
        if self.put_url_error is not None:
            raise self.put_url_error

        self.presigned_put_requests.append((storage_key, content_type, max_size))
        return self.put_url

    async def generate_presigned_get_url(self, storage_key: str) -> str:
        if self.get_url_error is not None:
            raise self.get_url_error

        self.presigned_get_requests.append(storage_key)
        return self.get_url

    async def get_file_metadata(self, storage_key: str) -> StoredObjectMetadata | None:
        if self.metadata_error is not None:
            raise self.metadata_error

        return self.files.get(storage_key)

    async def delete(self, storage_key: str) -> None:
        if self.delete_error is not None:
            raise self.delete_error

        self.deleted_keys.append(storage_key)
        self.files.pop(storage_key, None)

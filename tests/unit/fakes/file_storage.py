from app.services import AbstractFileStorage, DocumentStorageError, StoredFile


class InMemoryFileStorage(AbstractFileStorage):
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.saved_files: list[tuple[str, str, str, bytes]] = []
        self.deleted_keys: list[str] = []
        self.save_error: DocumentStorageError | None = None
        self.delete_error: DocumentStorageError | None = None
        self.storage_key = "documents/generated-key"

    async def save(
        self,
        content: bytes,
        *,
        filename: str,
        content_type: str,
        checksum: str,
    ) -> StoredFile:
        if self.save_error is not None:
            raise self.save_error

        self.files[self.storage_key] = content
        self.saved_files.append((filename, content_type, checksum, content))
        return StoredFile(storage_key=self.storage_key)

    async def delete(self, storage_key: str) -> None:
        if self.delete_error is not None:
            raise self.delete_error

        self.deleted_keys.append(storage_key)
        self.files.pop(storage_key, None)

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredObjectMetadata:
    size_bytes: int
    etag: str | None = None
    content_type: str | None = None


class AbstractFileStorage(ABC):
    @abstractmethod
    async def generate_presigned_put_url(
        self,
        storage_key: str,
        content_type: str,
        max_size: int,
    ) -> str:
        """Generate a temporary direct-upload URL for the given object."""

    @abstractmethod
    async def generate_presigned_get_url(self, storage_key: str) -> str:
        """Generate a temporary download URL for the given object."""

    @abstractmethod
    async def get_file_metadata(self, storage_key: str) -> StoredObjectMetadata | None:
        """Return uploaded object metadata, or ``None`` when the object is missing."""

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        """Delete a previously stored file."""

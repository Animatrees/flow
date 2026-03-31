from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredObjectMetadata:
    """Data object for metadata fetched from object storage."""

    size_bytes: int
    etag: str | None = None
    content_type: str | None = None


class AbstractFileStorage(ABC):
    """Storage contract for direct-upload object operations.

    Supports:
        - presigned upload URL generation
        - presigned download URL generation
        - object metadata reads
        - object deletion
    """

    @abstractmethod
    async def generate_presigned_put_url(
        self,
        storage_key: str,
        content_type: str,
        max_size: int,
    ) -> str:
        """Generate a temporary direct-upload URL."""

    @abstractmethod
    async def generate_presigned_get_url(self, storage_key: str) -> str:
        """Generate a temporary download URL."""

    @abstractmethod
    async def get_file_metadata(self, storage_key: str) -> StoredObjectMetadata | None:
        """Return uploaded object metadata, or ``None`` when the object is missing."""

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        """Delete a previously stored file."""

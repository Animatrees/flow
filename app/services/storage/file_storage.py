from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredFile:
    storage_key: str


class AbstractFileStorage(ABC):
    @abstractmethod
    async def save(
        self,
        content: bytes,
        *,
        filename: str,
        content_type: str,
        checksum: str,
    ) -> StoredFile:
        """Persist file content and return storage metadata."""

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        """Delete a previously stored file."""

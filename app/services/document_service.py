import asyncio
import logging
from collections.abc import Sequence
from hashlib import sha256

from app.schemas.document import DocumentCreate, DocumentCreateStored, DocumentRead, DocumentUpdate
from app.schemas.project import ProjectRead
from app.schemas.type_ids import DocumentId, ProjectId
from app.schemas.user import UserRead
from app.services.exceptions import (
    DocumentNotFoundError,
    DocumentTooLargeError,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    UnsupportedDocumentTypeError,
)
from app.services.repositories.document_repository import AbstractDocumentRepository
from app.services.repositories.project_repository import AbstractProjectRepository
from app.services.storage.file_storage import AbstractFileStorage

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        repo: AbstractDocumentRepository,
        project_repo: AbstractProjectRepository,
        file_storage: AbstractFileStorage,
        *,
        max_document_size_bytes: int = 10 * 1024 * 1024,
        allowed_content_types: frozenset[str] | None = None,
    ) -> None:
        self.repo = repo
        self.project_repo = project_repo
        self.file_storage = file_storage
        self.max_document_size_bytes = max_document_size_bytes
        self.allowed_content_types = allowed_content_types or frozenset(
            {
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
        )

    async def create(
        self,
        current_user: UserRead,
        project_id: ProjectId,
        data: DocumentCreate,
        content: bytes,
    ) -> DocumentRead:
        await self._ensure_project_access(current_user, project_id)
        self._validate_content_type(data.content_type)
        size_bytes = self._validate_size(content)
        checksum = await self._calculate_checksum(content)

        stored_file = await self.file_storage.save(
            content,
            filename=data.filename,
            content_type=data.content_type,
            checksum=checksum,
        )

        try:
            return await self.repo.create(
                DocumentCreateStored(
                    project_id=project_id,
                    uploaded_by=current_user.id,
                    filename=data.filename,
                    content_type=data.content_type,
                    size_bytes=size_bytes,
                    storage_key=stored_file.storage_key,
                    checksum=checksum,
                )
            )
        except Exception:
            await self._delete_file_safely(stored_file.storage_key)
            raise

    async def get_by_id(self, current_user: UserRead, document_id: DocumentId) -> DocumentRead:
        document = await self._get_document(document_id)
        await self._ensure_project_access(current_user, document.project_id)
        return document

    async def get_all_for_project(
        self,
        current_user: UserRead,
        project_id: ProjectId,
    ) -> Sequence[DocumentRead]:
        await self._ensure_project_access(current_user, project_id)
        return await self.repo.get_all_for_project(project_id)

    async def update(
        self,
        current_user: UserRead,
        document_id: DocumentId,
        data: DocumentUpdate,
    ) -> DocumentRead:
        document = await self._get_document(document_id)
        await self._ensure_project_access(current_user, document.project_id)

        updated_document = await self.repo.update(document_id, data)
        if updated_document is None:
            msg = f"Document with id '{document_id}' was not found."
            raise DocumentNotFoundError(msg)
        return updated_document

    async def delete(self, current_user: UserRead, document_id: DocumentId) -> None:
        document = await self._get_document(document_id)
        await self._ensure_project_access(current_user, document.project_id)

        success = await self.repo.delete(document_id)
        if not success:
            msg = f"Document with id '{document_id}' was not found."
            raise DocumentNotFoundError(msg)

        await self._delete_file_safely(document.storage_key)

    async def _get_document(self, document_id: DocumentId) -> DocumentRead:
        document = await self.repo.get_by_id(document_id)
        if document is None:
            msg = f"Document with id '{document_id}' was not found."
            raise DocumentNotFoundError(msg)
        return document

    async def _ensure_project_access(self, current_user: UserRead, project_id: ProjectId) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            msg = f"Project with id '{project_id}' was not found."
            raise ProjectNotFoundError(msg)

        if self._is_owner(current_user, project):
            return

        if await self.project_repo.is_member(project_id, current_user.id):
            return

        raise ProjectAccessDeniedError

    @staticmethod
    def _is_owner(current_user: UserRead, project: ProjectRead) -> bool:
        return current_user.id == project.owner_id

    def _validate_content_type(self, content_type: str) -> None:
        if content_type not in self.allowed_content_types:
            msg = f"Document content type '{content_type}' is not supported."
            raise UnsupportedDocumentTypeError(msg)

    def _validate_size(self, content: bytes) -> int:
        size_bytes = len(content)
        if size_bytes > self.max_document_size_bytes:
            msg = (
                f"Document exceeds the maximum allowed size of "
                f"{self.max_document_size_bytes} bytes."
            )
            raise DocumentTooLargeError(msg)
        return size_bytes

    @staticmethod
    async def _calculate_checksum(content: bytes) -> str:
        return await asyncio.to_thread(lambda: sha256(content).hexdigest())

    async def _delete_file_safely(self, storage_key: str) -> None:
        try:
            await self.file_storage.delete(storage_key)
        except Exception:
            logger.exception("Failed to safely delete stored document file '%s'", storage_key)

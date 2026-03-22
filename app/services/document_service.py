import logging
from collections.abc import Sequence

from uuid_extensions import uuid7

from app.domain.repositories import AbstractDocumentRepository
from app.domain.repositories.project_repository import AbstractProjectRepository
from app.domain.schemas import ProjectRead
from app.domain.schemas.document import (
    DocumentConfirmUpload,
    DocumentCreate,
    DocumentCreateStored,
    DocumentRead,
    DocumentUpdate,
    UploadIntentResponse,
)
from app.domain.schemas.type_ids import DocumentId, ProjectId
from app.domain.schemas.user import UserAuthRead
from app.domain.storage import AbstractFileStorage
from app.services.exceptions import (
    DocumentNotFoundError,
    DocumentStorageError,
    DocumentTooLargeError,
    PermissionDeniedError,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    UnsupportedDocumentTypeError,
)

logger = logging.getLogger(__name__)

MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_FILE_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


class DocumentService:
    def __init__(
        self,
        repo: AbstractDocumentRepository,
        project_repo: AbstractProjectRepository,
        file_storage: AbstractFileStorage,
    ) -> None:
        self.repo = repo
        self.project_repo = project_repo
        self.file_storage = file_storage

    async def initiate_upload(
        self,
        current_user: UserAuthRead,
        project_id: ProjectId,
        data: DocumentCreate,
    ) -> UploadIntentResponse:
        await self._ensure_project_access(current_user, project_id)
        self._validate_file_type(data.filename, data.content_type)
        self._validate_size(data.size_bytes)

        storage_key = self._build_storage_key(project_id)
        upload_url = await self.file_storage.generate_presigned_put_url(
            storage_key=storage_key,
            content_type=data.content_type,
            max_size=MAX_DOCUMENT_SIZE_BYTES,
        )

        return UploadIntentResponse(
            upload_url=upload_url,
            storage_key=storage_key,
        )

    async def confirm_upload(
        self,
        current_user: UserAuthRead,
        project_id: ProjectId,
        data: DocumentConfirmUpload,
    ) -> DocumentRead:
        await self._ensure_project_access(current_user, project_id)
        self._validate_file_type(data.filename, data.content_type)
        self._ensure_storage_key_matches_project(project_id, data.storage_key)

        stored_object = await self.file_storage.get_file_metadata(data.storage_key)
        if stored_object is None:
            msg = f"Uploaded document '{data.storage_key}' was not found in storage."
            raise DocumentStorageError(msg)

        size_bytes = self._validate_size(stored_object.size_bytes)

        try:
            return await self.repo.create(
                DocumentCreateStored(
                    project_id=project_id,
                    uploaded_by=current_user.id,
                    filename=data.filename,
                    content_type=data.content_type,
                    size_bytes=size_bytes,
                    storage_key=data.storage_key,
                    checksum=data.checksum,
                )
            )
        except Exception:
            await self._delete_file_safely(data.storage_key)
            raise

    async def get_by_id(self, current_user: UserAuthRead, document_id: DocumentId) -> DocumentRead:
        document = await self._get_document(document_id)
        await self._ensure_project_access(current_user, document.project_id)
        return document

    async def get_download_url(self, current_user: UserAuthRead, document_id: DocumentId) -> str:
        document = await self._get_document(document_id)
        await self._ensure_project_access(current_user, document.project_id)
        return await self.file_storage.generate_presigned_get_url(document.storage_key)

    async def get_all_for_project(
        self,
        current_user: UserAuthRead,
        project_id: ProjectId,
    ) -> Sequence[DocumentRead]:
        await self._ensure_project_access(current_user, project_id)
        return await self.repo.get_all_for_project(project_id)

    async def update(
        self,
        current_user: UserAuthRead,
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

    async def delete(self, current_user: UserAuthRead, document_id: DocumentId) -> None:
        document = await self._get_document(document_id)
        await self._ensure_delete_access(current_user, document)

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

    async def _ensure_project_access(
        self, current_user: UserAuthRead, project_id: ProjectId
    ) -> None:
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
    def _is_owner(current_user: UserAuthRead, project: ProjectRead) -> bool:
        return current_user.id == project.owner_id

    @staticmethod
    def _build_storage_key(project_id: ProjectId) -> str:
        return f"projects/{project_id}/documents/{uuid7()}"

    @staticmethod
    def _ensure_storage_key_matches_project(project_id: ProjectId, storage_key: str) -> None:
        expected_prefix = f"projects/{project_id}/documents/"
        if storage_key.startswith(expected_prefix):
            return

        msg = f"Storage key '{storage_key}' does not belong to project '{project_id}'."
        raise DocumentStorageError(msg)

    @staticmethod
    def _validate_content_type(content_type: str) -> None:
        if content_type not in ALLOWED_FILE_TYPES:
            msg = f"Document content type '{content_type}' is not supported."
            raise UnsupportedDocumentTypeError(msg)

    def _validate_file_type(self, filename: str, content_type: str) -> None:
        self._validate_content_type(content_type)
        expected_extension = ALLOWED_FILE_TYPES[content_type]

        if "." not in filename:
            return
        if filename.lower().endswith(expected_extension):
            return

        msg = (
            f"Filename '{filename}' does not match the expected extension "
            f"'{expected_extension}' for content type '{content_type}'."
        )
        raise UnsupportedDocumentTypeError(msg)

    @staticmethod
    def _validate_size(size_bytes: int) -> int:
        if size_bytes > MAX_DOCUMENT_SIZE_BYTES:
            msg = f"Document exceeds the maximum allowed size of {MAX_DOCUMENT_SIZE_BYTES} bytes."
            raise DocumentTooLargeError(msg)
        return size_bytes

    async def _ensure_delete_access(
        self, current_user: UserAuthRead, document: DocumentRead
    ) -> None:
        project = await self.project_repo.get_by_id(document.project_id)
        if project is None:
            msg = f"Project with id '{document.project_id}' was not found."
            raise ProjectNotFoundError(msg)

        if self._is_owner(current_user, project):
            return

        if await self.project_repo.is_member(document.project_id, current_user.id):
            if document.uploaded_by == current_user.id:
                return
            raise PermissionDeniedError

        raise ProjectAccessDeniedError

    async def _delete_file_safely(self, storage_key: str) -> None:
        try:
            await self.file_storage.delete(storage_key)
        except Exception:
            logger.exception("Failed to safely delete stored document file '%s'", storage_key)

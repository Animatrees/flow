import logging
from collections.abc import Sequence
from uuid import UUID

from uuid_extensions import uuid7

from app.core.config import JWTConfig
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
from app.domain.schemas.type_ids import DocumentId, ProjectId, UserId
from app.domain.schemas.user import UserAuthRead
from app.domain.storage import AbstractFileStorage
from app.services.exceptions import (
    DocumentNotFoundError,
    DocumentStorageError,
    DocumentTooLargeError,
    InvalidTokenError,
    InvalidUploadTokenError,
    PermissionDeniedError,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    UnsupportedDocumentTypeError,
)
from app.services.jwt_service import JWTService

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
        jwt_service: JWTService,
        jwt_config: JWTConfig,
    ) -> None:
        self.repo = repo
        self.project_repo = project_repo
        self.file_storage = file_storage
        self.jwt_service = jwt_service
        self.jwt_config = jwt_config

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
        upload_token = self.jwt_service.create_token(
            {
                "sub": storage_key,
                "project_id": str(project_id),
                "uploaded_by": str(current_user.id),
                "type": "upload_intent",
            },
            expire_minutes=self.jwt_config.upload_token_expire_minutes,
        ).token

        return UploadIntentResponse(
            upload_url=upload_url,
            upload_token=upload_token,
        )

    async def confirm_upload(
        self,
        current_user: UserAuthRead,
        project_id: ProjectId,
        data: DocumentConfirmUpload,
    ) -> DocumentRead:
        await self._ensure_project_access(current_user, project_id)
        self._validate_file_type(data.filename, data.content_type)
        storage_key = self._decode_upload_token(
            upload_token=data.upload_token,
            project_id=project_id,
            user_id=current_user.id,
        )

        stored_object = await self.file_storage.get_file_metadata(storage_key)
        if stored_object is None:
            msg = f"Uploaded document '{storage_key}' was not found in storage."
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
                    storage_key=storage_key,
                    checksum=data.checksum,
                )
            )
        except Exception:
            await self._delete_file_safely(storage_key)
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

        if await self.project_repo.has_access_to_project(project_id, current_user.id):
            return

        raise ProjectAccessDeniedError

    @staticmethod
    def _is_owner(current_user: UserAuthRead, project: ProjectRead) -> bool:
        return current_user.id == project.owner_id

    @staticmethod
    def _build_storage_key(project_id: ProjectId) -> str:
        return f"projects/{project_id}/documents/{uuid7()}"

    def _decode_upload_token(
        self, upload_token: str, project_id: ProjectId, user_id: UserId
    ) -> str:
        try:
            payload = self.jwt_service.decode_token(upload_token)
        except InvalidTokenError as err:
            raise InvalidUploadTokenError from err

        if payload.get("type") != "upload_intent":
            msg = "Upload token has invalid type."
            raise InvalidUploadTokenError(msg)

        subject = payload.get("sub")
        if not subject:
            msg = "Upload token missing required 'sub' claim."
            raise InvalidUploadTokenError(msg)

        token_project_id = self._parse_token_uuid(payload.get("project_id"), "project_id")
        if token_project_id != project_id:
            msg = "Upload token does not belong to this project."
            raise InvalidUploadTokenError(msg)

        token_user_id = self._parse_token_uuid(payload.get("uploaded_by"), "uploaded_by")
        if token_user_id != user_id:
            msg = "Upload token does not belong to this user."
            raise InvalidUploadTokenError(msg)

        return subject

    @staticmethod
    def _parse_token_uuid(value: object, field_name: str) -> UUID:
        if not isinstance(value, str) or not value:
            msg = f"Upload token missing required '{field_name}' claim."
            raise InvalidUploadTokenError(msg)

        try:
            return UUID(value)
        except ValueError as err:
            msg = f"Upload token has invalid '{field_name}' claim."
            raise InvalidUploadTokenError(msg) from err

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

        if await self.project_repo.has_access_to_project(document.project_id, current_user.id):
            if document.uploaded_by == current_user.id:
                return
            raise PermissionDeniedError

        raise ProjectAccessDeniedError

    async def _delete_file_safely(self, storage_key: str) -> None:
        try:
            await self.file_storage.delete(storage_key)
        except Exception:
            logger.exception("Failed to safely delete stored document file '%s'", storage_key)

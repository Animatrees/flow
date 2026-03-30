from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document
from app.db.repositories.exceptions import (
    ConflictError,
    ProjectNotFoundError,
    RepositoryError,
    UserNotFoundError,
)
from app.domain.repositories import AbstractDocumentRepository
from app.domain.schemas.document import DocumentCreateStored, DocumentUpdate, StoredDocument
from app.domain.schemas.type_ids import DocumentId, ProjectId


class DocumentRepository(AbstractDocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id_: DocumentId) -> StoredDocument | None:
        document = await self.session.get(Document, id_)
        return StoredDocument.model_validate(document) if document is not None else None

    async def get_all(self) -> Sequence[StoredDocument]:
        statement = select(Document).order_by(Document.created_at, Document.id)
        documents = await self.session.scalars(statement)
        return [StoredDocument.model_validate(document) for document in documents]

    async def get_all_for_project(self, project_id: ProjectId) -> Sequence[StoredDocument]:
        statement = (
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at, Document.id)
        )
        documents = await self.session.scalars(statement)
        return [StoredDocument.model_validate(document) for document in documents]

    async def create(self, data: DocumentCreateStored) -> StoredDocument:
        document = Document(**data.model_dump())
        self.session.add(document)

        try:
            await self.session.flush()
        except IntegrityError as err:
            raise self._map_create_integrity_error(err, data) from err

        return StoredDocument.model_validate(document)

    async def update(self, id_: DocumentId, data: DocumentUpdate) -> StoredDocument | None:
        document = await self.session.get(Document, id_)
        if document is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(document, field, value)

        try:
            await self.session.flush()
        except IntegrityError as err:
            raise self._map_update_integrity_error(err) from err

        return StoredDocument.model_validate(document)

    async def delete(self, id_: DocumentId) -> bool:
        document = await self.session.get(Document, id_)
        if document is None:
            return False

        await self.session.delete(document)
        await self.session.flush()
        return True

    @staticmethod
    def _map_create_integrity_error(
        err: IntegrityError,
        data: DocumentCreateStored,
    ) -> RepositoryError:
        error_text = str(err.orig).lower()

        if "uq_documents_storage_key" in error_text or (
            "documents.storage_key" in error_text and "unique" in error_text
        ):
            return ConflictError(f"Document with storage key '{data.storage_key}' already exists.")

        if "documents.project_id" in error_text or "fk_documents_project_id_projects" in error_text:
            msg = f"Project with id '{data.project_id}' was not found."
            return ProjectNotFoundError(msg)

        if "documents.uploaded_by" in error_text or "fk_documents_uploaded_by_users" in error_text:
            msg = f"User with id '{data.uploaded_by}' was not found."
            return UserNotFoundError(msg)

        return RepositoryError("Failed to persist document due to database conflict.")

    @staticmethod
    def _map_update_integrity_error(err: IntegrityError) -> RepositoryError:
        error_text = str(err.orig).lower()
        if "uq_documents_storage_key" in error_text or (
            "documents.storage_key" in error_text and "unique" in error_text
        ):
            return ConflictError("Document with the same storage key already exists.")

        return RepositoryError("Failed to update document due to database conflict.")

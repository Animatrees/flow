from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.schemas.document import DocumentCreateStored, DocumentRead, DocumentUpdate
from app.schemas.type_ids import DocumentId, ProjectId
from app.services import AbstractDocumentRepository


def build_document_read(
    *,
    document_id: UUID,
    data: DocumentCreateStored,
    created_at: datetime | None = None,
) -> DocumentRead:
    return DocumentRead(
        id=DocumentId(document_id),
        project_id=data.project_id,
        uploaded_by=data.uploaded_by,
        filename=data.filename,
        content_type=data.content_type,
        size_bytes=data.size_bytes,
        storage_key=data.storage_key,
        checksum=data.checksum,
        created_at=created_at or datetime.now(UTC),
    )


class InMemoryDocumentRepository(AbstractDocumentRepository):
    def __init__(
        self,
        documents: Iterable[DocumentRead] | None = None,
        id_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self.documents: dict[UUID, DocumentRead] = {
            document.id: document for document in (documents or [])
        }
        self.id_factory = id_factory or uuid4
        self.create_error: Exception | None = None
        self.update_error: Exception | None = None

    async def get_by_id(self, id_: UUID) -> DocumentRead | None:
        return self.documents.get(id_)

    async def get_all(self) -> Sequence[DocumentRead]:
        return list(self.documents.values())

    async def get_all_for_project(self, project_id: ProjectId) -> Sequence[DocumentRead]:
        return [
            document for document in self.documents.values() if document.project_id == project_id
        ]

    async def create(self, data: DocumentCreateStored) -> DocumentRead:
        if self.create_error is not None:
            raise self.create_error

        created_document = build_document_read(document_id=self.id_factory(), data=data)
        self.documents[created_document.id] = created_document
        return created_document

    async def update(self, id_: UUID, data: DocumentUpdate) -> DocumentRead | None:
        if self.update_error is not None:
            raise self.update_error

        document = self.documents.get(id_)
        if document is None:
            return None

        updated_document = document.model_copy(update=data.model_dump(exclude_unset=True))
        self.documents[id_] = updated_document
        return updated_document

    async def delete(self, id_: UUID) -> bool:
        deleted_document = self.documents.pop(id_, None)
        return deleted_document is not None

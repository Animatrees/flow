from abc import abstractmethod
from collections.abc import Sequence

from app.domain.repositories.base_repository import AbstractRepository
from app.domain.schemas.document import DocumentCreateStored, DocumentUpdate, StoredDocument
from app.domain.schemas.type_ids import DocumentId, ProjectId


class AbstractDocumentRepository(
    AbstractRepository[DocumentId, DocumentCreateStored, StoredDocument, DocumentUpdate]
):
    @abstractmethod
    async def get_all_for_project(self, project_id: ProjectId) -> Sequence[StoredDocument]:
        """Return all documents that belong to the given project."""

from abc import abstractmethod
from collections.abc import Sequence

from app.domain.repositories.base_repository import AbstractRepository
from app.domain.schemas.document import DocumentCreateStored, DocumentUpdate, StoredDocument
from app.domain.schemas.type_ids import DocumentId, ProjectId


class AbstractDocumentRepository(
    AbstractRepository[DocumentId, DocumentCreateStored, StoredDocument, DocumentUpdate]
):
    """Repository contract for stored document metadata.

    Supports:
        - document CRUD operations
        - project-scoped document reads
    """

    @abstractmethod
    async def get_all_for_project(self, project_id: ProjectId) -> Sequence[StoredDocument]:
        """Return all documents for a project."""

from abc import abstractmethod
from collections.abc import Sequence

from app.schemas.document import DocumentCreateStored, DocumentRead, DocumentUpdate
from app.schemas.type_ids import DocumentId, ProjectId
from app.services.repositories.base_repository import AbstractRepository


class AbstractDocumentRepository(
    AbstractRepository[DocumentId, DocumentCreateStored, DocumentRead, DocumentUpdate]
):
    @abstractmethod
    async def get_all_for_project(self, project_id: ProjectId) -> Sequence[DocumentRead]:
        """Return all documents that belong to the given project."""

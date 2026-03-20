from abc import abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.schemas.project import (
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
)
from app.services.base_repository import AbstractRepository

type ProjectId = UUID


class AbstractProjectRepository(
    AbstractRepository[ProjectId, ProjectCreateWithOwner, ProjectRead, ProjectUpdate]
):
    @abstractmethod
    async def get_all_for_user(self, user_id: UUID) -> Sequence[ProjectRead]:
        """Return all projects accessible to the given user."""

    @abstractmethod
    async def is_member(self, project_id: ProjectId, user_id: UUID) -> bool:
        """Return whether the user is a participant of the given project."""

    @abstractmethod
    async def add_member(self, project_id: ProjectId, user_id: UUID) -> ProjectMemberRead:
        """Add a participant to the given project."""

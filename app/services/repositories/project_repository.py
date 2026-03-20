from abc import abstractmethod
from collections.abc import Sequence

from app.schemas.project import (
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
)
from app.schemas.type_ids import ProjectId, UserId
from app.services.repositories.base_repository import AbstractRepository


class AbstractProjectRepository(
    AbstractRepository[ProjectId, ProjectCreateWithOwner, ProjectRead, ProjectUpdate]
):
    @abstractmethod
    async def get_all_for_user(self, user_id: UserId) -> Sequence[ProjectRead]:
        """Return all projects accessible to the given user."""

    @abstractmethod
    async def is_member(self, project_id: ProjectId, user_id: UserId) -> bool:
        """Return whether the user is a participant of the given project."""

    @abstractmethod
    async def add_member(self, project_id: ProjectId, user_id: UserId) -> ProjectMemberRead:
        """Add a participant to the given project."""

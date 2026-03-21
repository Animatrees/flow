from abc import abstractmethod
from collections.abc import Sequence

from app.domain.repositories.base_repository import AbstractRepository
from app.domain.schemas import (
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
)
from app.domain.schemas.type_ids import ProjectId, UserId


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

    @abstractmethod
    async def delete_all_owned_by_user(self, user_id: UserId) -> None:
        """Delete all projects owned by the given user."""

    @abstractmethod
    async def remove_memberships_for_user(self, user_id: UserId) -> None:
        """Remove the user from all project memberships."""

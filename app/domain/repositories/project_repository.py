from abc import abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.repositories.base_repository import AbstractRepository
from app.domain.schemas import (
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectMemberRole,
    ProjectRead,
    ProjectUpdate,
)
from app.domain.schemas.type_ids import ProjectId, UserId


@dataclass(frozen=True, slots=True)
class ProjectWithUserRole:
    """Data object for a project paired with a user's membership role."""

    project: ProjectRead
    role: ProjectMemberRole | None


class AbstractProjectRepository(
    AbstractRepository[ProjectId, ProjectCreateWithOwner, ProjectRead, ProjectUpdate]
):
    """Repository contract for projects and project memberships.

    Supports:
        - project CRUD operations
        - project reads scoped to a user
        - membership reads and writes
        - membership cleanup for account deletion
    """

    @abstractmethod
    async def get_project_with_user_role(
        self,
        project_id: ProjectId,
        user_id: UserId,
    ) -> ProjectWithUserRole | None:
        """Return a project paired with the user's membership role, or `None` if it does not exist."""

    @abstractmethod
    async def get_all_for_user(self, user_id: UserId) -> Sequence[ProjectRead]:
        """Return all projects accessible to a user."""

    @abstractmethod
    async def has_access_to_project(self, project_id: ProjectId, user_id: UserId) -> bool:
        """Return whether a user has access to a project."""

    @abstractmethod
    async def get_members(self, project_id: ProjectId) -> Sequence[ProjectMemberRead]:
        """Return all membership records for a project."""

    @abstractmethod
    async def add_member(self, project_id: ProjectId, user_id: UserId) -> ProjectMemberRead:
        """Add a non-owner member to a project."""

    @abstractmethod
    async def delete_all_owned_by_user(self, user_id: UserId) -> None:
        """Delete all projects owned by a user."""

    @abstractmethod
    async def remove_memberships_for_user(self, user_id: UserId) -> None:
        """Remove a user from all project memberships."""

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
    project: ProjectRead
    role: ProjectMemberRole | None


class AbstractProjectRepository(
    AbstractRepository[ProjectId, ProjectCreateWithOwner, ProjectRead, ProjectUpdate]
):
    @abstractmethod
    async def get_project_with_user_role(
        self,
        project_id: ProjectId,
        user_id: UserId,
    ) -> ProjectWithUserRole | None:
        """Return the project with the user's membership role, if the project exists."""

    @abstractmethod
    async def get_all_for_user(self, user_id: UserId) -> Sequence[ProjectRead]:
        """Return all projects accessible to the given user."""

    @abstractmethod
    async def has_access_to_project(self, project_id: ProjectId, user_id: UserId) -> bool:
        """Return whether the user has project access via a membership row."""

    @abstractmethod
    async def get_members(self, project_id: ProjectId) -> Sequence[ProjectMemberRead]:
        """Return all project memberships for the given project."""

    @abstractmethod
    async def add_member(self, project_id: ProjectId, user_id: UserId) -> ProjectMemberRead:
        """Add a non-owner member to the given project."""

    @abstractmethod
    async def delete_all_owned_by_user(self, user_id: UserId) -> None:
        """Delete all projects owned by the given user."""

    @abstractmethod
    async def remove_memberships_for_user(self, user_id: UserId) -> None:
        """Remove the user from all project memberships."""

from collections.abc import Sequence
from datetime import date

from app.domain.repositories.project_repository import (
    AbstractProjectRepository,
    ProjectWithUserRole,
)
from app.domain.repositories.user_repository import AbstractUserRepository
from app.domain.schemas import (
    ProjectCreate,
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectMemberRole,
    ProjectRead,
    ProjectUpdate,
)
from app.domain.schemas.type_ids import ProjectId, UserId
from app.domain.schemas.user import UserAuthRead
from app.services.exceptions import (
    ConflictError,
    InvalidProjectDatesError,
    PermissionDeniedError,
    ProjectAccessDeniedError,
    ProjectMemberAlreadyExistsError,
    ProjectNotFoundError,
    UserNotFoundError,
)


class ProjectService:
    """Service for project lifecycle operations and membership checks.

    Handles:
        - project creation, reads, updates, and deletion
        - membership listing
        - owner-only member management
        - date-range validation and access checks
    """

    def __init__(
        self,
        repo: AbstractProjectRepository,
        user_repo: AbstractUserRepository,
    ) -> None:
        self.repo = repo
        self.user_repo = user_repo

    async def create(self, owner: UserAuthRead, data: ProjectCreate) -> ProjectRead:
        self._validate_date_range(
            start_date=data.start_date,
            end_date=data.end_date,
        )
        return await self.repo.create(
            ProjectCreateWithOwner(
                owner_id=owner.id,
                **data.model_dump(),
            )
        )

    async def get_by_id(self, current_user: UserAuthRead, project_id: ProjectId) -> ProjectRead:
        project_with_user_role = await self._require_project_with_user_role(
            project_id,
            current_user.id,
        )
        if project_with_user_role.role is None:
            raise ProjectAccessDeniedError
        return project_with_user_role.project

    async def get_all_for_user(self, current_user: UserAuthRead) -> Sequence[ProjectRead]:
        return await self.repo.get_all_for_user(current_user.id)

    async def get_members(
        self,
        current_user: UserAuthRead,
        project_id: ProjectId,
    ) -> Sequence[ProjectMemberRead]:
        project_with_user_role = await self._require_project_with_user_role(
            project_id,
            current_user.id,
        )
        if project_with_user_role.role is None:
            raise ProjectAccessDeniedError
        return await self.repo.get_members(project_id)

    async def update(
        self,
        current_user: UserAuthRead,
        project_id: ProjectId,
        data: ProjectUpdate,
    ) -> ProjectRead:
        project_with_user_role = await self._require_project_with_user_role(
            project_id,
            current_user.id,
        )
        if project_with_user_role.role is None:
            raise ProjectAccessDeniedError
        project = project_with_user_role.project
        self._validate_date_range(
            start_date=data.start_date or project.start_date,
            end_date=data.end_date or project.end_date,
        )

        updated_project = await self.repo.update(project_id, data)
        if updated_project is None:
            msg = f"Project with id '{project_id}' was not found."
            raise ProjectNotFoundError(msg)
        return updated_project

    async def delete(self, current_user: UserAuthRead, project_id: ProjectId) -> None:
        project_with_user_role = await self._require_project_with_user_role(
            project_id,
            current_user.id,
        )
        if project_with_user_role.role is None:
            raise ProjectAccessDeniedError
        if project_with_user_role.role is not ProjectMemberRole.OWNER:
            raise PermissionDeniedError

        success = await self.repo.delete(project_id)
        if not success:
            msg = f"Project with id '{project_id}' was not found."
            raise ProjectNotFoundError(msg)

    async def add_member(
        self,
        current_user: UserAuthRead,
        project_id: ProjectId,
        user_id: UserId,
    ) -> ProjectMemberRead:
        project_with_user_role = await self._require_project_with_user_role(
            project_id,
            current_user.id,
        )
        if project_with_user_role.role is None:
            raise ProjectAccessDeniedError
        if project_with_user_role.role is not ProjectMemberRole.OWNER:
            raise PermissionDeniedError

        if await self.user_repo.get_active_by_id(user_id) is None:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)

        try:
            return await self.repo.add_member(project_id, user_id)
        except ConflictError as err:
            raise ProjectMemberAlreadyExistsError(str(err)) from err

    async def _require_project_with_user_role(
        self,
        project_id: ProjectId,
        user_id: UserId,
    ) -> ProjectWithUserRole:
        project_with_user_role = await self.repo.get_project_with_user_role(
            project_id,
            user_id,
        )
        if project_with_user_role is None:
            msg = f"Project with id '{project_id}' was not found."
            raise ProjectNotFoundError(msg)
        return project_with_user_role

    @staticmethod
    def _validate_date_range(*, start_date: date, end_date: date) -> None:
        if end_date < start_date:
            raise InvalidProjectDatesError

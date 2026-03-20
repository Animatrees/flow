from collections.abc import Sequence
from datetime import date

from app.schemas.project import (
    ProjectCreate,
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
)
from app.schemas.type_ids import ProjectId, UserId
from app.schemas.user import UserRead
from app.services.exceptions import (
    ConflictError,
    InvalidProjectDatesError,
    PermissionDeniedError,
    ProjectAccessDeniedError,
    ProjectMemberAlreadyExistsError,
    ProjectNotFoundError,
)
from app.services.repositories.project_repository import AbstractProjectRepository


class ProjectService:
    def __init__(self, repo: AbstractProjectRepository) -> None:
        self.repo = repo

    async def create(self, owner: UserRead, data: ProjectCreate) -> ProjectRead:
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

    async def get_by_id(self, current_user: UserRead, project_id: ProjectId) -> ProjectRead:
        project = await self._get_project(project_id)
        await self._ensure_project_access(current_user, project)
        return project

    async def get_all_for_user(self, current_user: UserRead) -> Sequence[ProjectRead]:
        return await self.repo.get_all_for_user(current_user.id)

    async def get_all(self) -> Sequence[ProjectRead]:
        return await self.repo.get_all()

    async def update(
        self,
        current_user: UserRead,
        project_id: ProjectId,
        data: ProjectUpdate,
    ) -> ProjectRead:
        project = await self._get_project(project_id)
        await self._ensure_project_access(current_user, project)
        self._validate_date_range(
            start_date=data.start_date or project.start_date,
            end_date=data.end_date or project.end_date,
        )

        updated_project = await self.repo.update(project_id, data)
        if updated_project is None:
            msg = f"Project with id '{project_id}' was not found."
            raise ProjectNotFoundError(msg)
        return updated_project

    async def delete(self, current_user: UserRead, project_id: ProjectId) -> None:
        project = await self._get_project(project_id)
        await self._ensure_owner_access(current_user, project)

        success = await self.repo.delete(project_id)
        if not success:
            msg = f"Project with id '{project_id}' was not found."
            raise ProjectNotFoundError(msg)

    async def add_member(
        self,
        current_user: UserRead,
        project_id: ProjectId,
        user_id: UserId,
    ) -> ProjectMemberRead:
        project = await self._get_project(project_id)
        await self._ensure_owner_access(current_user, project)

        if user_id == project.owner_id:
            raise ProjectMemberAlreadyExistsError

        try:
            return await self.repo.add_member(project_id, user_id)
        except ConflictError as err:
            raise ProjectMemberAlreadyExistsError(str(err)) from err

    async def _get_project(self, project_id: ProjectId) -> ProjectRead:
        project = await self.repo.get_by_id(project_id)
        if project is None:
            msg = f"Project with id '{project_id}' was not found."
            raise ProjectNotFoundError(msg)
        return project

    async def _ensure_project_access(
        self,
        current_user: UserRead,
        project: ProjectRead,
    ) -> None:
        if current_user.id == project.owner_id:
            return

        if await self.repo.is_member(project.id, current_user.id):
            return

        raise ProjectAccessDeniedError

    async def _ensure_owner_access(
        self,
        current_user: UserRead,
        project: ProjectRead,
    ) -> None:
        if current_user.id == project.owner_id:
            return

        if await self.repo.is_member(project.id, current_user.id):
            raise PermissionDeniedError

        raise ProjectAccessDeniedError

    @staticmethod
    def _validate_date_range(*, start_date: date, end_date: date) -> None:
        if end_date < start_date:
            raise InvalidProjectDatesError

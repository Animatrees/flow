from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Project, ProjectMember
from app.db.repositories.exceptions import (
    ConflictError,
    ProjectNotFoundError,
    RepositoryError,
    UserNotFoundError,
)
from app.domain.repositories.project_repository import AbstractProjectRepository
from app.domain.schemas import (
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectMemberRole,
    ProjectRead,
    ProjectUpdate,
)
from app.domain.schemas.type_ids import ProjectId, UserId


class ProjectRepository(AbstractProjectRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id_: ProjectId) -> ProjectRead | None:
        project = await self.session.get(Project, id_)
        return ProjectRead.model_validate(project) if project is not None else None

    async def get_all(self) -> Sequence[ProjectRead]:
        statement = select(Project).order_by(Project.created_at, Project.id)
        projects = await self.session.scalars(statement)
        return [ProjectRead.model_validate(project) for project in projects]

    async def create(self, data: ProjectCreateWithOwner) -> ProjectRead:
        project = Project(**data.model_dump())
        self.session.add(project)

        try:
            await self.session.flush()
        except IntegrityError as err:
            raise self._map_project_integrity_error(err) from err

        owner_membership = ProjectMember(
            project_id=project.id,
            user_id=project.owner_id,
            role=ProjectMemberRole.OWNER,
        )
        self.session.add(owner_membership)

        try:
            await self.session.flush()
        except IntegrityError as err:
            raise self._map_member_integrity_error(
                err,
                ProjectId(project.id),
                UserId(project.owner_id),
            ) from err

        return ProjectRead.model_validate(project)

    async def update(self, id_: ProjectId, data: ProjectUpdate) -> ProjectRead | None:
        project = await self.session.get(Project, id_)
        if project is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)

        try:
            await self.session.flush()
        except IntegrityError as err:
            raise self._map_project_integrity_error(err) from err

        return ProjectRead.model_validate(project)

    async def delete(self, id_: ProjectId) -> bool:
        project = await self.session.get(Project, id_)
        if project is None:
            return False

        await self.session.delete(project)
        await self.session.flush()
        return True

    async def get_all_for_user(self, user_id: UserId) -> Sequence[ProjectRead]:
        statement = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
            .order_by(Project.created_at, Project.id)
        )
        projects = await self.session.scalars(statement)
        return [ProjectRead.model_validate(project) for project in projects]

    async def has_access_to_project(self, project_id: ProjectId, user_id: UserId) -> bool:
        statement = select(ProjectMember.project_id).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        return await self.session.scalar(statement) is not None

    async def get_members(self, project_id: ProjectId) -> Sequence[ProjectMemberRead]:
        memberships = await self.session.scalars(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.role, ProjectMember.user_id)
        )
        return [ProjectMemberRead.model_validate(member) for member in memberships]

    async def add_member(self, project_id: ProjectId, user_id: UserId) -> ProjectMemberRead:
        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=ProjectMemberRole.MEMBER,
        )
        self.session.add(member)

        try:
            await self.session.flush()
        except IntegrityError as err:
            raise self._map_member_integrity_error(err, project_id, user_id) from err

        return ProjectMemberRead.model_validate(member)

    async def delete_all_owned_by_user(self, user_id: UserId) -> None:
        project_ids = list(
            await self.session.scalars(select(Project.id).where(Project.owner_id == user_id))
        )
        if not project_ids:
            return

        await self.session.execute(
            delete(ProjectMember).where(ProjectMember.project_id.in_(project_ids))
        )
        await self.session.execute(delete(Project).where(Project.id.in_(project_ids)))
        await self.session.flush()

    async def remove_memberships_for_user(self, user_id: UserId) -> None:
        await self.session.execute(delete(ProjectMember).where(ProjectMember.user_id == user_id))
        await self.session.flush()

    @staticmethod
    def _map_project_integrity_error(err: IntegrityError) -> RepositoryError:
        error_text = str(err.orig).lower()
        if "end_date" in error_text and "start_date" in error_text:
            return RepositoryError("Failed to persist project due to invalid project dates.")

        return RepositoryError("Failed to persist project due to database conflict.")

    @staticmethod
    def _map_member_integrity_error(
        err: IntegrityError,
        project_id: ProjectId,
        user_id: UserId,
    ) -> RepositoryError:
        error_text = str(err.orig).lower()

        if "project_members" in error_text and "unique" in error_text:
            return ConflictError("User is already a member of this project.")

        if (
            "project_members.project_id" in error_text
            or "fk_project_members_project_id_projects" in error_text
            or "foreign key constraint failed" in error_text
        ):
            msg = f"Project with id '{project_id}' was not found."
            return ProjectNotFoundError(msg)

        if (
            "project_members.user_id" in error_text
            or "fk_project_members_user_id_users" in error_text
        ):
            msg = f"User with id '{user_id}' was not found."
            return UserNotFoundError(msg)

        return RepositoryError("Failed to persist project member due to database conflict.")

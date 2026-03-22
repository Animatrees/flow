from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.repositories.project_repository import ProjectWithUserRole
from app.domain.schemas import (
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectMemberRole,
    ProjectRead,
    ProjectUpdate,
)
from app.domain.schemas.type_ids import ProjectId, UserId
from app.services import AbstractProjectRepository, ConflictError


def build_project_read(
    *,
    project_id: UUID,
    data: ProjectCreateWithOwner,
    created_at: datetime | None = None,
) -> ProjectRead:
    return ProjectRead(
        id=ProjectId(project_id),
        name=data.name,
        description=data.description,
        owner_id=data.owner_id,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
        created_at=created_at or datetime.now(UTC),
    )


class InMemoryProjectRepository(AbstractProjectRepository):
    def __init__(
        self,
        projects: Iterable[ProjectRead] | None = None,
        members: Iterable[ProjectMemberRead] | None = None,
        id_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self.projects: dict[UUID, ProjectRead] = {
            project.id: project for project in (projects or [])
        }
        self.members: dict[UUID, dict[UUID, ProjectMemberRole]] = {}
        for project in self.projects.values():
            self.members.setdefault(project.id, {})[project.owner_id] = ProjectMemberRole.OWNER
        for member in members or []:
            self.members.setdefault(member.project_id, {})[member.user_id] = member.role

        self.id_factory = id_factory or uuid4
        self.add_member_error: Exception | None = None

    async def get_by_id(self, id_: UUID) -> ProjectRead | None:
        return self.projects.get(id_)

    async def get_project_with_user_role(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> ProjectWithUserRole | None:
        project = self.projects.get(project_id)
        if project is None:
            return None

        return ProjectWithUserRole(
            project=project,
            role=self.members.get(project_id, {}).get(user_id),
        )

    async def get_all(self) -> Sequence[ProjectRead]:
        return list(self.projects.values())

    async def create(self, data: ProjectCreateWithOwner) -> ProjectRead:
        created_project = ProjectRead(
            id=ProjectId(self.id_factory()),
            name=data.name,
            description=data.description,
            owner_id=data.owner_id,
            start_date=data.start_date,
            end_date=data.end_date,
            status=data.status,
            created_at=datetime.now(UTC),
        )
        self.projects[created_project.id] = created_project
        self.members.setdefault(created_project.id, {})[created_project.owner_id] = (
            ProjectMemberRole.OWNER
        )
        return created_project

    async def update(self, id_: UUID, data: ProjectUpdate) -> ProjectRead | None:
        project = self.projects.get(id_)
        if project is None:
            return None

        updated_project = project.model_copy(update=data.model_dump(exclude_unset=True))
        self.projects[id_] = updated_project
        return updated_project

    async def delete(self, id_: UUID) -> bool:
        project = self.projects.pop(id_, None)
        self.members.pop(id_, None)
        return project is not None

    async def get_all_for_user(self, user_id: UUID) -> Sequence[ProjectRead]:
        return [
            project
            for project in self.projects.values()
            if user_id in self.members.get(project.id, {})
        ]

    async def get_members(self, project_id: UUID) -> Sequence[ProjectMemberRead]:
        return [
            ProjectMemberRead(
                project_id=ProjectId(project_id),
                user_id=UserId(user_id),
                role=role,
            )
            for user_id, role in sorted(
                self.members.get(project_id, {}).items(),
                key=lambda item: (item[1].value, item[0]),
            )
        ]

    async def has_access_to_project(self, project_id: UUID, user_id: UUID) -> bool:
        return user_id in self.members.get(project_id, {})

    async def add_member(self, project_id: UUID, user_id: UUID) -> ProjectMemberRead:
        if self.add_member_error is not None:
            raise self.add_member_error

        project_members = self.members.setdefault(project_id, {})
        if user_id in project_members:
            msg = "User is already a member of this project."
            raise ConflictError(msg)

        project_members[user_id] = ProjectMemberRole.MEMBER
        return ProjectMemberRead(
            project_id=ProjectId(project_id),
            user_id=UserId(user_id),
            role=ProjectMemberRole.MEMBER,
        )

    async def delete_all_owned_by_user(self, user_id: UserId) -> None:
        owned_project_ids = [
            project_id
            for project_id, project in self.projects.items()
            if project.owner_id == user_id
        ]
        for project_id in owned_project_ids:
            self.projects.pop(project_id, None)
            self.members.pop(project_id, None)

    async def remove_memberships_for_user(self, user_id: UserId) -> None:
        for members in self.members.values():
            if user_id in members:
                members.pop(user_id)

from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.schemas.project import (
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
)
from app.services import AbstractProjectRepository, ConflictError


def build_project_read(
    *,
    project_id: UUID,
    data: ProjectCreateWithOwner,
    created_at: datetime | None = None,
) -> ProjectRead:
    return ProjectRead(
        id=project_id,
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
        self.members: dict[UUID, set[UUID]] = {}
        for member in members or []:
            self.members.setdefault(member.project_id, set()).add(member.user_id)

        self.id_factory = id_factory or uuid4
        self.add_member_error: Exception | None = None

    async def get_by_id(self, id_: UUID) -> ProjectRead | None:
        return self.projects.get(id_)

    async def get_all(self) -> Sequence[ProjectRead]:
        return list(self.projects.values())

    async def create(self, data: ProjectCreateWithOwner) -> ProjectRead:
        created_project = ProjectRead(
            id=self.id_factory(),
            name=data.name,
            description=data.description,
            owner_id=data.owner_id,
            start_date=data.start_date,
            end_date=data.end_date,
            status=data.status,
            created_at=datetime.now(UTC),
        )
        self.projects[created_project.id] = created_project
        self.members.setdefault(created_project.id, set())
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
            if project.owner_id == user_id or user_id in self.members.get(project.id, set())
        ]

    async def get_members(self, project_id: UUID) -> Sequence[ProjectMemberRead]:
        return [
            ProjectMemberRead(project_id=project_id, user_id=user_id)
            for user_id in self.members.get(project_id, set())
        ]

    async def is_member(self, project_id: UUID, user_id: UUID) -> bool:
        return user_id in self.members.get(project_id, set())

    async def add_member(self, project_id: UUID, user_id: UUID) -> ProjectMemberRead:
        if self.add_member_error is not None:
            raise self.add_member_error

        project_members = self.members.setdefault(project_id, set())
        if user_id in project_members:
            msg = "User is already a participant of this project."
            raise ConflictError(msg)

        project_members.add(user_id)
        return ProjectMemberRead(project_id=project_id, user_id=user_id)

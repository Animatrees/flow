import re
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from app.schemas import (
    ProjectCreate,
    ProjectMemberRead,
    ProjectRead,
    ProjectStatus,
    ProjectUpdate,
    UserRead,
)
from app.schemas.project import ProjectCreateWithOwner, ProjectId, UserId
from app.services import (
    ConflictError,
    InvalidProjectDatesError,
    PermissionDeniedError,
    ProjectAccessDeniedError,
    ProjectMemberAlreadyExistsError,
    ProjectNotFoundError,
    ProjectService,
)
from tests.unit.fakes.project_repository import InMemoryProjectRepository, build_project_read

OWNER_ID = UserId(UUID("11111111-1111-1111-1111-111111111111"))
PARTICIPANT_ID = UserId(UUID("22222222-2222-2222-2222-222222222222"))
OUTSIDER_ID = UserId(UUID("33333333-3333-3333-3333-333333333333"))
SECOND_OWNER_ID = UserId(UUID("44444444-4444-4444-4444-444444444444"))
PROJECT_ID = ProjectId(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
SECOND_PROJECT_ID = ProjectId(UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))
MISSING_PROJECT_ID = ProjectId(UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"))
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def build_user(user_id: UUID, username: str, email: str) -> UserRead:
    return UserRead(
        id=UserId(user_id),
        username=username,
        email=email,
        created_at=CREATED_AT,
    )


@pytest.fixture
def owner() -> UserRead:
    return build_user(OWNER_ID, "owner", "owner@example.com")


@pytest.fixture
def participant() -> UserRead:
    return build_user(PARTICIPANT_ID, "participant", "participant@example.com")


@pytest.fixture
def outsider() -> UserRead:
    return build_user(OUTSIDER_ID, "outsider", "outsider@example.com")


@pytest.fixture
def second_owner() -> UserRead:
    return build_user(SECOND_OWNER_ID, "second.owner", "second.owner@example.com")


@pytest.fixture
def existing_project() -> ProjectRead:
    return build_project_read(
        project_id=PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Flow",
            description="Educational backend",
            owner_id=UserId(OWNER_ID),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
        created_at=CREATED_AT,
    )


@pytest.fixture
def second_project() -> ProjectRead:
    return build_project_read(
        project_id=SECOND_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Second Flow",
            description="",
            owner_id=UserId(SECOND_OWNER_ID),
            start_date=date(2026, 2, 1),
            end_date=date(2026, 10, 1),
            status=ProjectStatus.WIP,
        ),
        created_at=CREATED_AT,
    )


@pytest.fixture
def project_repository(
    existing_project: ProjectRead,
    second_project: ProjectRead,
) -> InMemoryProjectRepository:
    return InMemoryProjectRepository(
        projects=[existing_project, second_project],
        members=[
            ProjectMemberRead(project_id=ProjectId(PROJECT_ID), user_id=UserId(PARTICIPANT_ID)),
        ],
        id_factory=lambda: UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
    )


@pytest.fixture
def project_service(project_repository: InMemoryProjectRepository) -> ProjectService:
    return ProjectService(project_repository)


@pytest.mark.anyio
async def test_project_service_create_returns_created_project(
    project_service: ProjectService,
    owner: UserRead,
) -> None:
    project = await project_service.create(
        owner,
        ProjectCreate(
            name="New Flow",
            description="New educational backend",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 9, 1),
            status=ProjectStatus.OPEN,
        ),
    )

    assert project.id == UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
    assert project.owner_id == owner.id
    assert project.start_date == date(2026, 3, 1)
    assert project.end_date == date(2026, 9, 1)
    assert project.status == ProjectStatus.OPEN


@pytest.mark.anyio
async def test_project_service_create_raises_for_invalid_date_range(
    project_service: ProjectService,
    owner: UserRead,
) -> None:
    with pytest.raises(
        InvalidProjectDatesError,
        match=re.escape("Project end date must be greater than or equal to the start date."),
    ):
        await project_service.create(
            owner,
            ProjectCreate(
                name="New Flow",
                description="New educational backend",
                start_date=date(2026, 9, 1),
                end_date=date(2026, 3, 1),
                status=ProjectStatus.OPEN,
            ),
        )


@pytest.mark.anyio
async def test_project_service_get_by_id_returns_project_for_owner(
    project_service: ProjectService,
    owner: UserRead,
    existing_project: ProjectRead,
) -> None:
    project = await project_service.get_by_id(owner, existing_project.id)

    assert project == existing_project


@pytest.mark.anyio
async def test_project_service_get_by_id_returns_project_for_participant(
    project_service: ProjectService,
    participant: UserRead,
    existing_project: ProjectRead,
) -> None:
    project = await project_service.get_by_id(participant, existing_project.id)

    assert project == existing_project


@pytest.mark.anyio
async def test_project_service_get_by_id_raises_for_missing_project(
    project_service: ProjectService,
    owner: UserRead,
) -> None:
    with pytest.raises(
        ProjectNotFoundError,
        match=re.escape(f"Project with id '{MISSING_PROJECT_ID}' was not found."),
    ):
        await project_service.get_by_id(owner, MISSING_PROJECT_ID)


@pytest.mark.anyio
async def test_project_service_get_by_id_raises_for_outsider(
    project_service: ProjectService,
    outsider: UserRead,
    existing_project: ProjectRead,
) -> None:
    with pytest.raises(
        ProjectAccessDeniedError,
        match=re.escape("You do not have access to this project."),
    ):
        await project_service.get_by_id(outsider, existing_project.id)


@pytest.mark.anyio
async def test_project_service_get_all_for_user_returns_accessible_projects(
    project_service: ProjectService,
    owner: UserRead,
    existing_project: ProjectRead,
) -> None:
    projects = await project_service.get_all_for_user(owner)

    assert projects == [existing_project]


@pytest.mark.anyio
async def test_project_service_get_all_returns_all_projects(
    project_service: ProjectService,
    existing_project: ProjectRead,
    second_project: ProjectRead,
) -> None:
    projects = await project_service.get_all()

    assert projects == [existing_project, second_project]


@pytest.mark.anyio
async def test_project_service_update_returns_updated_project_for_owner(
    project_service: ProjectService,
    owner: UserRead,
    existing_project: ProjectRead,
) -> None:
    updated_project = await project_service.update(
        owner,
        existing_project.id,
        ProjectUpdate(
            name="Updated Flow",
            description="Updated description",
            end_date=date(2026, 11, 30),
            status=ProjectStatus.DONE,
        ),
    )

    assert updated_project.name == "Updated Flow"
    assert updated_project.description == "Updated description"
    assert updated_project.end_date == date(2026, 11, 30)
    assert updated_project.status == ProjectStatus.DONE


@pytest.mark.anyio
async def test_project_service_update_returns_updated_project_for_participant(
    project_service: ProjectService,
    participant: UserRead,
    existing_project: ProjectRead,
) -> None:
    updated_project = await project_service.update(
        participant,
        existing_project.id,
        ProjectUpdate(
            description="Participant update",
        ),
    )

    assert updated_project.description == "Participant update"


@pytest.mark.anyio
async def test_project_service_update_raises_for_outsider(
    project_service: ProjectService,
    outsider: UserRead,
    existing_project: ProjectRead,
) -> None:
    with pytest.raises(
        ProjectAccessDeniedError,
        match=re.escape("You do not have access to this project."),
    ):
        await project_service.update(
            outsider,
            existing_project.id,
            ProjectUpdate(
                name="Blocked update",
            ),
        )


@pytest.mark.anyio
async def test_project_service_update_raises_for_invalid_date_range(
    project_service: ProjectService,
    owner: UserRead,
    existing_project: ProjectRead,
) -> None:
    with pytest.raises(
        InvalidProjectDatesError,
        match=re.escape("Project end date must be greater than or equal to the start date."),
    ):
        await project_service.update(
            owner,
            existing_project.id,
            ProjectUpdate(end_date=date(2025, 12, 31)),
        )


@pytest.mark.anyio
async def test_project_service_delete_allows_owner(
    project_service: ProjectService,
    project_repository: InMemoryProjectRepository,
    owner: UserRead,
    existing_project: ProjectRead,
) -> None:
    await project_service.delete(owner, existing_project.id)

    assert existing_project.id not in project_repository.projects


@pytest.mark.anyio
async def test_project_service_delete_rejects_participant(
    project_service: ProjectService,
    participant: UserRead,
    existing_project: ProjectRead,
) -> None:
    with pytest.raises(
        PermissionDeniedError,
        match=re.escape("You do not have sufficient permissions to perform this action."),
    ):
        await project_service.delete(participant, existing_project.id)


@pytest.mark.anyio
async def test_project_service_delete_rejects_outsider(
    project_service: ProjectService,
    outsider: UserRead,
    existing_project: ProjectRead,
) -> None:
    with pytest.raises(
        ProjectAccessDeniedError,
        match=re.escape("You do not have access to this project."),
    ):
        await project_service.delete(outsider, existing_project.id)


@pytest.mark.anyio
async def test_project_service_add_member_allows_owner(
    project_service: ProjectService,
    owner: UserRead,
    existing_project: ProjectRead,
    outsider: UserRead,
) -> None:
    member = await project_service.add_member(owner, existing_project.id, outsider.id)

    assert member == ProjectMemberRead(project_id=existing_project.id, user_id=outsider.id)


@pytest.mark.anyio
async def test_project_service_add_member_rejects_participant(
    project_service: ProjectService,
    participant: UserRead,
    existing_project: ProjectRead,
    outsider: UserRead,
) -> None:
    with pytest.raises(
        PermissionDeniedError,
        match=re.escape("You do not have sufficient permissions to perform this action."),
    ):
        await project_service.add_member(participant, existing_project.id, outsider.id)


@pytest.mark.anyio
async def test_project_service_add_member_rejects_outsider(
    project_service: ProjectService,
    outsider: UserRead,
    existing_project: ProjectRead,
) -> None:
    with pytest.raises(
        ProjectAccessDeniedError,
        match=re.escape("You do not have access to this project."),
    ):
        await project_service.add_member(outsider, existing_project.id, UserId(UUID(int=1)))


@pytest.mark.anyio
async def test_project_service_add_member_raises_for_existing_participant(
    project_service: ProjectService,
    owner: UserRead,
    existing_project: ProjectRead,
    participant: UserRead,
) -> None:
    with pytest.raises(
        ProjectMemberAlreadyExistsError,
        match=re.escape("User is already a participant of this project."),
    ):
        await project_service.add_member(owner, existing_project.id, participant.id)


@pytest.mark.anyio
async def test_project_service_add_member_raises_for_owner(
    project_service: ProjectService,
    owner: UserRead,
    existing_project: ProjectRead,
) -> None:
    with pytest.raises(
        ProjectMemberAlreadyExistsError,
        match=re.escape("User is already a participant of this project."),
    ):
        await project_service.add_member(owner, existing_project.id, owner.id)


@pytest.mark.anyio
async def test_project_service_add_member_maps_repository_conflict(
    project_service: ProjectService,
    project_repository: InMemoryProjectRepository,
    owner: UserRead,
    existing_project: ProjectRead,
    outsider: UserRead,
) -> None:
    project_repository.add_member_error = ConflictError(
        "User is already a participant of this project."
    )

    with pytest.raises(
        ProjectMemberAlreadyExistsError,
        match=re.escape("User is already a participant of this project."),
    ):
        await project_service.add_member(owner, existing_project.id, outsider.id)

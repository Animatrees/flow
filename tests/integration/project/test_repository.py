import re
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Project, ProjectMember, User
from app.db.repositories import (
    ConflictError,
    ProjectRepository,
    RepositoryError,
)
from app.domain.schemas import (
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectMemberRole,
    ProjectStatus,
    ProjectUpdate,
    UserId,
)
from app.domain.schemas.type_ids import ProjectId

pytestmark = pytest.mark.anyio

OWNER_ID = UserId(UUID("11111111-1111-1111-1111-111111111111"))
PARTICIPANT_ID = UserId(UUID("22222222-2222-2222-2222-222222222222"))
OUTSIDER_ID = UserId(UUID("33333333-3333-3333-3333-333333333333"))
FIRST_PROJECT_ID = ProjectId(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
SECOND_PROJECT_ID = ProjectId(UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))
MISSING_PROJECT_ID = ProjectId(UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"))
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
LATER_CREATED_AT = datetime(2026, 2, 1, tzinfo=UTC)


async def seed_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    username: str,
    email: str,
) -> User:
    user = User(
        id=user_id,
        username=username,
        email=email,
        password_hash="hashed-password",
        is_active=True,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
        last_login_at=None,
        deleted_at=None,
    )
    session.add(user)
    await session.flush()
    return user


async def seed_project(
    session: AsyncSession,
    *,
    project_id: UUID,
    data: ProjectCreateWithOwner,
    created_at: datetime = CREATED_AT,
) -> Project:
    project = Project(
        id=project_id,
        **data.model_dump(),
        created_at=created_at,
    )
    session.add(project)
    await session.flush()
    session.add(
        ProjectMember(
            project_id=project_id,
            user_id=data.owner_id,
            role=ProjectMemberRole.OWNER,
        )
    )
    await session.flush()
    return project


async def seed_member(
    session: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID,
    role: ProjectMemberRole = ProjectMemberRole.MEMBER,
) -> ProjectMember:
    member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
    session.add(member)
    await session.flush()
    return member


@pytest.fixture
async def repository(db_session: AsyncSession) -> ProjectRepository:
    return ProjectRepository(db_session)


async def test_create_persists_project_and_returns_read_model(
    repository: ProjectRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )

    created_project = await repository.create(
        ProjectCreateWithOwner(
            name="Flow",
            description="Educational backend",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 1),
            status=ProjectStatus.OPEN,
        )
    )

    persisted_project = await repository.get_by_id(created_project.id)

    assert persisted_project == created_project
    assert created_project.owner_id == OWNER_ID
    assert created_project.status == ProjectStatus.OPEN
    assert await repository.has_access_to_project(created_project.id, OWNER_ID) is True
    assert await repository.get_members(created_project.id) == [
        ProjectMemberRead(
            project_id=created_project.id,
            user_id=OWNER_ID,
            role=ProjectMemberRole.OWNER,
        )
    ]


async def test_get_by_id_returns_none_for_missing_project(repository: ProjectRepository) -> None:
    project = await repository.get_by_id(MISSING_PROJECT_ID)

    assert project is None


async def test_get_all_returns_projects_sorted_by_created_at_then_id(
    repository: ProjectRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    first_project = await seed_project(
        db_session,
        project_id=FIRST_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Alpha",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
        created_at=CREATED_AT,
    )
    second_project = await seed_project(
        db_session,
        project_id=SECOND_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Beta",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
        created_at=LATER_CREATED_AT,
    )

    projects = await repository.get_all()

    assert [project.id for project in projects] == [first_project.id, second_project.id]


async def test_update_persists_changed_fields(
    repository: ProjectRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_project(
        db_session,
        project_id=FIRST_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Flow",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
    )

    updated_project = await repository.update(
        FIRST_PROJECT_ID,
        ProjectUpdate(
            name="Updated Flow",
            description="Updated description",
            end_date=date(2026, 10, 1),
            status=ProjectStatus.DONE,
        ),
    )

    assert updated_project is not None
    assert updated_project.name == "Updated Flow"
    assert updated_project.description == "Updated description"
    assert updated_project.end_date == date(2026, 10, 1)
    assert updated_project.status == ProjectStatus.DONE


async def test_update_returns_none_for_missing_project(repository: ProjectRepository) -> None:
    updated_project = await repository.update(
        MISSING_PROJECT_ID,
        ProjectUpdate(name="Updated Flow"),
    )

    assert updated_project is None


async def test_delete_removes_project(
    repository: ProjectRepository, db_session: AsyncSession
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_project(
        db_session,
        project_id=FIRST_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Flow",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
    )

    success = await repository.delete(FIRST_PROJECT_ID)

    assert success is True
    assert await repository.get_by_id(FIRST_PROJECT_ID) is None


async def test_delete_returns_false_for_missing_project(repository: ProjectRepository) -> None:
    success = await repository.delete(MISSING_PROJECT_ID)

    assert success is False


async def test_delete_all_owned_by_user_removes_owned_projects(
    repository: ProjectRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_project(
        db_session,
        project_id=FIRST_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="First",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
    )
    await seed_project(
        db_session,
        project_id=SECOND_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Second",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
    )

    await repository.delete_all_owned_by_user(OWNER_ID)
    assert await repository.get_by_id(FIRST_PROJECT_ID) is None
    assert await repository.get_by_id(SECOND_PROJECT_ID) is None


async def test_remove_memberships_for_user_removes_all_participations(
    repository: ProjectRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_user(
        db_session,
        user_id=PARTICIPANT_ID,
        username="participant",
        email="participant@example.com",
    )
    await seed_project(
        db_session,
        project_id=FIRST_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="First",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
    )
    await seed_project(
        db_session,
        project_id=SECOND_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Second",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
    )
    await seed_member(db_session, project_id=FIRST_PROJECT_ID, user_id=PARTICIPANT_ID)
    await seed_member(db_session, project_id=SECOND_PROJECT_ID, user_id=PARTICIPANT_ID)

    await repository.remove_memberships_for_user(PARTICIPANT_ID)
    assert await repository.has_access_to_project(FIRST_PROJECT_ID, PARTICIPANT_ID) is False
    assert await repository.has_access_to_project(SECOND_PROJECT_ID, PARTICIPANT_ID) is False


async def test_get_all_for_user_returns_owned_and_member_projects(
    repository: ProjectRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_user(
        db_session,
        user_id=PARTICIPANT_ID,
        username="participant",
        email="participant@example.com",
    )
    await seed_user(
        db_session,
        user_id=OUTSIDER_ID,
        username="outsider",
        email="outsider@example.com",
    )
    owned_project = await seed_project(
        db_session,
        project_id=FIRST_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Owned by participant",
            description="",
            owner_id=PARTICIPANT_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
        created_at=CREATED_AT,
    )
    member_project = await seed_project(
        db_session,
        project_id=SECOND_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Member project",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
        created_at=LATER_CREATED_AT,
    )
    await seed_member(
        db_session,
        project_id=SECOND_PROJECT_ID,
        user_id=PARTICIPANT_ID,
    )

    projects = await repository.get_all_for_user(PARTICIPANT_ID)

    assert [project.id for project in projects] == [owned_project.id, member_project.id]


async def test_has_access_to_project_returns_true_for_owner_and_member(
    repository: ProjectRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_user(
        db_session,
        user_id=PARTICIPANT_ID,
        username="participant",
        email="participant@example.com",
    )
    await seed_project(
        db_session,
        project_id=FIRST_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Flow",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
    )
    await seed_member(
        db_session,
        project_id=FIRST_PROJECT_ID,
        user_id=PARTICIPANT_ID,
    )

    assert await repository.has_access_to_project(FIRST_PROJECT_ID, PARTICIPANT_ID) is True
    assert await repository.has_access_to_project(FIRST_PROJECT_ID, OWNER_ID) is True


async def test_add_member_creates_membership(
    repository: ProjectRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_user(
        db_session,
        user_id=PARTICIPANT_ID,
        username="participant",
        email="participant@example.com",
    )
    await seed_project(
        db_session,
        project_id=FIRST_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Flow",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
    )

    member = await repository.add_member(FIRST_PROJECT_ID, PARTICIPANT_ID)

    assert member.project_id == FIRST_PROJECT_ID
    assert member.user_id == PARTICIPANT_ID
    assert member.role is ProjectMemberRole.MEMBER
    assert await repository.has_access_to_project(FIRST_PROJECT_ID, PARTICIPANT_ID) is True


async def test_add_member_raises_for_duplicate_membership(
    repository: ProjectRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_user(
        db_session,
        user_id=PARTICIPANT_ID,
        username="participant",
        email="participant@example.com",
    )
    await seed_project(
        db_session,
        project_id=FIRST_PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Flow",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
    )
    await seed_member(
        db_session,
        project_id=FIRST_PROJECT_ID,
        user_id=PARTICIPANT_ID,
    )

    with pytest.raises(
        ConflictError,
        match=re.escape("User is already a member of this project."),
    ):
        await repository.add_member(FIRST_PROJECT_ID, PARTICIPANT_ID)


async def test_get_members_returns_owner_and_members_with_roles(
    repository: ProjectRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_user(
        db_session,
        user_id=PARTICIPANT_ID,
        username="participant",
        email="participant@example.com",
    )
    created_project = await repository.create(
        ProjectCreateWithOwner(
            name="Flow",
            description="",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        )
    )
    await repository.add_member(created_project.id, PARTICIPANT_ID)

    members = await repository.get_members(created_project.id)

    assert members == [
        ProjectMemberRead(
            project_id=created_project.id,
            user_id=PARTICIPANT_ID,
            role=ProjectMemberRole.MEMBER,
        ),
        ProjectMemberRead(
            project_id=created_project.id,
            user_id=OWNER_ID,
            role=ProjectMemberRole.OWNER,
        ),
    ]


async def test_add_member_raises_for_missing_project(
    repository: ProjectRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=PARTICIPANT_ID,
        username="participant",
        email="participant@example.com",
    )

    with pytest.raises(RepositoryError):
        await repository.add_member(MISSING_PROJECT_ID, PARTICIPANT_ID)

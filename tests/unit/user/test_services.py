import re
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.schemas import ProjectId, UserAuthRead, UserCreate, UserId, UserUpdate
from app.domain.schemas.project import ProjectCreateWithOwner, ProjectMemberRead, ProjectStatus
from app.services import (
    EmailAlreadyExistsError,
    PermissionDeniedError,
    UserLifecycleService,
    UsernameAlreadyExistsError,
    UserNotFoundError,
    UserService,
)
from tests.unit.fakes.project_repository import (
    InMemoryProjectRepository,
    build_project_read,
)
from tests.unit.fakes.user_repository import (
    InMemoryUserRepository,
    to_user_read,
)
from tests.unit.fakes.user_repository import (
    build_user_auth_read as make_user_auth_read,
)

FIRST_USER_ID = UserId(UUID("11111111-1111-1111-1111-111111111111"))
SECOND_USER_ID = UserId(UUID("22222222-2222-2222-2222-222222222222"))
MISSING_USER_ID = UserId(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def existing_user() -> UserAuthRead:
    return make_user_auth_read(
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
        password_hash="hashed-password",
        created_at=CREATED_AT,
    )


@pytest.fixture
def second_user() -> UserAuthRead:
    return make_user_auth_read(
        user_id=SECOND_USER_ID,
        username="second.user",
        email="second@example.com",
        password_hash="hashed-password",
        created_at=CREATED_AT,
    )


@pytest.fixture
def user_repository(
    existing_user: UserAuthRead, second_user: UserAuthRead
) -> InMemoryUserRepository:
    return InMemoryUserRepository(
        users=[existing_user, second_user],
        id_factory=lambda: UUID("33333333-3333-3333-3333-333333333333"),
    )


@pytest.fixture
def user_service(user_repository: InMemoryUserRepository) -> UserService:
    return UserService(user_repository)


@pytest.fixture
def user_lifecycle_service(user_repository: InMemoryUserRepository) -> UserLifecycleService:
    return UserLifecycleService(user_repository, InMemoryProjectRepository())


@pytest.mark.anyio
async def test_user_service_create_returns_created_user(user_service: UserService) -> None:
    created_user = await user_service.create(
        UserCreate(
            username="new.user",
            email="new@example.com",
            password_hash="hashed-password",
        )
    )

    assert created_user.id == UUID("33333333-3333-3333-3333-333333333333")
    assert created_user.username == "new.user"
    assert created_user.email == "new@example.com"


@pytest.mark.anyio
async def test_user_service_create_propagates_username_conflict(
    user_service: UserService,
    user_repository: InMemoryUserRepository,
) -> None:
    user_repository.create_error = UsernameAlreadyExistsError()

    with pytest.raises(
        UsernameAlreadyExistsError,
        match=re.escape("Username is already taken."),
    ):
        await user_service.create(
            UserCreate(
                username="new.user",
                email="new@example.com",
                password_hash="hashed-password",
            )
        )


@pytest.mark.anyio
async def test_user_service_get_by_id_returns_user(
    user_service: UserService,
    existing_user: UserAuthRead,
) -> None:
    user = await user_service.get_by_id(existing_user.id)

    assert user == to_user_read(existing_user)


@pytest.mark.anyio
async def test_user_service_get_by_id_raises_for_missing_user(
    user_service: UserService,
) -> None:
    with pytest.raises(
        UserNotFoundError,
        match=re.escape(f"User with id '{MISSING_USER_ID}' was not found."),
    ):
        await user_service.get_by_id(UserId(MISSING_USER_ID))


@pytest.mark.anyio
async def test_user_service_get_by_username_returns_user(
    user_service: UserService,
    existing_user: UserAuthRead,
) -> None:
    user = await user_service.get_by_username(existing_user.username)

    assert user == to_user_read(existing_user)


@pytest.mark.anyio
async def test_user_service_get_by_username_raises_for_missing_user(
    user_service: UserService,
) -> None:
    with pytest.raises(
        UserNotFoundError,
        match=re.escape("User with username 'missing.user' was not found."),
    ):
        await user_service.get_by_username("missing.user")


@pytest.mark.anyio
async def test_user_service_get_auth_user_by_username_returns_auth_user(
    user_service: UserService,
    existing_user: UserAuthRead,
) -> None:
    auth_user = await user_service.get_auth_user_by_username(existing_user.username)

    assert auth_user == existing_user


@pytest.mark.anyio
async def test_user_service_get_all_returns_all_users(
    user_service: UserService,
    existing_user: UserAuthRead,
    second_user: UserAuthRead,
) -> None:
    users = await user_service.get_all()

    assert users == [to_user_read(existing_user), to_user_read(second_user)]


@pytest.mark.anyio
async def test_user_service_update_returns_updated_user(
    user_service: UserService,
    existing_user: UserAuthRead,
) -> None:
    updated_user = await user_service.update(
        to_user_read(existing_user),
        existing_user.id,
        UserUpdate(username="updated.user"),
    )

    assert updated_user.id == existing_user.id
    assert updated_user.username == "updated.user"
    assert updated_user.email == existing_user.email


@pytest.mark.anyio
async def test_user_service_update_propagates_email_conflict(
    user_service: UserService,
    user_repository: InMemoryUserRepository,
    existing_user: UserAuthRead,
) -> None:
    user_repository.update_error = EmailAlreadyExistsError()

    with pytest.raises(
        EmailAlreadyExistsError,
        match=re.escape("Email is already taken."),
    ):
        await user_service.update(
            to_user_read(existing_user),
            existing_user.id,
            UserUpdate(email="updated@example.com"),
        )


@pytest.mark.anyio
async def test_user_service_update_raises_for_missing_user(
    user_service: UserService,
) -> None:
    missing_current_user = to_user_read(
        make_user_auth_read(
            user_id=MISSING_USER_ID,
            username="missing.user",
            email="missing@example.com",
            password_hash="hashed-password",
            created_at=CREATED_AT,
        )
    )

    with pytest.raises(
        UserNotFoundError,
        match=re.escape(f"User with id '{MISSING_USER_ID}' was not found."),
    ):
        await user_service.update(
            missing_current_user,
            MISSING_USER_ID,
            UserUpdate(username="updated.user"),
        )


@pytest.mark.anyio
async def test_user_service_update_raises_for_other_user(
    user_service: UserService,
    existing_user: UserAuthRead,
    second_user: UserAuthRead,
) -> None:
    with pytest.raises(
        PermissionDeniedError,
        match=re.escape("You do not have sufficient permissions to perform this action."),
    ):
        await user_service.update(
            to_user_read(existing_user),
            second_user.id,
            UserUpdate(username="updated.user"),
        )


@pytest.mark.anyio
async def test_user_lifecycle_service_delete_account_removes_existing_user(
    user_lifecycle_service: UserLifecycleService,
    user_repository: InMemoryUserRepository,
    existing_user: UserAuthRead,
) -> None:
    result = await user_lifecycle_service.delete_account(to_user_read(existing_user), FIRST_USER_ID)

    assert result is None

    with pytest.raises(
        UserNotFoundError,
        match=re.escape(f"User with id '{FIRST_USER_ID}' was not found."),
    ):
        await UserService(user_repository).get_by_id(FIRST_USER_ID)

    deleted_user = user_repository.users[FIRST_USER_ID]
    assert deleted_user.deleted_at is not None
    assert deleted_user.is_active is False
    assert deleted_user.username.startswith("deleted-")
    assert deleted_user.email.endswith("@deleted.local")


@pytest.mark.anyio
async def test_user_lifecycle_service_delete_account_raises_for_missing_user(
    user_lifecycle_service: UserLifecycleService,
) -> None:
    missing_current_user = to_user_read(
        make_user_auth_read(
            user_id=MISSING_USER_ID,
            username="missing.user",
            email="missing@example.com",
            password_hash="hashed-password",
            created_at=CREATED_AT,
        )
    )

    with pytest.raises(
        UserNotFoundError,
        match=re.escape(f"User with id '{MISSING_USER_ID}' was not found."),
    ):
        await user_lifecycle_service.delete_account(missing_current_user, MISSING_USER_ID)


@pytest.mark.anyio
async def test_user_lifecycle_service_delete_account_raises_for_other_user(
    user_lifecycle_service: UserLifecycleService,
    existing_user: UserAuthRead,
    second_user: UserAuthRead,
) -> None:
    with pytest.raises(
        PermissionDeniedError,
        match=re.escape("You do not have sufficient permissions to perform this action."),
    ):
        await user_lifecycle_service.delete_account(to_user_read(existing_user), second_user.id)


@pytest.mark.anyio
async def test_user_service_touch_last_login_updates_timestamp(
    user_service: UserService,
    user_repository: InMemoryUserRepository,
    existing_user: UserAuthRead,
) -> None:
    result = await user_service.touch_last_login(existing_user.id)

    assert result is None
    assert user_repository.users[existing_user.id].last_login_at is not None


@pytest.mark.anyio
async def test_user_lifecycle_service_delete_account_removes_owned_projects_and_memberships(
    existing_user: UserAuthRead,
) -> None:
    project_repository = InMemoryProjectRepository(
        projects=[
            build_project_read(
                project_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                data=ProjectCreateWithOwner(
                    name="Owned project",
                    description="",
                    owner_id=existing_user.id,
                    start_date=datetime(2026, 1, 1, tzinfo=UTC).date(),
                    end_date=datetime(2026, 12, 31, tzinfo=UTC).date(),
                    status=ProjectStatus.OPEN,
                ),
                created_at=CREATED_AT,
            ),
        ],
        members=[
            ProjectMemberRead(
                project_id=ProjectId(UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")),
                user_id=existing_user.id,
            )
        ],
    )
    user_lifecycle_service = UserLifecycleService(
        InMemoryUserRepository(users=[existing_user]),
        project_repository,
    )

    await user_lifecycle_service.delete_account(to_user_read(existing_user), existing_user.id)

    assert project_repository.projects == {}
    assert existing_user.id not in project_repository.members.get(
        UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        set(),
    )

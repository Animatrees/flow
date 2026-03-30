from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories import (
    EmailAlreadyExistsError,
    UsernameAlreadyExistsError,
    UserRepository,
)
from app.domain.schemas import StoredUser, UserAdminUpdate, UserCreate, UserId, UserUpdate

pytestmark = pytest.mark.anyio

FIRST_USER_ID = UserId(UUID("11111111-1111-1111-1111-111111111111"))
SECOND_USER_ID = UserId(UUID("22222222-2222-2222-2222-222222222222"))
MISSING_USER_ID = UserId(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
DEFAULT_PASSWORD_HASH = "hashed-password"


async def create_user(
    repository: UserRepository,
    *,
    username: str,
    email: str,
    password_hash: str = DEFAULT_PASSWORD_HASH,
) -> None:
    await repository.create(
        UserCreate(
            username=username,
            email=email,
            password_hash=password_hash,
        )
    )


async def seed_user(  # noqa: PLR0913
    session: AsyncSession,
    *,
    user_id: UUID,
    username: str,
    email: str,
    password_hash: str = DEFAULT_PASSWORD_HASH,
    is_superuser: bool = False,
) -> User:
    user = User(
        id=user_id,
        username=username,
        email=email,
        password_hash=password_hash,
        is_superuser=is_superuser,
        is_active=True,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
        last_login_at=None,
        deleted_at=None,
    )
    session.add(user)
    await session.flush()
    return user


@pytest.fixture
async def repository(db_session: AsyncSession) -> UserRepository:
    return UserRepository(db_session)


async def test_create_persists_user_and_returns_read_model(repository: UserRepository) -> None:
    created_user = await repository.create(
        UserCreate(
            username="new.user",
            email="new@example.com",
            password_hash=DEFAULT_PASSWORD_HASH,
        )
    )

    persisted_user = await repository.get_active_by_id(created_user.id)

    assert persisted_user == created_user
    assert created_user.username == "new.user"
    assert created_user.email == "new@example.com"


async def test_create_maps_username_uniqueness_violation(repository: UserRepository) -> None:
    await create_user(
        repository,
        username="existing.user",
        email="first@example.com",
    )

    with pytest.raises(UsernameAlreadyExistsError):
        await repository.create(
            UserCreate(
                username="existing.user",
                email="second@example.com",
                password_hash=DEFAULT_PASSWORD_HASH,
            )
        )


async def test_create_maps_email_uniqueness_violation(repository: UserRepository) -> None:
    await create_user(
        repository,
        username="first.user",
        email="existing@example.com",
    )

    with pytest.raises(EmailAlreadyExistsError):
        await repository.create(
            UserCreate(
                username="second.user",
                email="existing@example.com",
                password_hash=DEFAULT_PASSWORD_HASH,
            )
        )


async def test_get_active_by_id_returns_none_for_missing_user(repository: UserRepository) -> None:
    user = await repository.get_active_by_id(MISSING_USER_ID)

    assert user is None


async def test_get_all_any_status_returns_users_sorted_by_username_then_id(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    second_user = await seed_user(
        db_session,
        user_id=SECOND_USER_ID,
        username="beta.user",
        email="beta@example.com",
    )
    first_user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="alpha.user",
        email="alpha@example.com",
    )

    users = await repository.get_all_any_status()

    assert [user.id for user in users] == [first_user.id, second_user.id]


async def test_get_active_by_username_returns_matching_user(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )

    found_user = await repository.get_active_by_username(user.username)

    assert found_user is not None
    assert found_user.id == user.id
    assert found_user.username == user.username


async def test_get_active_by_username_returns_full_user_data(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
        password_hash="stored-password-hash",
    )

    found_user = await repository.get_active_by_username(user.username)

    assert found_user == StoredUser(
        id=UserId(user.id),
        username=user.username,
        email=user.email,
        password_hash="stored-password-hash",
        is_superuser=False,
        is_active=True,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
        last_login_at=None,
        deleted_at=None,
    )


async def test_update_persists_changed_fields(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )

    updated_user = await repository.update(
        UserId(user.id),
        UserUpdate(username="updated.user", email="updated@example.com"),
    )

    reloaded_user = await repository.get_active_by_id(UserId(user.id))

    assert updated_user == reloaded_user
    assert updated_user is not None
    assert updated_user.username == "updated.user"
    assert updated_user.email == "updated@example.com"


async def test_update_returns_none_for_missing_user(repository: UserRepository) -> None:
    updated_user = await repository.update(
        MISSING_USER_ID,
        UserUpdate(username="updated.user"),
    )

    assert updated_user is None


async def test_update_maps_email_uniqueness_violation(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )
    second_user = await seed_user(
        db_session,
        user_id=SECOND_USER_ID,
        username="second.user",
        email="second@example.com",
    )

    with pytest.raises(EmailAlreadyExistsError):
        await repository.update(
            UserId(second_user.id),
            UserUpdate(email="first@example.com"),
        )


async def test_delete_removes_existing_user(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )

    deleted = await repository.soft_delete(UserId(user.id))

    assert deleted is True
    assert await repository.get_active_by_id(UserId(user.id)) is None
    soft_deleted_user = await db_session.get(User, user.id)
    assert soft_deleted_user is not None
    assert soft_deleted_user.deleted_at is not None
    assert soft_deleted_user.is_active is False
    assert soft_deleted_user.username == f"deleted-{user.id}"
    assert soft_deleted_user.email == f"deleted-{user.id}@deleted.local"


async def test_delete_returns_false_for_missing_user(repository: UserRepository) -> None:
    deleted = await repository.soft_delete(MISSING_USER_ID)

    assert deleted is False


async def test_create_allows_reuse_of_username_and_email_after_soft_delete(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )
    await repository.soft_delete(UserId(user.id))

    recreated_user = await repository.create(
        UserCreate(
            username="first.user",
            email="first@example.com",
            password_hash=DEFAULT_PASSWORD_HASH,
        )
    )

    assert recreated_user.username == "first.user"
    assert recreated_user.email == "first@example.com"


async def test_get_active_by_id_returns_none_for_soft_deleted_user(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )
    await repository.soft_delete(UserId(user.id))

    auth_user = await repository.get_active_by_id(UserId(user.id))

    assert auth_user is None


async def test_touch_last_login_updates_last_login_at(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )

    updated = await repository.touch_last_login(UserId(user.id))

    assert updated is True
    reloaded_user = await repository.get_active_by_id(UserId(user.id))
    assert reloaded_user is not None
    assert reloaded_user.last_login_at is not None


async def test_get_any_by_id_returns_soft_deleted_user(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )
    await repository.soft_delete(UserId(user.id))

    found_user = await repository.get_any_by_id(UserId(user.id))

    assert found_user is not None
    assert found_user.deleted_at is not None


async def test_get_all_any_status_includes_soft_deleted_users(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    first_user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )
    second_user = await seed_user(
        db_session,
        user_id=SECOND_USER_ID,
        username="second.user",
        email="second@example.com",
    )
    await repository.soft_delete(UserId(second_user.id))

    users = await repository.get_all_any_status()

    assert [user.id for user in users] == [second_user.id, first_user.id]
    assert users[0].deleted_at is not None


async def test_update_admin_returns_none_for_soft_deleted_user(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )
    await repository.soft_delete(UserId(user.id))

    updated_user = await repository.update_admin(
        UserId(user.id),
        UserAdminUpdate(username="updated.user"),
    )

    assert updated_user is None

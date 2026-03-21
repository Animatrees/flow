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
from app.domain.schemas import UserAuthRead, UserCreate, UserId, UserUpdate

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


async def seed_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    username: str,
    email: str,
    password_hash: str = DEFAULT_PASSWORD_HASH,
) -> User:
    user = User(
        id=user_id,
        username=username,
        email=email,
        password_hash=password_hash,
        created_at=CREATED_AT,
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

    persisted_user = await repository.get_by_id(created_user.id)

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


async def test_get_by_id_returns_none_for_missing_user(repository: UserRepository) -> None:
    user = await repository.get_by_id(MISSING_USER_ID)

    assert user is None


async def test_get_all_returns_users_sorted_by_username_then_id(
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

    users = await repository.get_all()

    assert [user.id for user in users] == [first_user.id, second_user.id]


async def test_get_by_username_returns_matching_user(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )

    found_user = await repository.get_by_username(user.username)

    assert found_user is not None
    assert found_user.id == user.id
    assert found_user.email == user.email


async def test_get_by_email_returns_matching_user(
    db_session: AsyncSession,
    repository: UserRepository,
) -> None:
    user = await seed_user(
        db_session,
        user_id=FIRST_USER_ID,
        username="first.user",
        email="first@example.com",
    )

    found_user = await repository.get_by_email(user.email)

    assert found_user is not None
    assert found_user.id == user.id
    assert found_user.username == user.username


async def test_get_auth_by_username_returns_auth_projection(
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

    auth_user = await repository.get_auth_by_username(user.username)

    assert auth_user == UserAuthRead(
        id=UserId(user.id),
        username=user.username,
        email=user.email,
        password_hash="stored-password-hash",
        created_at=CREATED_AT,
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

    reloaded_user = await repository.get_by_id(UserId(user.id))

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

    deleted = await repository.delete(UserId(user.id))

    assert deleted is True
    assert await repository.get_by_id(UserId(user.id)) is None


async def test_delete_returns_false_for_missing_user(repository: UserRepository) -> None:
    deleted = await repository.delete(MISSING_USER_ID)

    assert deleted is False

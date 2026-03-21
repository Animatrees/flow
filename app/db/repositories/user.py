from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories.exceptions import (
    EmailAlreadyExistsError,
    RepositoryError,
    UsernameAlreadyExistsError,
)
from app.domain.repositories import AbstractUserRepository
from app.domain.schemas import UserAuthRead, UserCreate, UserId, UserRead, UserUpdate


class UserRepository(AbstractUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id_: UserId) -> UserRead | None:
        user = await self._get_active_user(id_)
        return UserRead.model_validate(user) if user is not None else None

    async def get_all(self) -> Sequence[UserRead]:
        statement = (
            select(User)
            .where(
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
            .order_by(User.username, User.id)
        )
        users = await self.session.scalars(statement)
        return [UserRead.model_validate(user) for user in users]

    async def create(self, data: UserCreate) -> UserRead:
        user = User(**data.model_dump())
        self.session.add(user)

        try:
            await self.session.flush()
        except IntegrityError as err:
            raise self._map_integrity_error(err, data.username, data.email) from err

        return UserRead.model_validate(user)

    async def update(self, id_: UserId, data: UserUpdate) -> UserRead | None:
        user = await self._get_active_user(id_)
        if user is None:
            return None

        username = data.username or user.username
        email = data.email or user.email

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        try:
            await self.session.flush()
        except IntegrityError as err:
            raise self._map_integrity_error(err, username, email) from err

        return UserRead.model_validate(user)

    async def soft_delete(self, user_id: UserId) -> bool:
        statement = select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
        )
        user = (await self.session.scalars(statement)).one_or_none()
        if user is None:
            return False

        user.username = f"deleted-{user.id}"
        user.email = f"deleted-{user.id}@deleted.local"
        user.password_hash = f"deleted:{user.id}"
        user.is_active = False
        user.last_login_at = None
        user.deleted_at = datetime.now(UTC)
        await self.session.flush()
        return True

    async def get_by_username(self, username: str) -> UserRead | None:
        statement = select(User).where(
            User.username == username,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        result = await self.session.scalars(statement)
        user = result.one_or_none()
        return UserRead.model_validate(user) if user is not None else None

    async def get_auth_by_username(self, username: str) -> UserAuthRead | None:
        statement = select(User).where(
            User.username == username,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        result = await self.session.scalars(statement)
        user = result.one_or_none()
        return UserAuthRead.model_validate(user) if user is not None else None

    async def touch_last_login(self, user_id: UserId) -> bool:
        user = await self._get_active_user(user_id)
        if user is None:
            return False

        user.last_login_at = datetime.now(UTC)
        await self.session.flush()
        return True

    async def _get_active_user(self, user_id: UserId) -> User | None:
        statement = select(User).where(
            User.id == user_id,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        return (await self.session.scalars(statement)).one_or_none()

    @staticmethod
    def _map_integrity_error(
        err: IntegrityError,
        username: str,
        email: str,
    ) -> RepositoryError:
        error_text = str(err.orig).lower()

        if "username" in error_text:
            return UsernameAlreadyExistsError(f"Username '{username}' already exists.")

        if "email" in error_text:
            return EmailAlreadyExistsError(f"Email '{email}' already exists.")

        return RepositoryError("Failed to persist user due to database conflict.")

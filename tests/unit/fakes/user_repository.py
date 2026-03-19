from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.db.repositories import EmailAlreadyExistsError, UsernameAlreadyExistsError
from app.schemas import UserAuthRead, UserCreate, UserRead, UserUpdate
from app.services import (
    AbstractUserRepository,
)


def build_user_auth_read(
    *,
    user_id: UUID,
    username: str,
    email: str,
    password_hash: str,
    created_at: datetime | None = None,
) -> UserAuthRead:
    return UserAuthRead(
        id=user_id,
        username=username,
        email=email,
        password_hash=password_hash,
        created_at=created_at or datetime.now(UTC),
    )


def to_user_read(user: UserAuthRead) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
    )


class InMemoryUserRepository(AbstractUserRepository):
    def __init__(
        self,
        users: Iterable[UserAuthRead] | None = None,
        id_factory: Callable[[], UUID] | None = None,
    ) -> None:
        self.users: dict[UUID, UserAuthRead] = {user.id: user for user in (users or [])}
        self.create_error: Exception | None = None
        self.update_error: Exception | None = None
        self.id_factory = id_factory or uuid4

    async def get_by_id(self, id_: UUID) -> UserRead | None:
        user = self.users.get(id_)
        return to_user_read(user) if user is not None else None

    async def get_all(self) -> Sequence[UserRead]:
        return [to_user_read(user) for user in self.users.values()]

    async def create(self, data: UserCreate) -> UserRead:
        if self.create_error is not None:
            raise self.create_error

        self._ensure_unique_username(data.username)
        self._ensure_unique_email(data.email)
        created_user = build_user_auth_read(
            user_id=self.id_factory(),
            username=data.username,
            email=data.email,
            password_hash=data.password_hash,
        )
        self.users[created_user.id] = created_user
        return to_user_read(created_user)

    async def update(self, id_: UUID, data: UserUpdate) -> UserRead | None:
        if self.update_error is not None:
            raise self.update_error

        user = self.users.get(id_)
        if user is None:
            return None
        if data.username is not None:
            self._ensure_unique_username(data.username, exclude_user_id=id_)
        if data.email is not None:
            self._ensure_unique_email(data.email, exclude_user_id=id_)

        updated_user = user.model_copy(update=data.model_dump(exclude_unset=True))
        self.users[id_] = updated_user
        return to_user_read(updated_user)

    async def delete(self, id_: UUID) -> bool:
        deleted_user = self.users.pop(id_, None)
        return deleted_user is not None

    async def get_by_username(self, username: str) -> UserRead | None:
        for user in self.users.values():
            if user.username == username:
                return to_user_read(user)
        return None

    async def get_by_email(self, email: str) -> UserRead | None:
        for user in self.users.values():
            if user.email == email:
                return to_user_read(user)
        return None

    async def get_auth_by_username(self, username: str) -> UserAuthRead | None:
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    def _ensure_unique_username(
        self,
        username: str,
        exclude_user_id: UUID | None = None,
    ) -> None:
        for user_id, user in self.users.items():
            if user.username == username and user_id != exclude_user_id:
                raise UsernameAlreadyExistsError

    def _ensure_unique_email(
        self,
        email: str,
        exclude_user_id: UUID | None = None,
    ) -> None:
        for user_id, user in self.users.items():
            if user.email == email and user_id != exclude_user_id:
                raise EmailAlreadyExistsError

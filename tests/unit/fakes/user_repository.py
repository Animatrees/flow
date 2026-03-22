from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.schemas import (
    UserAdminRead,
    UserAdminUpdate,
    UserAuthRead,
    UserCreate,
    UserData,
    UserPublicRead,
    UserSelfRead,
    UserUpdate,
)
from app.domain.schemas.type_ids import UserId
from app.services import (
    AbstractUserRepository,
    EmailAlreadyExistsError,
    UsernameAlreadyExistsError,
)


def build_user_auth_read(  # noqa: PLR0913
    *,
    user_id: UUID,
    username: str,
    email: str,
    password_hash: str,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    last_login_at: datetime | None = None,
    is_superuser: bool = False,
    is_active: bool = True,
    deleted_at: datetime | None = None,
) -> UserAuthRead:
    timestamp = created_at or datetime.now(UTC)
    return UserAuthRead(
        id=UserId(user_id),
        username=username,
        email=email,
        password_hash=password_hash,
        is_superuser=is_superuser,
        is_active=is_active,
        created_at=timestamp,
        updated_at=updated_at or timestamp,
        last_login_at=last_login_at,
        deleted_at=deleted_at,
    )


def to_user_data(user: UserAuthRead) -> UserData:
    return UserData.model_validate(user)


def to_user_self_read(user: UserAuthRead) -> UserSelfRead:
    return UserSelfRead(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


def to_user_public_read(user: UserAuthRead) -> UserPublicRead:
    return UserPublicRead(
        id=user.id,
        username=user.username,
        last_login_at=user.last_login_at,
    )


def to_user_admin_read(user: UserAuthRead) -> UserAdminRead:
    return UserAdminRead(
        id=user.id,
        username=user.username,
        email=user.email,
        is_superuser=user.is_superuser,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        deleted_at=user.deleted_at,
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

    async def get_active_by_id(self, id_: UUID) -> UserData | None:
        user = self.users.get(id_)
        if user is None or user.deleted_at is not None or not user.is_active:
            return None
        return to_user_data(user)

    async def get_active_by_username(self, username: str) -> UserData | None:
        for user in self.users.values():
            if user.username == username and user.deleted_at is None and user.is_active:
                return to_user_data(user)
        return None

    async def get_any_by_id(self, id_: UUID) -> UserData | None:
        user = self.users.get(id_)
        if user is None:
            return None
        return to_user_data(user)

    async def get_all_any_status(self) -> Sequence[UserData]:
        return [to_user_data(user) for user in self.users.values()]

    async def create(self, data: UserCreate) -> UserData:
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
        return to_user_data(created_user)

    async def update(self, id_: UUID, data: UserUpdate) -> UserData | None:
        if self.update_error is not None:
            raise self.update_error

        user = self.users.get(id_)
        if user is None or user.deleted_at is not None or not user.is_active:
            return None
        if data.username is not None:
            self._ensure_unique_username(data.username, exclude_user_id=id_)
        if data.email is not None:
            self._ensure_unique_email(data.email, exclude_user_id=id_)

        updated_user = user.model_copy(update=data.model_dump(exclude_unset=True))
        self.users[id_] = updated_user
        return to_user_data(updated_user)

    async def update_admin(self, id_: UUID, data: UserAdminUpdate) -> UserData | None:
        if self.update_error is not None:
            raise self.update_error

        user = self.users.get(id_)
        if user is None or user.deleted_at is not None:
            return None
        if data.username is not None:
            self._ensure_unique_username(data.username, exclude_user_id=id_)
        if data.email is not None:
            self._ensure_unique_email(data.email, exclude_user_id=id_)

        updated_user = user.model_copy(update=data.model_dump(exclude_unset=True))
        self.users[id_] = updated_user
        return to_user_data(updated_user)

    async def soft_delete(self, user_id: UserId) -> bool:
        user = self.users.get(user_id)
        if user is None or user.deleted_at is not None:
            return False

        deleted_user = user.model_copy(
            update={
                "username": f"deleted-{user.id}",
                "email": f"deleted-{user.id}@deleted.local",
                "password_hash": f"deleted:{user.id}",
                "is_active": False,
                "last_login_at": None,
                "deleted_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )
        self.users[user_id] = deleted_user
        return True

    async def touch_last_login(self, user_id: UserId) -> bool:
        user = self.users.get(user_id)
        if user is None or user.deleted_at is not None or not user.is_active:
            return False

        updated_user = user.model_copy(
            update={
                "last_login_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )
        self.users[user_id] = updated_user
        return True

    def _ensure_unique_username(
        self,
        username: str,
        exclude_user_id: UUID | None = None,
    ) -> None:
        for user_id, user in self.users.items():
            if user.username == username and user_id != exclude_user_id and user.deleted_at is None:
                raise UsernameAlreadyExistsError

    def _ensure_unique_email(
        self,
        email: str,
        exclude_user_id: UUID | None = None,
    ) -> None:
        for user_id, user in self.users.items():
            if user.email == email and user_id != exclude_user_id and user.deleted_at is None:
                raise EmailAlreadyExistsError

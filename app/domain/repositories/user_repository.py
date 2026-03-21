from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.schemas.type_ids import UserId
from app.domain.schemas.user import UserAuthRead, UserCreate, UserRead, UserUpdate


class AbstractUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id_: UserId) -> UserRead | None:
        """Return an active, non-deleted user by id or None if it does not exist."""

    @abstractmethod
    async def get_all(self) -> Sequence[UserRead]:
        """Return all active, non-deleted users."""

    @abstractmethod
    async def create(self, data: UserCreate) -> UserRead:
        """Create and return a user."""

    @abstractmethod
    async def update(self, id_: UserId, data: UserUpdate) -> UserRead | None:
        """Update and return a user or None if it does not exist."""

    @abstractmethod
    async def get_by_username(self, username: str) -> UserRead | None:
        """Return an active, non-deleted user by username or None if it does not exist."""

    @abstractmethod
    async def get_auth_by_username(self, username: str) -> UserAuthRead | None:
        """Return auth data for a user by username or None if it does not exist."""

    @abstractmethod
    async def touch_last_login(self, user_id: UserId) -> bool:
        """Update the user's last successful login time."""

    @abstractmethod
    async def soft_delete(self, user_id: UserId) -> bool:
        """Soft-delete a user and return True if the user was found and updated."""

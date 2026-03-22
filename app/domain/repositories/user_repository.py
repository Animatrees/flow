from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.schemas.type_ids import UserId
from app.domain.schemas.user import UserAdminUpdate, UserCreate, UserData, UserUpdate


class AbstractUserRepository(ABC):
    @abstractmethod
    async def get_active_by_id(self, id_: UserId) -> UserData | None:
        """Return an active, non-deleted user by id or None if it does not exist."""

    @abstractmethod
    async def get_active_by_username(self, username: str) -> UserData | None:
        """Return an active, non-deleted user by username or None if it does not exist."""

    @abstractmethod
    async def get_any_by_id(self, id_: UserId) -> UserData | None:
        """Return any user by id, including inactive or soft-deleted records."""

    @abstractmethod
    async def get_all_any_status(self) -> Sequence[UserData]:
        """Return all users, including inactive or soft-deleted records."""

    @abstractmethod
    async def create(self, data: UserCreate) -> UserData:
        """Create and return a user."""

    @abstractmethod
    async def update(self, id_: UserId, data: UserUpdate) -> UserData | None:
        """Update and return an active, non-deleted user or None if it does not exist."""

    @abstractmethod
    async def update_admin(self, id_: UserId, data: UserAdminUpdate) -> UserData | None:
        """Update and return a non-deleted user or None if it does not exist."""

    @abstractmethod
    async def touch_last_login(self, user_id: UserId) -> bool:
        """Update the user's last successful login time."""

    @abstractmethod
    async def soft_delete(self, user_id: UserId) -> bool:
        """Soft-delete a user and return True if the user was found and updated."""

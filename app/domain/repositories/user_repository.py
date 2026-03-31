from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.schemas.type_ids import UserId
from app.domain.schemas.user import StoredUser, UserAdminUpdate, UserCreate, UserUpdate


class AbstractUserRepository(ABC):
    """Repository contract for user records and lifecycle updates.

    Supports:
        - reads for active and any-status users
        - user creation and updates
        - last-login tracking
        - soft deletion
    """

    @abstractmethod
    async def get_active_by_id(self, id_: UserId) -> StoredUser | None:
        """Return an active, non-deleted user by id, or `None` if it does not exist."""

    @abstractmethod
    async def get_active_by_username(self, username: str) -> StoredUser | None:
        """Return an active, non-deleted user by username, or `None` if it does not exist."""

    @abstractmethod
    async def get_any_by_id(self, id_: UserId) -> StoredUser | None:
        """Return any user by id, or `None` if it does not exist."""

    @abstractmethod
    async def get_all_any_status(self) -> Sequence[StoredUser]:
        """Return all users, including inactive or soft-deleted records."""

    @abstractmethod
    async def create(self, data: UserCreate) -> StoredUser:
        """Create a user."""

    @abstractmethod
    async def update(self, id_: UserId, data: UserUpdate) -> StoredUser | None:
        """Update an active, non-deleted user, or return `None` if it does not exist."""

    @abstractmethod
    async def update_admin(self, id_: UserId, data: UserAdminUpdate) -> StoredUser | None:
        """Update a non-deleted user with administrative fields, or return `None` if it does not exist."""

    @abstractmethod
    async def touch_last_login(self, user_id: UserId) -> bool:
        """Update the user's last successful login time."""

    @abstractmethod
    async def soft_delete(self, user_id: UserId) -> bool:
        """Soft-delete a user."""

from abc import abstractmethod
from uuid import UUID

from app.schemas.user import UserAuthRead, UserCreate, UserRead, UserUpdate
from app.services.base_repository import AbstractRepository


class AbstractUserRepository(AbstractRepository[UUID, UserCreate, UserRead, UserUpdate]):
    @abstractmethod
    async def get_by_username(self, username: str) -> UserRead | None:
        """Return a user by username or None if it does not exist."""

    @abstractmethod
    async def get_by_email(self, email: str) -> UserRead | None:
        """Return a user by email or None if it does not exist."""

    @abstractmethod
    async def get_auth_by_username(self, username: str) -> UserAuthRead | None:
        """Return auth data for a user by username or None if it does not exist."""

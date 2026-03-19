from collections.abc import Sequence
from uuid import UUID

from app.db.repositories import (
    ConflictError as RepositoryConflictError,
)
from app.db.repositories import (
    EmailAlreadyExistsError as RepositoryEmailAlreadyExistsError,
)
from app.db.repositories import (
    UsernameAlreadyExistsError as RepositoryUsernameAlreadyExistsError,
)
from app.schemas.user import UserAuthRead, UserCreate, UserRead, UserUpdate
from app.services.exceptions import (
    ConflictError,
    EmailAlreadyExistsError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from app.services.user_repository import AbstractUserRepository


class UserService:
    def __init__(self, repo: AbstractUserRepository) -> None:
        self.repo = repo

    async def create(self, data: UserCreate) -> UserRead:
        try:
            return await self.repo.create(data)
        except RepositoryConflictError as err:
            raise self._map_conflict_error(err) from err

    async def get_by_id(self, user_id: UUID) -> UserRead:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)
        return user

    async def get_by_username(self, username: str) -> UserRead:
        user = await self.repo.get_by_username(username)
        if user is None:
            msg = f"User with username '{username}' was not found."
            raise UserNotFoundError(msg)
        return user

    async def get_by_email(self, email: str) -> UserRead:
        user = await self.repo.get_by_email(email)
        if user is None:
            msg = f"User with email '{email}' was not found."
            raise UserNotFoundError(msg)
        return user

    async def get_auth_user_by_username(self, username: str) -> UserAuthRead | None:
        return await self.repo.get_auth_by_username(username)

    async def get_all(self) -> Sequence[UserRead]:
        return await self.repo.get_all()

    async def update(self, user_id: UUID, data: UserUpdate) -> UserRead:
        try:
            user = await self.repo.update(user_id, data)
        except RepositoryConflictError as err:
            raise self._map_conflict_error(err) from err

        if user is None:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)
        return user

    async def delete(self, user_id: UUID) -> None:
        success = await self.repo.delete(user_id)
        if not success:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)

    @staticmethod
    def _map_conflict_error(err: RepositoryConflictError) -> ConflictError:
        if isinstance(err, RepositoryUsernameAlreadyExistsError):
            return UsernameAlreadyExistsError(str(err))

        if isinstance(err, RepositoryEmailAlreadyExistsError):
            return EmailAlreadyExistsError(str(err))

        return ConflictError(str(err))

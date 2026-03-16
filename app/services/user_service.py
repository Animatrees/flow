from collections.abc import Sequence
from uuid import UUID

from app.schemas.user import UserAuthRead, UserCreate, UserRead, UserUpdate
from app.services.exceptions import (
    NotFoundError,
    UserNotFoundError,
)
from app.services.user_repository import AbstractUserRepository


class UserService:
    def __init__(self, repo: AbstractUserRepository) -> None:
        self.repo = repo

    async def create(self, data: UserCreate) -> UserRead:
        return await self.repo.create(data)

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
            return await self.repo.update(user_id, data)
        except NotFoundError as err:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg) from err

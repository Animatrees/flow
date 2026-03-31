from app.domain.mappers import UserMapper
from app.domain.repositories import AbstractUserRepository
from app.domain.schemas.type_ids import UserId
from app.domain.schemas.user import (
    UserAuthRead,
    UserCreate,
    UserPublicRead,
    UserSelfRead,
    UserUpdate,
)
from app.services.exceptions import (
    ConflictError,
    EmailAlreadyExistsError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from app.services.user_lifecycle_service import UserLifecycleService


class UserService:
    """Service for self-service user operations.

    Handles:
        - user creation
        - self and public user reads
        - self-service profile updates
        - self-service account deletion
        - last-login tracking
    """

    def __init__(
        self, repo: AbstractUserRepository, lifecycle_service: UserLifecycleService
    ) -> None:
        self.repo = repo
        self.lifecycle_service = lifecycle_service

    async def create(self, data: UserCreate) -> UserSelfRead:
        try:
            user = await self.repo.create(data)
        except ConflictError as err:
            raise self._map_conflict_error(err) from err
        return UserMapper.to_self(user)

    async def get_self_by_id(self, user_id: UserId) -> UserSelfRead:
        user = await self.repo.get_active_by_id(user_id)
        if user is None:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)
        return UserMapper.to_self(user)

    async def get_public_by_id(self, user_id: UserId) -> UserPublicRead:
        user = await self.repo.get_active_by_id(user_id)
        if user is None:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)
        return UserMapper.to_public(user)

    async def get_public_by_username(self, username: str) -> UserPublicRead:
        user = await self.repo.get_active_by_username(username)
        if user is None:
            msg = f"User with username '{username}' was not found."
            raise UserNotFoundError(msg)
        return UserMapper.to_public(user)

    async def get_auth_user_by_username(self, username: str) -> UserAuthRead | None:
        user = await self.repo.get_active_by_username(username)
        if user is None:
            return None
        return UserMapper.to_auth(user)

    async def get_auth_user_by_id(self, user_id: UserId) -> UserAuthRead:
        user = await self.repo.get_active_by_id(user_id)
        if user is None:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)
        return UserMapper.to_auth(user)

    async def update_self(self, user_id: UserId, data: UserUpdate) -> UserSelfRead:
        try:
            user = await self.repo.update(user_id, data)
        except ConflictError as err:
            raise self._map_conflict_error(err) from err

        if user is None:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)
        return UserMapper.to_self(user)

    async def delete_self(self, user_id: UserId) -> None:
        await self.lifecycle_service.delete_account(user_id)

    async def touch_last_login(self, user_id: UserId) -> None:
        success = await self.repo.touch_last_login(user_id)
        if not success:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)

    @staticmethod
    def _map_conflict_error(err: ConflictError) -> ConflictError:
        if isinstance(err, UsernameAlreadyExistsError):
            return UsernameAlreadyExistsError(str(err))

        if isinstance(err, EmailAlreadyExistsError):
            return EmailAlreadyExistsError(str(err))

        return ConflictError(str(err))

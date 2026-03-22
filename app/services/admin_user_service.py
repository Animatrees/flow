from collections.abc import Sequence

from app.domain.mappers import UserMapper
from app.domain.repositories import AbstractUserRepository
from app.domain.schemas.type_ids import UserId
from app.domain.schemas.user import UserAdminRead, UserAdminUpdate, UserAuthRead
from app.services.exceptions import (
    ConflictError,
    EmailAlreadyExistsError,
    PermissionDeniedError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from app.services.user_lifecycle_service import UserLifecycleService


class AdminUserService:
    def __init__(
        self, repo: AbstractUserRepository, lifecycle_service: UserLifecycleService
    ) -> None:
        self.repo = repo
        self.lifecycle_service = lifecycle_service

    async def get_all(self, current_user: UserAuthRead) -> Sequence[UserAdminRead]:
        self._ensure_admin(current_user)
        return [UserMapper.to_admin(user) for user in await self.repo.get_all_any_status()]

    async def get_by_id(self, current_user: UserAuthRead, user_id: UserId) -> UserAdminRead:
        self._ensure_admin(current_user)
        user = await self.repo.get_any_by_id(user_id)
        if user is None:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)
        return UserMapper.to_admin(user)

    async def update(
        self,
        current_user: UserAuthRead,
        user_id: UserId,
        data: UserAdminUpdate,
    ) -> UserAdminRead:
        self._ensure_admin(current_user)
        try:
            user = await self.repo.update_admin(user_id, data)
        except ConflictError as err:
            raise self._map_conflict_error(err) from err

        if user is None:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)
        return UserMapper.to_admin(user)

    async def delete(self, current_user: UserAuthRead, user_id: UserId) -> None:
        self._ensure_admin(current_user)
        await self.lifecycle_service.delete_account(user_id)

    @staticmethod
    def _map_conflict_error(err: ConflictError) -> ConflictError:
        if isinstance(err, UsernameAlreadyExistsError):
            return UsernameAlreadyExistsError(str(err))

        if isinstance(err, EmailAlreadyExistsError):
            return EmailAlreadyExistsError(str(err))

        return ConflictError(str(err))

    @staticmethod
    def _ensure_admin(current_user: UserAuthRead) -> None:
        if not current_user.is_superuser:
            raise PermissionDeniedError

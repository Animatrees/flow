from app.domain.repositories import AbstractUserRepository
from app.domain.repositories.project_repository import AbstractProjectRepository
from app.domain.schemas.type_ids import UserId
from app.services.exceptions import UserNotFoundError


class UserLifecycleService:
    """Service for user account deletion side effects.

    Handles:
        - user soft deletion
        - deletion of owned projects
        - membership cleanup
    """

    def __init__(
        self,
        user_repo: AbstractUserRepository,
        project_repo: AbstractProjectRepository,
    ) -> None:
        self.user_repo = user_repo
        self.project_repo = project_repo

    async def delete_account(self, user_id: UserId) -> None:
        await self.project_repo.delete_all_owned_by_user(user_id)
        await self.project_repo.remove_memberships_for_user(user_id)
        success = await self.user_repo.soft_delete(user_id)
        if not success:
            msg = f"User with id '{user_id}' was not found."
            raise UserNotFoundError(msg)

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import UserRepository
from app.services.user_repository import AbstractUserRepository


class RepositoryProvider(Provider):
    @provide(scope=Scope.REQUEST, provides=AbstractUserRepository)
    def provide_user_repository(self, session: AsyncSession) -> AbstractUserRepository:
        return UserRepository(session)

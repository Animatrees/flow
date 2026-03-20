from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import ProjectRepository, UserRepository
from app.services import AbstractProjectRepository, AbstractUserRepository


class RepositoryProvider(Provider):
    @provide(scope=Scope.REQUEST, provides=AbstractProjectRepository)
    def provide_project_repository(self, session: AsyncSession) -> AbstractProjectRepository:
        return ProjectRepository(session)

    @provide(scope=Scope.REQUEST, provides=AbstractUserRepository)
    def provide_user_repository(self, session: AsyncSession) -> AbstractUserRepository:
        return UserRepository(session)

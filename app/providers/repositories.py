from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import DocumentRepository, ProjectRepository, UserRepository
from app.services import (
    AbstractDocumentRepository,
    AbstractProjectRepository,
    AbstractUserRepository,
)


class RepositoryProvider(Provider):
    @provide(scope=Scope.REQUEST, provides=AbstractDocumentRepository)
    def provide_document_repository(self, session: AsyncSession) -> AbstractDocumentRepository:
        return DocumentRepository(session)

    @provide(scope=Scope.REQUEST, provides=AbstractProjectRepository)
    def provide_project_repository(self, session: AsyncSession) -> AbstractProjectRepository:
        return ProjectRepository(session)

    @provide(scope=Scope.REQUEST, provides=AbstractUserRepository)
    def provide_user_repository(self, session: AsyncSession) -> AbstractUserRepository:
        return UserRepository(session)

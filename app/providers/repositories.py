from dishka import Provider, Scope, provide

from app.db.repositories import DocumentRepository, ProjectRepository, UserRepository
from app.services import (
    AbstractDocumentRepository,
    AbstractProjectRepository,
    AbstractUserRepository,
)


class RepositoryProvider(Provider):
    """Dishka provider for SQLAlchemy-backed repository bindings."""

    scope = Scope.REQUEST

    document_repository = provide(DocumentRepository, provides=AbstractDocumentRepository)
    project_repository = provide(ProjectRepository, provides=AbstractProjectRepository)
    user_repository = provide(UserRepository, provides=AbstractUserRepository)

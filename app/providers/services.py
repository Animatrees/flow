from dishka import Provider, Scope, provide

from app.services import (
    AdminUserService,
    AuthService,
    DocumentService,
    JWTService,
    ProjectService,
    UserLifecycleService,
    UserService,
)


class ServiceProvider(Provider):
    """Dishka provider for application service bindings."""

    scope = Scope.REQUEST

    project_service = provide(ProjectService)
    user_service = provide(UserService)
    admin_user_service = provide(AdminUserService)
    user_lifecycle_service = provide(UserLifecycleService)
    auth_service = provide(AuthService)
    document_service = provide(DocumentService)

    jwt_service = provide(JWTService, scope=Scope.APP)

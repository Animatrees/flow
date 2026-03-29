from dishka import Provider, Scope, provide

from app.core.config import JWTConfig
from app.services import (
    AbstractProjectRepository,
    AbstractUserRepository,
    AdminUserService,
    AuthService,
    JWTService,
    ProjectService,
    UserLifecycleService,
    UserService,
)


class ServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_project_service(
        self,
        repo: AbstractProjectRepository,
        user_repo: AbstractUserRepository,
    ) -> ProjectService:
        return ProjectService(repo, user_repo)

    @provide(scope=Scope.REQUEST)
    def provide_user_service(
        self,
        repo: AbstractUserRepository,
        lifecycle_service: UserLifecycleService,
    ) -> UserService:
        return UserService(repo, lifecycle_service)

    @provide(scope=Scope.REQUEST)
    def provide_admin_user_service(
        self,
        repo: AbstractUserRepository,
        lifecycle_service: UserLifecycleService,
    ) -> AdminUserService:
        return AdminUserService(repo, lifecycle_service)

    @provide(scope=Scope.REQUEST)
    def provide_user_lifecycle_service(
        self,
        user_repo: AbstractUserRepository,
        project_repo: AbstractProjectRepository,
    ) -> UserLifecycleService:
        return UserLifecycleService(user_repo, project_repo)

    @provide(scope=Scope.REQUEST)
    def provide_auth_service(
        self,
        user_service: UserService,
        jwt_service: JWTService,
        jwt_config: JWTConfig,
    ) -> AuthService:
        return AuthService(user_service, jwt_service, jwt_config)

    @provide(scope=Scope.APP)
    def provide_jwt_service(self, config: JWTConfig) -> JWTService:
        return JWTService(config)

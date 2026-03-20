from dishka import Provider, Scope, provide

from app.core.config import AuthJWT
from app.services import AuthService, UserService
from app.services.jwt_service import JWTService
from app.services.user_repository import AbstractUserRepository


class ServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_user_service(self, repo: AbstractUserRepository) -> UserService:
        return UserService(repo)

    @provide(scope=Scope.REQUEST)
    def provide_auth_service(
        self, user_service: UserService, jwt_service: JWTService
    ) -> AuthService:
        return AuthService(user_service, jwt_service)

    @provide(scope=Scope.APP)
    def provide_jwt_service(self, config: AuthJWT) -> JWTService:
        return JWTService(config)

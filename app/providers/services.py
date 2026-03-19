from dishka import Provider, Scope, provide

from app.services import AuthService, UserService
from app.services.user_repository import AbstractUserRepository


class ServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def provide_user_service(self, repo: AbstractUserRepository) -> UserService:
        return UserService(repo)

    @provide(scope=Scope.REQUEST)
    def provide_auth_service(self, user_service: UserService) -> AuthService:
        return AuthService(user_service)

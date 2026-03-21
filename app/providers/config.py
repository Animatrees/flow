from dishka import Provider, Scope, provide

from app.core.config import AuthJWT, DatabaseConfig, Settings


class ConfigProvider(Provider):
    def __init__(self, config: Settings) -> None:
        super().__init__()
        self._config = config

    @provide(scope=Scope.APP)
    def provide_config(self) -> Settings:
        return self._config

    @provide(scope=Scope.APP)
    def provide_db_config(self) -> DatabaseConfig:
        return self._config.db

    @provide(scope=Scope.APP)
    def provide_auth_jwt_config(self) -> AuthJWT:
        return self._config.auth_jwt

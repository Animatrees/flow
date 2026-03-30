from dishka import Provider, Scope, provide

from app.core.config import DatabaseConfig, JWTConfig, S3Config, Settings


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
    def provide_jwt_config(self) -> JWTConfig:
        return self._config.jwt

    @provide(scope=Scope.APP)
    def provide_s3_config(self) -> S3Config:
        return self._config.s3

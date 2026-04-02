from dishka import Provider, Scope, from_context, provide

from app.core.config import DatabaseConfig, JWTConfig, S3Config, Settings


class ConfigProvider(Provider):
    """Dishka provider for application configuration objects."""

    scope = Scope.APP

    config = from_context(provides=Settings)

    @provide
    def provide_db_config(self, settings: Settings) -> DatabaseConfig:
        return settings.db

    @provide
    def provide_jwt_config(self, settings: Settings) -> JWTConfig:
        return settings.jwt

    @provide
    def provide_s3_config(self, settings: Settings) -> S3Config:
        return settings.s3

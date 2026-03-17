from pathlib import Path

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class RunConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000


class ApiPrefix(BaseModel):
    prefix: str = "/api/v1"


class DatabaseConfig(BaseModel):
    name: str
    user: str
    password: SecretStr
    host: str
    port: int

    echo: bool = True
    echo_pool: bool = True
    pool_pre_ping: bool = True
    pool_size: int = 15
    max_overflow: int = 15

    @property
    def url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.name,
        )


class Settings(BaseSettings):
    ENV_FILE_PATH: Path = Path(__file__).resolve().parent.parent.parent / ".env"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False,
    )

    run: RunConfig = RunConfig()
    api: ApiPrefix = ApiPrefix()
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)


settings = Settings()

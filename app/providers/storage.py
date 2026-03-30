from dishka import Provider, Scope, provide

from app.core.config import S3Config
from app.infrastructure import S3FileStorage
from app.services import AbstractFileStorage


class StorageProvider(Provider):
    @provide(scope=Scope.APP, provides=AbstractFileStorage)
    def provide_file_storage(self, config: S3Config) -> AbstractFileStorage:
        return S3FileStorage(config)

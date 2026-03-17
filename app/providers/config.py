from dishka import Provider, Scope, provide

from app.core.config import Settings


class ConfigProvider(Provider):
    def __init__(self, config: Settings) -> None:
        super().__init__()
        self._config = config

    @provide(scope=Scope.APP)
    def provide_config(self) -> Settings:
        return self._config

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from app.api.v1 import init_exception_handler, init_routes
from app.core.config import Settings
from app.providers import ConfigProvider, RepositoryProvider, ServiceProvider, SqlalchemyProvider

config = Settings()


def container_factory() -> AsyncContainer:
    return make_async_container(
        ConfigProvider(config=config),
        SqlalchemyProvider(),
        RepositoryProvider(),
        ServiceProvider(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    if hasattr(app.state, "dishka_container"):
        await app.state.dishka_container.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Flow",
        version="0.1.0",
        swagger_ui_parameters={
            "syntaxHighlight.theme": "obsidian",
            "persistAuthorization": True,
        },
        lifespan=lifespan,
        docs_url="/docs",
    )

    init_routes(app, config)
    init_exception_handler(app)

    container = container_factory()
    setup_dishka(container, app)

    return app


if __name__ == "__main__":
    uvicorn.run(
        "main:create_app", factory=True, host=config.run.host, port=config.run.port, reload=True
    )

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import AsyncContainer, setup_dishka
from fastapi import FastAPI
from pydantic import SecretStr
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.api.v1 import init_exception_handler
from app.api.v1.routes import init_routes
from app.core.config import ApiPrefix, DatabaseConfig, RunConfig, Settings
from app.db.models import Base
from app.providers import RepositoryProvider, ServiceProvider

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


def create_test_engine(
    db_url: str,
    *,
    poolclass: type[NullPool] | None = None,
) -> AsyncEngine:
    engine = create_async_engine(
        db_url,
        poolclass=poolclass,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def register_sqlite_functions(dbapi_connection: Any, _: Any) -> None:
        dbapi_connection.run_async(
            lambda connection: connection.create_function("char_length", 1, len)
        )

    return engine


class ApiTestDatabaseProvider(Provider):
    def __init__(self, db_url: str) -> None:
        super().__init__()
        self._db_url = db_url

    @provide(scope=Scope.APP)
    async def provide_engine(self) -> AsyncIterator[AsyncEngine]:
        engine = create_test_engine(self._db_url)
        try:
            yield engine
        finally:
            await engine.dispose()

    @provide(scope=Scope.APP)
    def provide_session_maker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    @provide(scope=Scope.REQUEST, provides=AsyncSession)
    async def provide_session(
        self, session_maker: async_sessionmaker[AsyncSession]
    ) -> AsyncIterator[AsyncSession]:
        session = session_maker()
        try:
            yield session
            if session.in_transaction():
                if session.is_active:
                    await session.commit()
                else:
                    await session.rollback()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def prepare_database(db_url: str) -> None:
    engine = create_test_engine(db_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def engine() -> AsyncEngine:
    return create_test_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )


@pytest.fixture
async def db_session(
    engine: AsyncEngine,
) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with session_factory() as session:
            yield session
            await session.rollback()


@pytest.fixture
async def container(tmp_path: Path) -> AsyncIterator[AsyncContainer]:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    await prepare_database(db_url)

    test_container = make_async_container(
        ApiTestDatabaseProvider(db_url),
        RepositoryProvider(),
        ServiceProvider(),
    )
    try:
        yield test_container
    finally:
        await test_container.close()


@pytest.fixture
def settings() -> Settings:
    return Settings.model_construct(
        run=RunConfig(),
        api=ApiPrefix(),
        db=DatabaseConfig.model_construct(
            name="test",
            user="test",
            password=SecretStr("test"),
            host="localhost",
            port=5432,
        ),
    )


@pytest.fixture
def app(settings: Settings, container: AsyncContainer) -> FastAPI:
    test_app = FastAPI()
    init_routes(test_app, settings)
    init_exception_handler(test_app)
    setup_dishka(container, test_app)
    return test_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client

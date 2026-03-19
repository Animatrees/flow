from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.db.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def engine() -> AsyncEngine:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def register_sqlite_functions(dbapi_connection: Any, _: Any) -> None:
        dbapi_connection.run_async(
            lambda connection: connection.create_function("char_length", 1, len)
        )

    return engine


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

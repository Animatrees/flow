from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import DatabaseConfig


class SqlalchemyProvider(Provider):
    """Dishka provider for the async SQLAlchemy engine and sessions."""

    @provide(scope=Scope.APP)
    async def provide_engine(self, config: DatabaseConfig) -> AsyncGenerator[AsyncEngine, None]:
        engine = create_async_engine(
            url=config.url,
            echo=config.echo,
            echo_pool=config.echo_pool,
            pool_pre_ping=config.pool_pre_ping,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
        )
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
    ) -> AsyncGenerator[AsyncSession, None]:
        session = session_maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

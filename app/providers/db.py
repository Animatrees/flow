from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


class SqlalchemyProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_engine(self, config: Settings) -> AsyncGenerator[AsyncEngine, None]:
        engine = create_async_engine(
            url=config.db.url,
            echo=config.db.echo,
            echo_pool=config.db.echo_pool,
            pool_pre_ping=config.db.pool_pre_ping,
            pool_size=config.db.pool_size,
            max_overflow=config.db.max_overflow,
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

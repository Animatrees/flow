from fastapi import FastAPI

from app.core.config import Settings

from .auth import router as auth_router
from .health_check import router
from .users import router as users_router


def init_routes(app: FastAPI, config: Settings) -> None:
    prefix: str = config.api.prefix
    app.include_router(
        router=auth_router,
        prefix=f"{prefix}/auth",
        tags=["Auth"],
    )
    app.include_router(
        router=users_router,
        prefix=f"{prefix}/users",
        tags=["Users"],
    )
    app.include_router(
        router=router,
        prefix=f"{prefix}/health-check",
        tags=["Test"],
    )


__all__ = ["init_routes"]

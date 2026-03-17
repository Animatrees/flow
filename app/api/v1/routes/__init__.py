from fastapi import FastAPI

from app.core.config import Settings

from .health_check import router


def init_routes(app: FastAPI, config: Settings) -> None:
    prefix: str = config.api.prefix
    app.include_router(
        router=router,
        prefix=f"{prefix}/health-check",
        tags=["Test"],
    )


__all__ = ["init_routes"]

from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services import ServiceError

exception_status_codes = {
    ServiceError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


async def app_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    for exc_class, status_code in exception_status_codes.items():
        if isinstance(exc, exc_class):
            return JSONResponse(
                status_code=status_code,
                content={"message": str(exc)},
            )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Internal Server Error"},
    )


async def http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast("StarletteHTTPException", exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content={"message": str(http_exc.detail)},
    )


async def validation_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast("RequestValidationError", exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Ошибка валидации данных",
            "details": http_exc.errors(),  # по желанию, можно убрать
        },
    )


def init_exception_handler(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    for exc_class in exception_status_codes:
        app.add_exception_handler(exc_class, app_exception_handler)

    app.add_exception_handler(Exception, app_exception_handler)

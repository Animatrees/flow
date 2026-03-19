import logging
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services import ConflictError, InvalidCredentialsError, NotFoundError, ServiceError

logger = logging.getLogger(__name__)

exception_status_codes = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    ServiceError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


async def app_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    for exc_class, status_code in exception_status_codes.items():
        if isinstance(exc, exc_class):
            return JSONResponse(
                status_code=status_code,
                content={"message": str(exc)},
            )

    logger.exception("Unhandled exception occurred")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Internal Server Error"},
    )


async def validation_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    val_exc = cast("RequestValidationError", exc)

    clean_errors = []
    for err in val_exc.errors():
        msg = err.get("msg", "")

        if isinstance(msg, str):
            for prefix in ["Value error, ", "Assertion failed, "]:
                if msg.startswith(prefix):
                    msg = msg.replace(prefix, "", 1)

        clean_errors.append(
            {
                "loc": err.get("loc"),
                "msg": msg,
                "type": err.get("type"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(
            {
                "message": "Data validation error",
                "details": clean_errors,
            }
        ),
    )


async def http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast("StarletteHTTPException", exc)

    return JSONResponse(
        status_code=http_exc.status_code,
        content={"message": http_exc.detail},
    )


def init_exception_handler(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    for exc_class in exception_status_codes:
        app.add_exception_handler(exc_class, app_exception_handler)

    app.add_exception_handler(Exception, app_exception_handler)

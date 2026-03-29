from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.domain.schemas import UserAuthRead
from app.services import (
    AuthService,
    InvalidTokenError,
    PermissionDeniedError,
    UserNotFoundError,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@inject
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: FromDishka[AuthService],
) -> UserAuthRead:
    try:
        return await auth_service.get_current_user_by_token(token)
    except (InvalidTokenError, UserNotFoundError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


async def check_admin(
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> UserAuthRead:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(PermissionDeniedError()),
        )
    return current_user

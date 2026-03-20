from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.schemas import UserId, UserRead
from app.services import AuthService, InvalidTokenError, UserNotFoundError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@inject
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: FromDishka[AuthService],
) -> UserRead:
    try:
        payload = auth_service.jwt_service.decode_access_token(token)
        user_id = UserId(UUID(payload["sub"]))
        return await auth_service.user_service.get_by_id(user_id)
    except (InvalidTokenError, UserNotFoundError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

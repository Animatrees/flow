from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, status
from fastapi.responses import Response

from app.api.v1.get_current_user import get_current_user
from app.domain.schemas import UserAuthRead, UserId, UserPublicRead, UserSelfRead, UserUpdate
from app.services import UserService

router = APIRouter(
    route_class=DishkaRoute,
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
)
async def get_me(
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
    user_service: FromDishka[UserService],
) -> UserSelfRead:
    return await user_service.get_self_by_id(current_user.id)


@router.patch(
    "/me",
    status_code=status.HTTP_200_OK,
)
async def update_me(
    data: UserUpdate,
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
    user_service: FromDishka[UserService],
) -> UserSelfRead:
    return await user_service.update_self(current_user.id, data)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_me(
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
    user_service: FromDishka[UserService],
) -> Response:
    await user_service.delete_self(current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def get_user_by_id(
    user_id: UserId,
    user_service: FromDishka[UserService],
) -> UserPublicRead:
    return await user_service.get_public_by_id(user_id)

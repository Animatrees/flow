from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, status

from app.api.v1.get_current_user import get_current_user
from app.schemas import UserId, UserRead, UserUpdate
from app.schemas.user import LowerEmail, Username
from app.services import UserService

router = APIRouter(
    route_class=DishkaRoute,
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
async def get_users(
    user_service: FromDishka[UserService],
) -> list[UserRead]:
    return list(await user_service.get_all())


@router.get(
    "/by-username/{username}",
    status_code=status.HTTP_200_OK,
)
async def get_user_by_username(
    username: Username,
    user_service: FromDishka[UserService],
) -> UserRead:
    return await user_service.get_by_username(username)


@router.get(
    "/by-email/{email}",
    status_code=status.HTTP_200_OK,
)
async def get_user_by_email(
    email: LowerEmail,
    user_service: FromDishka[UserService],
) -> UserRead:
    return await user_service.get_by_email(email)


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def get_user_by_id(
    user_id: UserId,
    user_service: FromDishka[UserService],
) -> UserRead:
    return await user_service.get_by_id(user_id)


@router.patch(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def update_user(
    user_id: UserId,
    data: UserUpdate,
    user_service: FromDishka[UserService],
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> UserRead:
    return await user_service.update(current_user, user_id, data)

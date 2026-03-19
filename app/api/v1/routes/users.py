from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from app.schemas import UserRead, UserUpdate
from app.schemas.user import LowerEmail, Username
from app.services import UserService

router = APIRouter(route_class=DishkaRoute)


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
    user_id: UUID,
    user_service: FromDishka[UserService],
) -> UserRead:
    return await user_service.get_by_id(user_id)


@router.patch(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    user_service: FromDishka[UserService],
) -> UserRead:
    return await user_service.update(user_id, data)

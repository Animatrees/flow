from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, status
from fastapi.responses import Response

from app.api.v1.get_current_user import check_admin, get_current_user
from app.domain.schemas import UserAdminRead, UserAdminUpdate, UserAuthRead, UserId
from app.services import AdminUserService

router = APIRouter(
    route_class=DishkaRoute,
    dependencies=[Depends(check_admin)],
    include_in_schema=False,
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
async def get_users(
    admin_user_service: FromDishka[AdminUserService],
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> list[UserAdminRead]:
    return list(await admin_user_service.get_all(current_user))


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def get_user_by_id(
    user_id: UserId,
    admin_user_service: FromDishka[AdminUserService],
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> UserAdminRead:
    return await admin_user_service.get_by_id(current_user, user_id)


@router.patch(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
)
async def update_user(
    user_id: UserId,
    data: UserAdminUpdate,
    admin_user_service: FromDishka[AdminUserService],
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> UserAdminRead:
    return await admin_user_service.update(current_user, user_id, data)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(
    user_id: UserId,
    admin_user_service: FromDishka[AdminUserService],
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> Response:
    await admin_user_service.delete(current_user, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

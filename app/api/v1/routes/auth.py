from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from app.schemas import LoginRequest, RegisterRequest, UserRead
from app.services import AuthService

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    auth_service: FromDishka[AuthService],
) -> UserRead:
    return await auth_service.register(data)


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
)
async def login(
    data: LoginRequest,
    auth_service: FromDishka[AuthService],
) -> UserRead:
    return await auth_service.authenticate(data)

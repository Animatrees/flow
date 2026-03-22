from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.domain.schemas import LoginRequest, RegisterRequest, UserSelfRead
from app.domain.schemas.auth import TokenResponse
from app.services import AuthService

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    auth_service: FromDishka[AuthService],
) -> UserSelfRead:
    return await auth_service.register(data)


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
)
async def login(
    auth_service: FromDishka[AuthService],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    data = LoginRequest(
        username=form_data.username,
        password=form_data.password,
    )
    return await auth_service.authenticate(data)

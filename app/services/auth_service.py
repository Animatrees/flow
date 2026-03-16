from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserCreate, UserRead
from app.services.exceptions import InvalidCredentialsError
from app.services.security import hash_password, verify_password
from app.services.user_service import UserService


class AuthService:
    def __init__(self, user_service: UserService) -> None:
        self.user_service = user_service

    async def register(self, data: RegisterRequest) -> UserRead:
        password_hash = hash_password(data.password)
        user_create = UserCreate(
            username=data.username,
            email=data.email,
            password_hash=password_hash,
        )
        return await self.user_service.create(data=user_create)

    async def authenticate(self, data: LoginRequest) -> UserRead:
        user = await self.user_service.get_auth_user_by_username(data.username)
        if user is None or not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError

        return UserRead.model_validate(user)

from app.domain.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.domain.schemas.user import UserCreate, UserRead
from app.services.exceptions import InvalidCredentialsError
from app.services.jwt_service import JWTService
from app.services.security import hash_password, verify_password
from app.services.user_service import UserService


class AuthService:
    def __init__(self, user_service: UserService, jwt_service: JWTService) -> None:
        self.user_service = user_service
        self.jwt_service = jwt_service

    async def register(self, data: RegisterRequest) -> UserRead:
        password_hash = hash_password(data.password)
        user_create = UserCreate(
            username=data.username,
            email=data.email,
            password_hash=password_hash,
        )
        return await self.user_service.create(data=user_create)

    async def authenticate(self, data: LoginRequest) -> TokenResponse:
        user = await self.user_service.get_auth_user_by_username(data.username)
        if user is None or not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError

        await self.user_service.touch_last_login(user.id)

        token_data = self.jwt_service.create_access_token(
            {
                "sub": str(user.id),
                "username": user.username,
            }
        )
        return TokenResponse(
            access_token=token_data.token,
            exp=token_data.exp,
            iat=token_data.iat,
        )

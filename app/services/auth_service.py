from uuid import UUID

from app.core.config import JWTConfig
from app.domain.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserAuthRead,
    UserCreate,
    UserId,
    UserSelfRead,
)
from app.services.exceptions import InvalidCredentialsError, InvalidTokenError
from app.services.jwt_service import JWTService
from app.services.security import hash_password, verify_password
from app.services.user_service import UserService


class AuthService:
    def __init__(
        self,
        user_service: UserService,
        jwt_service: JWTService,
        jwt_config: JWTConfig,
    ) -> None:
        self.user_service = user_service
        self.jwt_service = jwt_service
        self.jwt_config = jwt_config

    async def register(self, data: RegisterRequest) -> UserSelfRead:
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

        token_data = self.jwt_service.create_token(
            {
                "sub": str(user.id),
                "username": user.username,
                "type": "access",
            },
            expire_minutes=self.jwt_config.access_token_expire_minutes,
        )
        return TokenResponse(
            access_token=token_data.token,
            exp=token_data.exp,
            iat=token_data.iat,
        )

    async def get_current_user_by_token(self, token: str) -> UserAuthRead:
        user_id = self._verify_access_token(token)
        return await self.user_service.get_auth_user_by_id(user_id)

    def _verify_access_token(self, token: str) -> UserId:
        payload = self.jwt_service.decode_token(token)

        if payload.get("type") != "access":
            msg = "Invalid token type. Expected 'access'"
            raise InvalidTokenError(msg)

        subject = payload.get("sub")
        if not subject:
            msg = "Token missing required 'sub' claim"
            raise InvalidTokenError(msg)

        try:
            return UserId(UUID(subject))
        except ValueError as err:
            msg = "Invalid UUID in token subject"
            raise InvalidTokenError(msg) from err

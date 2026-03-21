import pytest

from app.domain.schemas import LoginRequest, RegisterRequest, UserCreate
from app.services import (
    AuthService,
    InvalidCredentialsError,
    InvalidTokenError,
    UserService,
    hash_password,
)
from app.services import (
    EmailAlreadyExistsError as ServiceEmailAlreadyExistsError,
)
from app.services import (
    UsernameAlreadyExistsError as ServiceUsernameAlreadyExistsError,
)
from app.services.jwt_service import JWTService
from tests.fixtures.jwt import TEST_AUTH_JWT
from tests.unit.fakes.user_repository import InMemoryUserRepository


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def user_service(user_repository: InMemoryUserRepository) -> UserService:
    return UserService(user_repository)


@pytest.fixture
def jwt_service() -> JWTService:
    return JWTService(TEST_AUTH_JWT)


@pytest.fixture
def auth_service(user_service: UserService, jwt_service: JWTService) -> AuthService:
    return AuthService(user_service, jwt_service)


@pytest.fixture
def register_request() -> RegisterRequest:
    return RegisterRequest(
        username="valid.user",
        email="user@example.com",
        password="StrongPass1!",
        repeat_password="StrongPass1!",
    )


@pytest.mark.anyio
async def test_auth_service_register_creates_user(
    auth_service: AuthService,
    user_repository: InMemoryUserRepository,
    register_request: RegisterRequest,
) -> None:
    user = await auth_service.register(register_request)

    stored_user = await user_repository.get_auth_by_username(register_request.username)

    assert user.username == register_request.username
    assert stored_user is not None
    assert stored_user.password_hash != register_request.password


@pytest.mark.anyio
async def test_auth_service_register_rejects_duplicate_username(
    auth_service: AuthService,
    register_request: RegisterRequest,
) -> None:
    await auth_service.register(register_request)

    with pytest.raises(ServiceUsernameAlreadyExistsError):
        await auth_service.register(
            register_request.model_copy(update={"email": "other@example.com"})
        )


@pytest.mark.anyio
async def test_auth_service_register_rejects_duplicate_email(
    auth_service: AuthService,
    register_request: RegisterRequest,
) -> None:
    await auth_service.register(register_request)

    with pytest.raises(ServiceEmailAlreadyExistsError):
        await auth_service.register(register_request.model_copy(update={"username": "other.user"}))


@pytest.mark.anyio
async def test_auth_service_authenticate_returns_token(
    auth_service: AuthService,
    jwt_service: JWTService,
    user_repository: InMemoryUserRepository,
) -> None:
    password = "StrongPass1!"
    created_user = await user_repository.create(
        UserCreate(
            username="valid.user",
            email="user@example.com",
            password_hash=hash_password(password),
        )
    )

    token_response = await auth_service.authenticate(
        LoginRequest(username="valid.user", password=password)
    )

    payload = jwt_service.decode_access_token(token_response.access_token)
    auth_user = await user_repository.get_auth_by_username("valid.user")

    assert token_response.token_type == "Bearer"
    assert token_response.exp > token_response.iat
    assert payload["sub"] == str(created_user.id)
    assert payload["username"] == created_user.username
    assert auth_user is not None
    assert auth_user.last_login_at is not None


@pytest.mark.anyio
async def test_auth_service_authenticate_rejects_invalid_credentials(
    auth_service: AuthService,
    user_repository: InMemoryUserRepository,
) -> None:
    await user_repository.create(
        UserCreate(
            username="valid.user",
            email="user@example.com",
            password_hash=hash_password("StrongPass1!"),
        )
    )

    with pytest.raises(InvalidCredentialsError, match="Invalid username or password"):
        await auth_service.authenticate(LoginRequest(username="valid.user", password="WrongPass1!"))


@pytest.mark.anyio
async def test_auth_service_authenticate_rejects_missing_user(
    auth_service: AuthService,
) -> None:
    with pytest.raises(InvalidCredentialsError, match="Invalid username or password"):
        await auth_service.authenticate(
            LoginRequest(username="missing.user", password="StrongPass1!")
        )


@pytest.mark.anyio
async def test_auth_service_authenticate_rejects_soft_deleted_user(
    auth_service: AuthService,
    user_repository: InMemoryUserRepository,
) -> None:
    created_user = await user_repository.create(
        UserCreate(
            username="valid.user",
            email="user@example.com",
            password_hash=hash_password("StrongPass1!"),
        )
    )
    await user_repository.soft_delete(created_user.id)

    with pytest.raises(InvalidCredentialsError, match="Invalid username or password"):
        await auth_service.authenticate(
            LoginRequest(username="valid.user", password="StrongPass1!")
        )


def test_jwt_service_decode_access_token_rejects_invalid_token(
    jwt_service: JWTService,
) -> None:
    with pytest.raises(InvalidTokenError, match="Invalid access token"):
        jwt_service.decode_access_token("invalid-token")

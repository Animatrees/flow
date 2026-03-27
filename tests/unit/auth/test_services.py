import pytest

from app.domain.schemas import LoginRequest, RegisterRequest, UserCreate
from app.services import (
    AuthService,
    InvalidCredentialsError,
    InvalidTokenError,
    UserLifecycleService,
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
from tests.fixtures.jwt import TEST_JWT_CONFIG
from tests.unit.fakes.project_repository import InMemoryProjectRepository
from tests.unit.fakes.user_repository import InMemoryUserRepository


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def user_service(user_repository: InMemoryUserRepository) -> UserService:
    lifecycle_service = UserLifecycleService(user_repository, InMemoryProjectRepository())
    return UserService(user_repository, lifecycle_service)


@pytest.fixture
def jwt_service() -> JWTService:
    return JWTService(TEST_JWT_CONFIG)


@pytest.fixture
def auth_service(user_service: UserService, jwt_service: JWTService) -> AuthService:
    return AuthService(user_service, jwt_service, TEST_JWT_CONFIG)


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

    stored_user = await user_repository.get_active_by_username(register_request.username)

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

    payload = jwt_service.decode_token(token_response.access_token)
    auth_user = await user_repository.get_active_by_username("valid.user")

    assert token_response.token_type == "Bearer"
    assert token_response.exp > token_response.iat
    assert payload["sub"] == str(created_user.id)
    assert payload["type"] == "access"
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
    with pytest.raises(InvalidTokenError, match="Invalid token"):
        jwt_service.decode_token("invalid-token")


@pytest.mark.anyio
async def test_auth_service_get_current_user_by_token_returns_user(
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
    token = auth_service.jwt_service.create_token(
        {
            "sub": str(created_user.id),
            "username": created_user.username,
            "type": "access",
        },
        expire_minutes=TEST_JWT_CONFIG.access_token_expire_minutes,
    ).token

    current_user = await auth_service.get_current_user_by_token(token)

    assert current_user.id == created_user.id
    assert current_user.username == created_user.username


@pytest.mark.anyio
async def test_auth_service_get_current_user_by_token_rejects_wrong_token_type(
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
    token = auth_service.jwt_service.create_token(
        {
            "sub": str(created_user.id),
            "type": "upload",
        },
        expire_minutes=TEST_JWT_CONFIG.upload_token_expire_minutes,
    ).token

    with pytest.raises(InvalidTokenError, match="Invalid token type"):
        await auth_service.get_current_user_by_token(token)


@pytest.mark.anyio
async def test_auth_service_get_current_user_by_token_rejects_missing_subject(
    auth_service: AuthService,
) -> None:
    token = auth_service.jwt_service.create_token(
        {"type": "access"},
        expire_minutes=TEST_JWT_CONFIG.access_token_expire_minutes,
    ).token

    with pytest.raises(InvalidTokenError, match="Token missing required 'sub' claim"):
        await auth_service.get_current_user_by_token(token)


@pytest.mark.anyio
async def test_auth_service_get_current_user_by_token_rejects_invalid_subject_uuid(
    auth_service: AuthService,
) -> None:
    token = auth_service.jwt_service.create_token(
        {
            "sub": "not-a-uuid",
            "type": "access",
        },
        expire_minutes=TEST_JWT_CONFIG.access_token_expire_minutes,
    ).token

    with pytest.raises(InvalidTokenError, match="Invalid UUID in token subject"):
        await auth_service.get_current_user_by_token(token)

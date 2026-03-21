import pytest
from pydantic import ValidationError

from app.domain.schemas import UserCreate, UserUpdate

VALID_USERNAME = "valid.user"
VALID_EMAIL = "user@example.com"
VALID_PASSWORD_HASH = "hashed-password"


def test_user_create_accepts_internal_payload():
    user = UserCreate(
        username=VALID_USERNAME,
        email=VALID_EMAIL,
        password_hash=VALID_PASSWORD_HASH,
    )

    assert user.username == VALID_USERNAME
    assert user.email == VALID_EMAIL
    assert user.password_hash == VALID_PASSWORD_HASH


@pytest.mark.parametrize(
    "username",
    [
        "invalid user",  # space
        "user@name",  # @
        "user#name",  # #
        "пользователь",  # cyrillic
    ],
)
def test_user_create_rejects_invalid_username(username: str):
    with pytest.raises(
        ValidationError,
        match="Username may contain only letters, digits, dots, underscores, and hyphens",
    ):
        UserCreate(
            username=username,
            email=VALID_EMAIL,
            password_hash=VALID_PASSWORD_HASH,
        )


@pytest.mark.parametrize(
    "email",
    [
        "invalid-email",
        "missing@",
        "@nodomain.com",
        "no-at-sign",
        "",
    ],
)
def test_user_create_rejects_invalid_email(email: str):
    with pytest.raises(ValidationError):
        UserCreate(
            username=VALID_USERNAME,
            email=email,
            password_hash=VALID_PASSWORD_HASH,
        )


def test_user_update_allows_partial_payload():
    user_update = UserUpdate(email=VALID_EMAIL)

    assert user_update.email == VALID_EMAIL
    assert user_update.username is None


def test_user_update_normalizes_email_to_lowercase():
    user_update = UserUpdate(email="User@Example.COM")

    assert user_update.email == "user@example.com"


def test_user_update_accepts_empty_payload():
    user_update = UserUpdate()

    assert user_update.model_dump(exclude_unset=True) == {}


def test_user_update_reuses_username_validation():
    with pytest.raises(
        ValidationError,
        match="Username may contain only letters, digits, dots, underscores, and hyphens",
    ):
        UserUpdate(username="invalid user")


def test_user_update_reuses_email_validation():
    with pytest.raises(ValidationError):
        UserUpdate(email="invalid-email")

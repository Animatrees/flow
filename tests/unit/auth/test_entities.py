import pytest
from pydantic import ValidationError

from app.services.entities import UserCreate

VALID_USERNAME = "valid.user"
VALID_EMAIL = "user@example.com"
VALID_PASSWORD = "StrongPass1!"


@pytest.fixture
def valid_user_data() -> dict:
    return {
        "username": VALID_USERNAME,
        "password": VALID_PASSWORD,
        "repeat_password": VALID_PASSWORD,
        "email": VALID_EMAIL,
    }


@pytest.fixture
def valid_user(valid_user_data: dict) -> UserCreate:
    return UserCreate(**valid_user_data)


def test_user_create_accepts_valid_payload(valid_user: UserCreate):
    assert valid_user.username == VALID_USERNAME
    assert valid_user.email == VALID_EMAIL


@pytest.mark.parametrize(
    "username",
    [
        "invalid user",  # space
        "user@name",  # @
        "user#name",  # #
        "пользователь",  # cyrillic
    ],
)
def test_username_rejects_invalid_characters(valid_user_data: dict, username: str):
    with pytest.raises(
        ValidationError,
        match="Username may contain only letters, digits, dots, underscores, and hyphens",
    ):
        UserCreate(**{**valid_user_data, "username": username})


@pytest.mark.parametrize(
    ("password", "missing_requirement"),
    [
        ("NOLOWERCASE1!", "at least one lowercase letter"),
        ("nouppercase1!", "at least one uppercase letter"),
        ("NoDigitsHere!", "at least one digit"),
        ("NoSpecial123A", "at least one special character"),
    ],
)
def test_password_rejects_missing_each_requirement(
    valid_user_data: dict, password: str, missing_requirement: str
):
    with pytest.raises(ValidationError, match=missing_requirement):
        UserCreate(**{**valid_user_data, "password": password, "repeat_password": password})


def test_password_accumulates_multiple_errors(valid_user_data: dict):
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(**{**valid_user_data, "password": "weakpass", "repeat_password": "weakpass"})

    error_text = str(exc_info.value)
    assert "at least one uppercase letter" in error_text
    assert "at least one digit" in error_text
    assert "at least one special character" in error_text


def test_password_match_rejects_mismatch(valid_user_data: dict):
    with pytest.raises(ValidationError, match="Passwords do not match"):
        UserCreate(**{**valid_user_data, "repeat_password": "AnotherPass1!"})


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
def test_email_rejects_invalid_format(valid_user_data: dict, email: str):
    with pytest.raises(ValidationError):
        UserCreate(**{**valid_user_data, "email": email})

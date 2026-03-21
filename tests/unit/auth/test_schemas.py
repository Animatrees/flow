import pytest
from pydantic import ValidationError

from app.domain.schemas import LoginRequest, RegisterRequest

VALID_USERNAME = "valid.user"
VALID_EMAIL = "user@example.com"
VALID_PASSWORD = "StrongPass1!"


@pytest.fixture
def valid_register_data() -> dict:
    return {
        "username": VALID_USERNAME,
        "password": VALID_PASSWORD,
        "repeat_password": VALID_PASSWORD,
        "email": VALID_EMAIL,
    }


@pytest.fixture
def valid_register_request(valid_register_data: dict) -> RegisterRequest:
    return RegisterRequest(**valid_register_data)


def test_register_request_accepts_valid_payload(valid_register_request: RegisterRequest):
    assert valid_register_request.username == VALID_USERNAME
    assert valid_register_request.email == VALID_EMAIL
    assert valid_register_request.password == VALID_PASSWORD


@pytest.mark.parametrize(
    "username",
    [
        "invalid user",  # space
        "user@name",  # @
        "user#name",  # #
        "пользователь",  # cyrillic
    ],
)
def test_username_rejects_invalid_characters(valid_register_data: dict, username: str):
    with pytest.raises(
        ValidationError,
        match="Username may contain only letters, digits, dots, underscores, and hyphens",
    ):
        RegisterRequest(**{**valid_register_data, "username": username})


@pytest.mark.parametrize(
    "password",
    [
        "NOLOWERCASE1!",
        "nouppercase1!",
        "NoDigitsHere!",
        "NoSpecial123A",
        "StrongPass1 ",
    ],
)
def test_password_accepts_strong_passwords_without_character_class_rules(
    valid_register_data: dict, password: str
):
    register_request = RegisterRequest(
        **{**valid_register_data, "password": password, "repeat_password": password}
    )

    assert register_request.password == password


def test_password_rejects_weak_password_with_zxcvbn_feedback(valid_register_data: dict):
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            **{**valid_register_data, "password": "password", "repeat_password": "password"}
        )

    error_text = str(exc_info.value)
    assert "Password is too weak." in error_text
    assert "top-10 common password" in error_text
    assert "Add another word or two. Uncommon words are better." in error_text


def test_password_match_rejects_mismatch(valid_register_data: dict):
    with pytest.raises(ValidationError, match="Passwords do not match"):
        RegisterRequest(**{**valid_register_data, "repeat_password": "AnotherPass1!"})


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
def test_email_rejects_invalid_format(valid_register_data: dict, email: str):
    with pytest.raises(ValidationError):
        RegisterRequest(**{**valid_register_data, "email": email})


def test_password_rejects_password_similar_to_user_inputs(valid_register_data: dict):
    weak_password = "valid.user123"

    with pytest.raises(ValidationError, match=r"Password is too weak."):
        RegisterRequest(
            **{
                **valid_register_data,
                "password": weak_password,
                "repeat_password": weak_password,
            }
        )


def test_login_request_normalizes_username_to_lowercase():
    login_request = LoginRequest(username="Valid.User", password="StrongPass1!")

    assert login_request.username == "valid.user"

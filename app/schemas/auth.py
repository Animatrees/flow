from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
    model_validator,
)

from app.schemas.user import Username


def validate_password_strength(value: str) -> str:
    errors: list[str] = []
    if not any(char.islower() for char in value):
        errors.append("at least one lowercase letter")
    if not any(char.isupper() for char in value):
        errors.append("at least one uppercase letter")
    if not any(char.isdigit() for char in value):
        errors.append("at least one digit")
    if not any(not char.isalnum() for char in value):
        errors.append("at least one special character")
    if errors:
        raise ValueError("Password must contain " + ", ".join(errors) + ".")
    return value


type StrongPassword = Annotated[
    str,
    StringConstraints(min_length=8, max_length=128),
    AfterValidator(validate_password_strength),
]


class RegisterRequest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    username: Username
    password: StrongPassword
    repeat_password: str
    email: EmailStr

    @model_validator(mode="after")
    def validate_password_match(self) -> Self:
        if self.password != self.repeat_password:
            msg = "Passwords do not match."
            raise ValueError(msg)
        return self


class LoginRequest(BaseModel):
    username: str
    password: str

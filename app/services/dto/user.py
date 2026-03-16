import re
from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
    model_validator,
)

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.\-]+$")


def validate_username_format(value: str) -> str:
    if not _USERNAME_RE.match(value):
        msg = "Username may contain only letters, digits, dots, underscores, and hyphens."
        raise ValueError(msg)
    return value


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


type Username = Annotated[
    str,
    StringConstraints(min_length=3, max_length=50),
    AfterValidator(validate_username_format),
]

type StrongPassword = Annotated[
    str,
    StringConstraints(min_length=8, max_length=128),
    AfterValidator(validate_password_strength),
]


class UserCreate(BaseModel):
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


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    created_at: datetime

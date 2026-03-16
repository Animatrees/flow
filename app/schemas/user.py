import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
)

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.\-]+$")


def validate_username_format(value: str) -> str:
    if not _USERNAME_RE.match(value):
        msg = "Username may contain only letters, digits, dots, underscores, and hyphens."
        raise ValueError(msg)
    return value


type Username = Annotated[
    str,
    StringConstraints(min_length=3, max_length=50),
    AfterValidator(validate_username_format),
]


class UserCreate(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    username: Username
    email: EmailStr
    password_hash: str


class UserUpdate(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    username: Username | None = None
    email: EmailStr | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    created_at: datetime

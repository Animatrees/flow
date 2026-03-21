import re
from datetime import datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
)

from app.domain.schemas.type_ids import UserId

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.\-]+$")


def to_lower(value: str) -> str:
    return value.lower()


def validate_username_format(value: str) -> str:
    if not _USERNAME_RE.match(value):
        msg = "Username may contain only letters, digits, dots, underscores, and hyphens."
        raise ValueError(msg)
    return value


type Username = Annotated[
    str,
    StringConstraints(min_length=3, max_length=50),
    AfterValidator(validate_username_format),
    AfterValidator(to_lower),
]

type LowerEmail = Annotated[EmailStr, AfterValidator(to_lower)]


class UserCreate(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    username: Username
    email: LowerEmail
    password_hash: str


class UserUpdate(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    username: Username | None = None
    email: LowerEmail | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UserId
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


class UserAuthRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UserId
    username: str
    email: str
    password_hash: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None
    deleted_at: datetime | None

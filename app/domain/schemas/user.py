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
    """Schema for creating a persisted user record."""

    model_config = ConfigDict(strict=True, frozen=True)

    username: Username
    email: LowerEmail
    password_hash: str


class UserUpdate(BaseModel):
    """Schema for self-service user profile updates."""

    model_config = ConfigDict(strict=True, frozen=True)

    username: Username | None = None
    email: LowerEmail | None = None


class UserAdminUpdate(UserUpdate):
    """Schema for admin-only user updates."""

    model_config = ConfigDict(strict=True, frozen=True)

    is_superuser: bool | None = None
    is_active: bool | None = None


class StoredUser(BaseModel):
    """Schema for a persisted user record."""

    model_config = ConfigDict(from_attributes=True)

    id: UserId
    username: str
    email: str
    password_hash: str
    is_superuser: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None
    deleted_at: datetime | None


class UserPublicRead(BaseModel):
    """Schema for the public user view."""

    model_config = ConfigDict(from_attributes=True)

    id: UserId
    username: str
    last_login_at: datetime | None


class UserSelfRead(UserPublicRead):
    """Schema for the self-service user view."""

    email: str
    created_at: datetime
    updated_at: datetime


class UserAdminRead(UserSelfRead):
    """Schema for the administrative user view."""

    is_superuser: bool
    is_active: bool
    deleted_at: datetime | None


class UserAuthRead(UserAdminRead):
    """Schema for user data used during authentication and authorization."""

    password_hash: str

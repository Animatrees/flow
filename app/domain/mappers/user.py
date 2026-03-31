from app.domain.schemas.user import (
    StoredUser,
    UserAdminRead,
    UserAuthRead,
    UserPublicRead,
    UserSelfRead,
)


class UserMapper:
    """Mapper for stored user records and API-facing schema variants."""

    @staticmethod
    def to_public(user: StoredUser) -> UserPublicRead:
        return UserPublicRead.model_validate(user)

    @staticmethod
    def to_self(user: StoredUser) -> UserSelfRead:
        return UserSelfRead.model_validate(user)

    @staticmethod
    def to_auth(user: StoredUser) -> UserAuthRead:
        return UserAuthRead.model_validate(user)

    @staticmethod
    def to_admin(user: StoredUser) -> UserAdminRead:
        return UserAdminRead.model_validate(user)

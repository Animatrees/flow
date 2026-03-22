from app.domain.schemas.user import (
    UserAdminRead,
    UserAuthRead,
    UserData,
    UserPublicRead,
    UserSelfRead,
)


class UserMapper:
    @staticmethod
    def to_public(user: UserData) -> UserPublicRead:
        return UserPublicRead.model_validate(user)

    @staticmethod
    def to_self(user: UserData) -> UserSelfRead:
        return UserSelfRead.model_validate(user)

    @staticmethod
    def to_auth(user: UserData) -> UserAuthRead:
        return UserAuthRead.model_validate(user)

    @staticmethod
    def to_admin(user: UserData) -> UserAdminRead:
        return UserAdminRead.model_validate(user)

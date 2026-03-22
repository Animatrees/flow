from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import AuthJWT
from app.services.exceptions import InvalidTokenError


@dataclass
class TokenData:
    token: str
    exp: int
    iat: int


class JWTService:
    def __init__(self, config: AuthJWT) -> None:
        self.config = config
        self.private_key = config.private_key_path.read_text()
        self.public_key = config.public_key_path.read_text()
        self.algorithm = config.algorithm

    def create_access_token(self, payload: dict) -> TokenData:
        to_encode = payload.copy()
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self.config.access_token_expire_minutes)
        to_encode.update(
            exp=expire,
            iat=now,
        )
        encoded = jwt.encode(to_encode, self.private_key, algorithm=self.config.algorithm)
        return TokenData(
            token=encoded,
            exp=int(expire.timestamp()),
            iat=int(now.timestamp()),
        )

    def decode_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
            )
        except jwt.InvalidTokenError as err:
            raise InvalidTokenError from err

        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise InvalidTokenError

        return payload

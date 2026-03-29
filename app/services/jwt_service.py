from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import JWTConfig
from app.services.exceptions import InvalidTokenError


@dataclass
class TokenData:
    token: str
    exp: int
    iat: int


class JWTService:
    def __init__(self, config: JWTConfig) -> None:
        self.config = config
        self.private_key = config.private_key_path.read_text()
        self.public_key = config.public_key_path.read_text()

    def create_token(self, payload: dict, expire_minutes: int) -> TokenData:
        to_encode = payload.copy()
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=expire_minutes)
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

    def decode_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.config.algorithm],
            )
        except jwt.InvalidTokenError as err:
            raise InvalidTokenError from err

        return payload

from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)
from zxcvbn import zxcvbn

from app.domain.schemas.user import LowerEmail, Username


class RegisterRequest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    username: Username
    password: Annotated[str, StringConstraints(min_length=8, max_length=128)]
    repeat_password: str
    email: LowerEmail

    @model_validator(mode="after")
    def validate_password_match(self) -> Self:
        if self.password != self.repeat_password:
            msg = "Passwords do not match."
            raise ValueError(msg)

        result = zxcvbn(self.password, user_inputs=[self.username, self.email])
        min_score = 2
        if result["score"] < min_score:
            feedback = result["feedback"]
            parts = ["Password is too weak."]
            if feedback.get("warning"):
                parts.append(feedback["warning"])
            if feedback.get("suggestions"):
                parts.extend(feedback["suggestions"])
            raise ValueError(" ".join(parts))

        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    username: Username
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = Field(default="Bearer")
    exp: int
    iat: int

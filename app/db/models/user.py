from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base
from app.db.models.mixins import UUIDPkMixin


class User(Base, UUIDPkMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    __table_args__ = (
        CheckConstraint("char_length(username) >= 3", name="username_min_length"),
        CheckConstraint("username = lower(username)", name="username_is_lower"),
        CheckConstraint("email = lower(email)", name="email_is_lower"),
    )

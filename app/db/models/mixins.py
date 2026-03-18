import uuid

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid
from uuid_extensions import uuid7


class IntIdPkMixin:
    id: Mapped[int] = mapped_column(primary_key=True)


class UUIDPkMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

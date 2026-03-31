import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models import Base
from app.db.models.mixins import TimestampMixin, UUIDPkMixin
from app.domain.schemas import ProjectStatus


def project_status_values(_: type[ProjectStatus]) -> list[str]:
    return [status.value for status in ProjectStatus]


class Project(Base, UUIDPkMixin, TimestampMixin):
    """Database model for projects."""

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String, default="")
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(
            ProjectStatus,
            name="project_status",
            create_constraint=True,
            validate_strings=True,
            values_callable=project_status_values,
        )
    )

    __table_args__ = (CheckConstraint("end_date >= start_date", name="project_dates_valid"),)

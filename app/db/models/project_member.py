import uuid

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.models import Base
from app.db.models.mixins import CreatedAtMixin
from app.domain.schemas import ProjectMemberRole


def project_member_role_values(_: type[ProjectMemberRole]) -> list[str]:
    return [role.value for role in ProjectMemberRole]


class ProjectMember(Base, CreatedAtMixin):
    """Database model for project membership records."""

    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    role: Mapped[ProjectMemberRole] = mapped_column(
        Enum(
            ProjectMemberRole,
            name="project_member_role",
            create_constraint=True,
            validate_strings=True,
            values_callable=project_member_role_values,
        )
    )

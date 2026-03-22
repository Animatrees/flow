"""Add project member roles and owner memberships.

Revision ID: 3c4d5e6f7a8b
Revises: b3d0f8f6a2c1
Create Date: 2026-03-22 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.domain.schemas import ProjectMemberRole


def project_member_role_values(_: type[ProjectMemberRole]) -> list[str]:
    return [role.value for role in ProjectMemberRole]


# revision identifiers, used by Alembic.
revision: str = "3c4d5e6f7a8b"
down_revision: str | Sequence[str] | None = "b3d0f8f6a2c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

project_member_role_enum = sa.Enum(
    ProjectMemberRole,
    name="project_member_role",
    create_constraint=True,
    validate_strings=True,
    values_callable=project_member_role_values,
)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "project_members",
        sa.Column("role", project_member_role_enum, nullable=True),
    )

    op.execute(
        sa.text("UPDATE project_members SET role = :member_role WHERE role IS NULL").bindparams(
            member_role=ProjectMemberRole.MEMBER.value
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO project_members (project_id, user_id, role) "
            "SELECT id, owner_id, :owner_role "
            "FROM projects "
            "WHERE NOT EXISTS ("
            "    SELECT 1 "
            "    FROM project_members "
            "    WHERE project_members.project_id = projects.id "
            "      AND project_members.user_id = projects.owner_id"
            ")"
        ).bindparams(owner_role=ProjectMemberRole.OWNER.value)
    )

    with op.batch_alter_table("project_members") as batch_op:
        batch_op.alter_column("role", nullable=False)

    op.create_index(
        "ux_project_members_owner_per_project",
        "project_members",
        ["project_id"],
        unique=True,
        sqlite_where=sa.text("role = 'owner'"),
        postgresql_where=sa.text("role = 'owner'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ux_project_members_owner_per_project", table_name="project_members")
    op.execute(sa.text("DELETE FROM project_members WHERE role = 'owner'"))

    with op.batch_alter_table("project_members") as batch_op:
        batch_op.drop_column("role")

    project_member_role_enum.drop(op.get_bind(), checkfirst=True)

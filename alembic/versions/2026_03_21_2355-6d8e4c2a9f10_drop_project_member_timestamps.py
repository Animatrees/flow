"""Drop timestamp columns from project_members.

Revision ID: 6d8e4c2a9f10
Revises: 85814c1e6c19
Create Date: 2026-03-21 23:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6d8e4c2a9f10"
down_revision: str | Sequence[str] | None = "85814c1e6c19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("project_members") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("project_members") as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            )
        )

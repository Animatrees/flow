"""add is_superuser to users.

Revision ID: b3d0f8f6a2c1
Revises: 6d8e4c2a9f10
Create Date: 2026-03-22 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3d0f8f6a2c1"
down_revision: str | Sequence[str] | None = "6d8e4c2a9f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("is_superuser", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "is_superuser")

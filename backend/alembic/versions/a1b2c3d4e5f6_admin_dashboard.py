"""admin dashboard: user status/admin flag, agent_runs, audit_logs

Revision ID: a1b2c3d4e5f6
Revises: 9d3f2b7a1c45
Create Date: 2026-11-08 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9d3f2b7a1c45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(), server_default="active", nullable=False)
        )
        batch_op.add_column(
            sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False)
        )
        batch_op.add_column(
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True)
        )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("agent_runs", schema=None) as batch_op:
        for col in ("id", "kind", "name", "status", "created_at"):
            batch_op.create_index(
                batch_op.f(f"ix_agent_runs_{col}"), [col], unique=False
            )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("admin_email", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        for col in ("id", "admin_id", "action", "created_at"):
            batch_op.create_index(
                batch_op.f(f"ix_audit_logs_{col}"), [col], unique=False
            )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("agent_runs")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("is_admin")
        batch_op.drop_column("status")

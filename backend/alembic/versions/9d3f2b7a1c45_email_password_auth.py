"""email password auth

Revision ID: 9d3f2b7a1c45
Revises: 7c1e5d2a9b34
Create Date: 2026-11-02 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9d3f2b7a1c45'
down_revision: Union[str, Sequence[str], None] = '7c1e5d2a9b34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('email_otps',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('code_hash', sa.String(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_sent_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('email_otps', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_email_otps_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_email_otps_id'), ['id'], unique=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('password_hash', sa.String(), nullable=True))
        batch_op.drop_index(batch_op.f('ix_users_google_id'))
        batch_op.drop_column('google_id')
        batch_op.drop_column('picture')


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('picture', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('google_id', sa.String(), nullable=True))
        batch_op.drop_column('password_hash')

    with op.batch_alter_table('email_otps', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_email_otps_id'))
        batch_op.drop_index(batch_op.f('ix_email_otps_email'))
    op.drop_table('email_otps')

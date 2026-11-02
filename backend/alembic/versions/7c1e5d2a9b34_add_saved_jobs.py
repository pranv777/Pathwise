"""add saved_jobs

Revision ID: 7c1e5d2a9b34
Revises: 4b80596c7999
Create Date: 2026-11-01 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7c1e5d2a9b34'
down_revision: Union[str, Sequence[str], None] = '4b80596c7999'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('saved_jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('company', sa.String(), nullable=False),
    sa.Column('location', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('source', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'job_id', name='uq_saved_jobs_user_job')
    )
    with op.batch_alter_table('saved_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_saved_jobs_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_saved_jobs_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('saved_jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_saved_jobs_user_id'))
        batch_op.drop_index(batch_op.f('ix_saved_jobs_id'))

    op.drop_table('saved_jobs')

"""Add paths table

Revision ID: a3c1d8e2f901
Revises: f602b0b76ed4
Create Date: 2026-02-18 22:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c1d8e2f901'
down_revision: Union[str, Sequence[str], None] = 'f602b0b76ed4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create paths table."""
    op.create_table(
        'paths',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('subdomain_id', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('content_length', sa.Integer(), nullable=True),
        sa.Column('discovered_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['subdomain_id'], ['subdomains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_paths_subdomain_id'), 'paths', ['subdomain_id'], unique=False)


def downgrade() -> None:
    """Drop paths table."""
    op.drop_index(op.f('ix_paths_subdomain_id'), table_name='paths')
    op.drop_table('paths')

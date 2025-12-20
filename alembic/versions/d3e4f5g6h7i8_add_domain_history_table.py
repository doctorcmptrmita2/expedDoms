"""Add domain_history table

Revision ID: d3e4f5g6h7i8
Revises: c2d3e4f5g6h7
Create Date: 2025-12-11 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e4f5g6h7i8'
down_revision: Union[str, None] = 'c2d3e4f5g6h7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'domain_histories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(191), nullable=False),  # 191 for MySQL utf8mb4 index
        # Wayback Machine data
        sa.Column('wayback_snapshots', sa.Integer(), nullable=False, default=0),
        sa.Column('wayback_first_snapshot', sa.Date(), nullable=True),
        sa.Column('wayback_last_snapshot', sa.Date(), nullable=True),
        sa.Column('archive_url', sa.String(500), nullable=True),
        # Whois data
        sa.Column('first_registered', sa.Date(), nullable=True),
        sa.Column('last_updated', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('registrar', sa.String(255), nullable=True),
        # Previous owners (JSON)
        sa.Column('previous_owners', sa.JSON(), nullable=True),
        # Domain age
        sa.Column('domain_age_days', sa.Integer(), nullable=True),
        # Raw whois
        sa.Column('whois_raw', sa.Text(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_domain_histories_id'), 'domain_histories', ['id'], unique=False)
    op.create_index(op.f('ix_domain_histories_domain'), 'domain_histories', ['domain'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_domain_histories_domain'), table_name='domain_histories')
    op.drop_index(op.f('ix_domain_histories_id'), table_name='domain_histories')
    op.drop_table('domain_histories')


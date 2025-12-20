"""Add user tables

Revision ID: b1c2d3e4f5g6
Revises: ae3452e56c99
Create Date: 2025-12-11 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, None] = 'ae3452e56c99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_premium', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    # Use prefix length for indexes to avoid MySQL key length issues
    op.execute("CREATE UNIQUE INDEX ix_users_email ON users (email(191))")
    op.execute("CREATE UNIQUE INDEX ix_users_username ON users (username)")
    
    # Create user_watchlists table
    op.create_table(
        'user_watchlists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('domain_pattern', sa.String(255), nullable=True),
        sa.Column('tld_filter', sa.String(255), nullable=True),
        sa.Column('min_length', sa.Integer(), nullable=True),
        sa.Column('max_length', sa.Integer(), nullable=True),
        sa.Column('charset_filter', sa.String(50), nullable=True),
        sa.Column('min_quality_score', sa.Integer(), nullable=True),
        sa.Column('notify_email', sa.Boolean(), nullable=False, default=True),
        sa.Column('notify_telegram', sa.Boolean(), nullable=False, default=False),
        sa.Column('notify_discord', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_notified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_watchlists_id'), 'user_watchlists', ['id'], unique=False)
    op.create_index(op.f('ix_user_watchlists_user_id'), 'user_watchlists', ['user_id'], unique=False)
    
    # Create user_favorites table
    op.create_table(
        'user_favorites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('domain_id', sa.BigInteger(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['domain_id'], ['dropped_domains.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_favorites_id'), 'user_favorites', ['id'], unique=False)
    op.create_index(op.f('ix_user_favorites_user_id'), 'user_favorites', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_favorites_domain_id'), 'user_favorites', ['domain_id'], unique=False)
    op.create_index('idx_user_domain_favorite', 'user_favorites', ['user_id', 'domain_id'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_user_domain_favorite', table_name='user_favorites')
    op.drop_index(op.f('ix_user_favorites_domain_id'), table_name='user_favorites')
    op.drop_index(op.f('ix_user_favorites_user_id'), table_name='user_favorites')
    op.drop_index(op.f('ix_user_favorites_id'), table_name='user_favorites')
    op.drop_table('user_favorites')
    
    op.drop_index(op.f('ix_user_watchlists_user_id'), table_name='user_watchlists')
    op.drop_index(op.f('ix_user_watchlists_id'), table_name='user_watchlists')
    op.drop_table('user_watchlists')
    
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')


"""Add notification tables

Revision ID: c2d3e4f5g6h7
Revises: b1c2d3e4f5g6
Create Date: 2025-12-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5g6h7'
down_revision: Union[str, None] = 'b1c2d3e4f5g6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notification_settings table
    op.create_table(
        'notification_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        # Email settings
        sa.Column('email_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('email_address', sa.String(255), nullable=True),
        # Telegram settings
        sa.Column('telegram_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('telegram_chat_id', sa.String(100), nullable=True),
        sa.Column('telegram_bot_token', sa.String(255), nullable=True),
        # Discord settings
        sa.Column('discord_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('discord_webhook_url', sa.String(500), nullable=True),
        # Webhook settings
        sa.Column('webhook_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('webhook_url', sa.String(500), nullable=True),
        sa.Column('webhook_secret', sa.String(255), nullable=True),
        # Preferences
        sa.Column('notify_on_watchlist_match', sa.Boolean(), nullable=False, default=True),
        sa.Column('notify_daily_digest', sa.Boolean(), nullable=False, default=False),
        sa.Column('notify_premium_drops', sa.Boolean(), nullable=False, default=True),
        sa.Column('min_quality_score', sa.Integer(), nullable=False, default=0),
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_settings_id'), 'notification_settings', ['id'], unique=False)
    op.create_index(op.f('ix_notification_settings_user_id'), 'notification_settings', ['user_id'], unique=False)
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('subject', sa.String(255), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('data', sa.Text(), nullable=True),
        sa.Column('recipient', sa.String(500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_notifications_status'), 'notifications', ['status'], unique=False)
    op.create_index(op.f('ix_notifications_channel'), 'notifications', ['channel'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_notifications_channel'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_status'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_user_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_id'), table_name='notifications')
    op.drop_table('notifications')
    
    op.drop_index(op.f('ix_notification_settings_user_id'), table_name='notification_settings')
    op.drop_index(op.f('ix_notification_settings_id'), table_name='notification_settings')
    op.drop_table('notification_settings')







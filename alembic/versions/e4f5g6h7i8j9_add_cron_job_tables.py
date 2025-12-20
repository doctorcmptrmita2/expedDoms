"""Add cron job tables

Revision ID: e4f5g6h7i8j9
Revises: d3e4f5g6h7i8
Create Date: 2025-12-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4f5g6h7i8j9'
down_revision = 'd3e4f5g6h7i8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create cron_jobs table
    op.create_table(
        'cron_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('tld', sa.String(length=50), nullable=False),
        sa.Column('cron_hour', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('cron_minute', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('job_type', sa.Enum('DOWNLOAD_ONLY', 'PARSE_ONLY', 'FULL', name='jobtype'), nullable=False, server_default='FULL'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('timeout_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('next_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_status', sa.Enum('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', name='jobstatus'), nullable=False, server_default='PENDING'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('total_runs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cron_jobs_id'), 'cron_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_cron_jobs_tld'), 'cron_jobs', ['tld'], unique=False)
    
    # Create cron_job_logs table
    op.create_table(
        'cron_job_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('SUCCESS', 'FAILED', 'TIMEOUT', 'CANCELLED', name='logstatus'), nullable=False, server_default='SUCCESS'),
        sa.Column('domains_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('drops_detected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_size_mb', sa.Float(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('execution_time_sec', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['job_id'], ['cron_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cron_job_logs_id'), 'cron_job_logs', ['id'], unique=False)
    op.create_index(op.f('ix_cron_job_logs_job_id'), 'cron_job_logs', ['job_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_cron_job_logs_job_id'), table_name='cron_job_logs')
    op.drop_index(op.f('ix_cron_job_logs_id'), table_name='cron_job_logs')
    op.drop_table('cron_job_logs')
    
    op.drop_index(op.f('ix_cron_jobs_tld'), table_name='cron_jobs')
    op.drop_index(op.f('ix_cron_jobs_id'), table_name='cron_jobs')
    op.drop_table('cron_jobs')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS logstatus")
    op.execute("DROP TYPE IF EXISTS jobstatus")
    op.execute("DROP TYPE IF EXISTS jobtype")


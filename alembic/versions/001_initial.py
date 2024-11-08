"""initial

Revision ID: 001
Revises: 
Create Date: 2024-03-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create devices table
    op.create_table(
        'devices',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('phone_number', sa.String(), nullable=False),
        sa.Column('sim_iccid', sa.String(), nullable=True),
        sa.Column('signal_strength', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('first_seen', sa.DateTime(), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=False),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('signal_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('device_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create SMS messages table
    op.create_table(
        'sms_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.String(), nullable=False),
        sa.Column('from_number', sa.String(), nullable=False),
        sa.Column('to_number', sa.String(), nullable=False),
        sa.Column('text', sa.String(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False),
        sa.Column('delivered', sa.Boolean(), default=False),
        sa.Column('delivery_attempts', sa.Integer(), default=0),
        sa.Column('last_attempt', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('retry_after', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_devices_type', 'devices', ['type'])
    op.create_index('idx_devices_status', 'devices', ['status'])
    op.create_index('idx_sms_device', 'sms_messages', ['device_id'])
    op.create_index('idx_sms_delivered', 'sms_messages', ['delivered'])
    op.create_index('idx_sms_retry', 'sms_messages', ['retry_after'])

def downgrade() -> None:
    op.drop_table('sms_messages')
    op.drop_table('devices')
"""initial migration

Revision ID: initial_migration
Revises: 
Create Date: 2024-01-31 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = 'initial_migration'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create users table
    op.create_table(
        'user',
        sa.Column('id', sa.String(length=36), nullable=False),  # UUID as string for SQLite
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_superuser', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    
    # Create user profiles table
    op.create_table(
        'userprofile',
        sa.Column('id', sa.String(length=36), nullable=False),  # UUID as string for SQLite
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('notification_enabled', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create devices table
    op.create_table(
        'device',
        sa.Column('id', sa.String(length=36), nullable=False),  # UUID as string for SQLite
        sa.Column('device_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=False),
        sa.Column('is_online', sa.Boolean(), nullable=False),
        sa.Column('latest_image_path', sa.String(), nullable=True),
        sa.Column('alert_enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('owner_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_device_device_id'), 'device', ['device_id'], unique=False)
    
    # Create detections table
    op.create_table(
        'detection',
        sa.Column('id', sa.String(length=36), nullable=False),  # UUID as string for SQLite
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('detected', sa.Boolean(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.JSON(), nullable=False),
        sa.Column('frame_number', sa.Integer(), nullable=False),
        sa.Column('fps', sa.Float(), nullable=False),
        sa.Column('device_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['device.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('detection')
    op.drop_table('device')
    op.drop_table('userprofile')
    op.drop_table('user') 
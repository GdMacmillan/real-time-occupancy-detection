"""seed initial data

Revision ID: seed_initial_data
Revises: initial_migration
Create Date: 2024-01-31 14:01:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from uuid import uuid4
from datetime import datetime

# revision identifiers
revision = 'seed_initial_data'
down_revision = 'initial_migration'
branch_labels = None
depends_on = None

def upgrade() -> None:
    connection = op.get_bind()
    
    # Create test admin user
    user_id = str(uuid4())
    connection.execute(
        text("""
        INSERT INTO user (id, email, hashed_password, is_active, is_superuser, created_at, updated_at)
        VALUES (:id, :email, :hashed_password, :is_active, :is_superuser, :created_at, :updated_at)
        """),
        {
            "id": user_id,
            "email": "admin@example.com",
            "hashed_password": "dummy_hashed_password",
            "is_active": True,
            "is_superuser": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    )
    
    # Create admin profile
    connection.execute(
        text("""
        INSERT INTO userprofile (id, user_id, first_name, last_name, notification_enabled)
        VALUES (:id, :user_id, :first_name, :last_name, :notification_enabled)
        """),
        {
            "id": str(uuid4()),
            "user_id": user_id,
            "first_name": "Admin",
            "last_name": "User",
            "notification_enabled": True
        }
    )
    
    # Create test device
    connection.execute(
        text("""
        INSERT INTO device (
            id, device_id, name, type, is_online, alert_enabled,
            owner_id, created_at, last_seen
        )
        VALUES (
            :id, :device_id, :name, :type, :is_online, :alert_enabled,
            :owner_id, :created_at, :last_seen
        )
        """),
        {
            "id": str(uuid4()),
            "device_id": "cv_module_01",
            "name": "Test Camera",
            "type": "realsense",
            "is_online": False,
            "alert_enabled": True,
            "owner_id": user_id,
            "created_at": datetime.utcnow(),
            "last_seen": datetime.utcnow()
        }
    )

def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(text("DELETE FROM detection"))
    connection.execute(text("DELETE FROM device"))
    connection.execute(text("DELETE FROM userprofile"))
    connection.execute(text("DELETE FROM user")) 
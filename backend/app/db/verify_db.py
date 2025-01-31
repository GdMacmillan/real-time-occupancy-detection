from sqlmodel import Session, select
from ..models.user import User, UserProfile
from ..models.device import Device
from ..models.detection import Detection
from .session import engine

def verify_database():
    """Verify database setup and seeded data."""
    with Session(engine) as session:
        # Check User
        user = session.exec(select(User)).first()
        print("\nUser Check:")
        print(f"Email: {user.email}")
        print(f"Is Superuser: {user.is_superuser}")
        
        # Check UserProfile
        profile = session.exec(select(UserProfile)).first()
        print("\nProfile Check:")
        print(f"Name: {profile.first_name} {profile.last_name}")
        print(f"Notifications: {profile.notification_enabled}")
        
        # Check Device
        device = session.exec(select(Device)).first()
        print("\nDevice Check:")
        print(f"Name: {device.name}")
        print(f"Type: {device.type}")
        print(f"Device ID: {device.device_id}")
        
        # Check Relationships
        print("\nRelationship Check:")
        print(f"User -> Profile: {user.profile.first_name if user.profile else 'Not Found'}")
        print(f"User -> Devices: {len(user.devices)} device(s)")
        print(f"Device -> Owner: {device.owner.email if device.owner else 'Not Found'}")

if __name__ == "__main__":
    verify_database() 
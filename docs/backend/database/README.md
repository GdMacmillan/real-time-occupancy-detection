# Backend Database System

This document outlines the database architecture, setup procedures, and development workflows for the Real-Time Occupancy Detection system.

## Overview

The backend uses SQLite for development and testing, with SQLModel (SQLAlchemy + Pydantic) for ORM and Alembic for migrations. The system is designed to be easily migrated to PostgreSQL for production.

## Database Models

### Core Models
- `User`: Authentication and base user information
- `UserProfile`: Extended user details and preferences
- `Device`: Connected camera devices (webcam/RealSense)
- `Detection`: Occupancy detection events from devices

### Model Relationships
```
User
├── UserProfile (1:1)
└── Device (1:N)
    └── Detection (1:N)
```

## Getting Started

### Prerequisites
```bash
conda create -n real-time-occupancy python=3.11
conda activate real-time-occupancy
pip install sqlmodel alembic fastapi uvicorn
```

### Initial Setup
```bash
cd backend
alembic upgrade head
python -m app.db.verify_db
```

## Development Workflow

### Making Model Changes

1. Update model in `app/models/`:
```python
class Device(SQLModel, table=True):
    # Add or modify fields
    new_field: str = Field(default="value")
```

2. Create migration:
```bash
alembic revision --autogenerate -m "add new_field to device"
```

3. Review generated migration in `alembic/versions/`

4. Apply migration:
```bash
alembic upgrade head
```

### Project Structure
```
backend/
├── app/
│   ├── models/
│   │   ├── user.py      # User and UserProfile models
│   │   ├── device.py    # Device model
│   │   └── detection.py # Detection model
│   └── db/
│       ├── session.py   # Database session management
│       └── init_db.py   # Database initialization
└── alembic/
    ├── versions/        # Migration files
    └── env.py          # Alembic configuration
```

## Database Operations

### Migration Commands
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Revert last migration
alembic downgrade -1

# Show migration history
alembic history

# Show current version
alembic current
```

### Reset Database
```bash
# Remove database
rm occupancy.db

# Rerun migrations
alembic upgrade head
```

### Verify Setup
```bash
python -m app.db.verify_db
```

## Production Considerations

### Database Migration
For PostgreSQL deployment:

1. Update settings:
```python
DATABASE_URL = "postgresql://user:password@localhost/dbname"
```

2. Update UUID handling:
```python
from sqlalchemy.dialects.postgresql import UUID

id: UUID = Field(
    default_factory=uuid4,
    sa_column=Column(UUID(as_uuid=True), primary_key=True)
)
```

### Performance
- Configure connection pooling
- Set up database indexing
- Implement query optimization
- Configure proper caching

### Security
- Use environment variables for credentials
- Implement proper user authentication
- Set up database backups
- Configure SSL for database connections

## Troubleshooting

### Common Issues

1. **Migration Conflicts**
```bash
# Reset migrations
alembic downgrade base
alembic upgrade head
```

2. **Database Verification**
```bash
# Verify data integrity
python -m app.db.verify_db
```

3. **Schema Inspection**
```python
from sqlmodel import SQLModel
from app.models import User
print(User.schema())
```

### Logging

SQLAlchemy logging is enabled by default in development. Check the logs for:
- SQL queries
- Connection issues
- Migration errors

## Contributing

When making database changes:
1. Create feature branch
2. Update models
3. Generate and test migrations
4. Update documentation
5. Submit pull request

## References

- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/) 
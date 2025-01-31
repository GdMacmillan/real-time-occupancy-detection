from sqlmodel import SQLModel, create_engine
from ..core.config import get_settings

settings = get_settings()

def init_db():
    """Initialize the database."""
    engine = create_engine(settings.DATABASE_URL)
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    init_db() 
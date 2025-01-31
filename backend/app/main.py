from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import get_settings
from .core.logging import get_logger
import uvicorn

settings = get_settings()
logger = get_logger("backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    try:
        # Startup
        logger.info(f"Starting {settings.APP_NAME}")
        logger.info(f"Host: {settings.HOST}:{settings.PORT}")
        logger.info(f"WebSocket URL: {settings.WS_URL}")
        
        yield
        
        # Shutdown
        logger.info(f"Shutting down {settings.APP_NAME}")
    except Exception as e:
        logger.error(f"Lifespan error: {e}", exc_info=True)
        raise

# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for real-time occupancy detection",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from .api.v1.api import api_router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok"}

if __name__ == "__main__":

    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",  # Explicitly use localhost
        port=8000,
        reload=True
    )

    # or run directly with uvicorn:
    # # From project root
    # uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

    # # From backend directory
    # uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
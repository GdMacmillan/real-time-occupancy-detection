from fastapi import APIRouter
from .endpoints import detection, websocket

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    websocket.router,
    tags=["websocket"]
)

api_router.include_router(
    detection.router,
    prefix="/detections",
    tags=["detections"]
) 
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select
from ....core.config import get_settings
from ....db.session import get_session
from ....models.device import Device
from ....models.detection import Detection
import json
from datetime import datetime
import base64
import os
import websockets
from fastapi import Depends
from ....core.logging import get_logger
import asyncio
from typing import Optional
import time

router = APIRouter()
logger = get_logger("backend.websocket")
settings = get_settings()

# Connection retry settings
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 1  # seconds

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.message_count = 0
        self.cv_connection: Optional[websockets.WebSocketClientProtocol] = None
        self._cv_connection_task: Optional[asyncio.Task] = None
        self._last_log_time = time.time()
        self._log_interval = 5  # Log summary every 5 seconds
        
    async def connect_to_cv_module(self):
        """Establish connection to CV module."""
        if self._cv_connection_task and not self._cv_connection_task.done():
            return

        ws_url = settings.WS_URL
        retry_delay = INITIAL_RETRY_DELAY
        
        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    logger.info(f"[WS] Reconnecting to CV module (attempt {attempt + 1}/{MAX_RETRIES})")
                else:
                    logger.info("[WS] Connecting to CV module")
                    
                self.cv_connection = await websockets.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5
                )
                logger.info("[WS] Connected to CV module successfully")
                
                # Subscribe to images
                await self.cv_connection.send(json.dumps({"subscribe_images": True}))
                
                # Start listening for messages in a separate task
                self._cv_connection_task = asyncio.create_task(
                    self._listen_to_cv_module(),
                    name="cv_module_listener"
                )
                return
                
            except ConnectionRefusedError:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
            except Exception as e:
                logger.error(f"[WS] Connection error: {str(e)}")
                if attempt >= MAX_RETRIES - 1:
                    raise

    async def _listen_to_cv_module(self):
        """Listen for messages from CV module."""
        detection_count = 0
        last_summary_time = time.time()
        
        try:
            while True:
                if not self.cv_connection:
                    break
                    
                try:
                    data = await self.cv_connection.recv()
                    message = json.loads(data)
                    
                    # Process detection events
                    if "detection" in message:
                        detection_count += 1
                        detection = message["detection"]
                        
                        # Log summary every 5 seconds
                        current_time = time.time()
                        if current_time - last_summary_time >= self._log_interval:
                            logger.info(
                                f"[WS] Detection Summary: {detection_count} events in last {self._log_interval}s | "
                                f"Last detection: {detection['count']} person(s) "
                                f"(conf: {max(detection['confidence']):.2f})"
                            )
                            detection_count = 0
                            last_summary_time = current_time
                        else:
                            logger.debug(
                                f"[WS] Detection: {detection['count']} person(s) "
                                f"(conf: {max(detection['confidence']):.2f})"
                            )
                    
                    # Broadcast to all connected clients
                    await self.broadcast(message)
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("[WS] CV module connection closed")
                    break
                    
        except Exception as e:
            logger.error(f"[WS] Listener error: {str(e)}")
        finally:
            logger.info("[WS] Reconnecting to CV module...")
            self.cv_connection = None
            self._cv_connection_task = None
            await asyncio.sleep(INITIAL_RETRY_DELAY)
            asyncio.create_task(self.connect_to_cv_module())

    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new client."""
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"Failed to accept connection from {client_id}: {e}")
            raise
        
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            self.active_connections.pop(client_id)
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
        
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        if self.active_connections:
            logger.debug(f"Broadcasting to {len(self.active_connections)} clients")
            for connection in self.active_connections.values():
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Broadcast error: {str(e)}")

# Create a single instance of ConnectionManager
connection_manager = ConnectionManager()

@router.on_event("startup")
async def startup_event():
    """Connect to CV module when the application starts."""
    logger.info("Initializing WebSocket connection to CV module")
    await connection_manager.connect_to_cv_module()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    session: Session = Depends(get_session)
):
    try:
        await connection_manager.connect(websocket, client_id)
        
        while True:
            try:
                # Wait for messages from the client
                data = await websocket.receive_text()
                # Handle client messages if needed
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected")
                break
                
    except Exception as e:
        logger.error(f"Error in websocket connection: {str(e)}")
    finally:
        connection_manager.disconnect(client_id)
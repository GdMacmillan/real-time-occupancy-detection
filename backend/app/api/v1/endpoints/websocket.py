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

router = APIRouter()
logger = get_logger("backend.websocket")
settings = get_settings()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.message_count = 0
        
    async def connect(self, websocket: WebSocket, client_id: str):
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
        self.message_count += 1
        logger.debug(f"Broadcasting message type: {message.get('type', 'unknown')}")
        for connection in self.active_connections.values():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message: {str(e)}")
                continue

# Create a dependency that returns the ConnectionManager instance
def get_connection_manager():
    """Dependency to get ConnectionManager instance."""
    return ConnectionManager()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    session: Session = Depends(get_session),
    manager: ConnectionManager = Depends(get_connection_manager)
):
    cv_ws: Optional[websockets.WebSocketClientProtocol] = None
    
    try:
        logger.info(f"New WebSocket connection request from client: {client_id}")
        await manager.connect(websocket, client_id)
        
        # Connect to CV service with retry
        ws_url = settings.WS_URL
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to CV service at {ws_url} (attempt {attempt + 1}/{max_retries})")
                cv_ws = await websockets.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5
                )
                logger.info("Successfully connected to CV service")
                break
            except (websockets.exceptions.InvalidURI, ValueError) as e:
                logger.error(f"Invalid WebSocket URL: {ws_url}", exc_info=True)
                raise
            except ConnectionRefusedError:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection refused, retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Failed to connect to CV service after all retries")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error connecting to CV service: {e}", exc_info=True)
                raise

        if cv_ws:
            try:
                logger.debug("Sending image subscription request")
                await cv_ws.send(json.dumps({"subscribe_images": True}))
                
                while True:
                    try:
                        logger.debug("Waiting for data from CV service...")
                        data = await cv_ws.recv()
                        logger.debug(f"Received data length: {len(data)}")
                        
                        message = json.loads(data)
                        logger.debug(f"Parsed message type: {message.get('type', 'unknown')}")
                        
                        # Handle device status updates
                        if "device_status" in message:
                            logger.debug("Processing device status update")
                            device_info = message["device_status"]
                            device = session.exec(
                                select(Device).where(Device.device_id == device_info["device_id"])
                            ).first()
                            
                            if not device:
                                logger.info(f"New device registered: {device_info['device_id']}")
                                device = Device(
                                    device_id=device_info["device_id"],
                                    name=device_info.get("name", f"Camera {device_info['device_id']}"),
                                    type=device_info["type"]
                                )
                            
                            device.is_online = True
                            device.last_seen = datetime.utcnow()
                            session.add(device)
                            
                            # Handle scene image
                            if "image" in message:
                                logger.debug(f"Saving scene image for device {device.device_id}")
                                img_data = base64.b64decode(message["image"])
                                img_path = f"images/{device.device_id}_latest.jpg"
                                os.makedirs("images", exist_ok=True)
                                
                                with open(img_path, "wb") as f:
                                    f.write(img_data)
                                device.latest_image_path = img_path
                            
                            session.commit()
                        
                        # Handle detection events
                        if "detection" in message:
                            logger.debug("Processing detection event")
                            detection = Detection(**message["detection"])
                            session.add(detection)
                            session.commit()
                            
                            if device and device.alert_enabled and detection.detected:
                                logger.info(
                                    f"Alert: Detection on device {device.name} "
                                    f"(confidence: {detection.confidence})"
                                )
                                await manager.broadcast({
                                    "type": "alert",
                                    "device_id": device.device_id,
                                    "device_name": device.name,
                                    "detection": message["detection"]
                                })
                        
                        await websocket.send_json(message)
                        
                    except websockets.exceptions.ConnectionClosed:
                        logger.error("CV service connection closed unexpectedly")
                        break
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Unexpected error processing message: {e}", exc_info=True)
                        continue
                        
            finally:
                if not cv_ws.closed:
                    await cv_ws.close()
                    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Error in websocket connection: {e}", exc_info=True)
    finally:
        manager.disconnect(client_id)
        if cv_ws and not cv_ws.closed:
            await cv_ws.close()
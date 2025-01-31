import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Optional, Set, Dict

import websockets
import cv2
import base64


class DetectionServer:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        max_clients: int = 5,
        message_queue_size: int = 100,
        ping_interval: int = 30,
        ping_timeout: int = 10,
    ):
        """Websocket server for broadcasting detection events."""
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.message_queue_size = message_queue_size
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.clients: Dict[websockets.WebSocketServerProtocol, dict] = {}  # Store client preferences
        self.running = False
        self.server: Optional[websockets.WebSocketServer] = None

    async def register(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new client connection."""
        if len(self.clients) >= self.max_clients:
            logging.warning(
                f"Max clients ({self.max_clients}) reached. Rejecting new connection."
            )
            await websocket.close(
                1013, "Maximum number of clients reached"
            )  # 1013 = Try Again Later
            return

        self.clients[websocket] = {"subscribe_images": False}  # Default preferences
        logging.info(
            f"Client connected. Total clients: {len(self.clients)}/{self.max_clients}"
        )

    async def unregister(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister a client connection."""
        if websocket in self.clients:
            del self.clients[websocket]
        logging.info(
            f"Client disconnected. Total clients: {len(self.clients)}/{self.max_clients}"
        )

    async def broadcast_detection(self, detection_result, stats):
        """Broadcast detection results to all connected clients."""
        if not self.clients:
            return

        for websocket, preferences in self.clients.items():
            try:
                # Create message payload
                message = {
                    "timestamp": datetime.now().isoformat(),
                    "detection": {
                        **asdict(detection_result),
                        "timestamp": datetime.fromtimestamp(
                            detection_result.timestamp
                        ).isoformat(),
                    },
                    "stats": asdict(stats),
                }

                # Include image data if client subscribed
                if preferences.get("subscribe_images") and detection_result.visualization_data:
                    frame = detection_result.visualization_data["frame"]
                    # Encode frame as base64 JPEG
                    _, buffer = cv2.imencode('.jpg', frame)
                    img_base64 = base64.b64encode(buffer).decode('utf-8')
                    message["image"] = img_base64

                await websocket.send(json.dumps(message))
            except Exception as e:
                logging.error(f"Failed to send message to client: {e}")
                continue

    async def handler(self, websocket: websockets.WebSocketServerProtocol):
        """Handle client connection."""
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Handle image subscription
                    if "subscribe_images" in data:
                        self.clients[websocket]["subscribe_images"] = bool(data["subscribe_images"])
                        logging.info(f"Client image subscription set to: {data['subscribe_images']}")
                except json.JSONDecodeError:
                    logging.warning(f"Received invalid JSON message: {message}")
                except Exception as e:
                    logging.error(f"Error handling message: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def start(self):
        """Start the WebSocket server."""
        self.server = await websockets.serve(
            self.handler,
            self.host,
            self.port,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout,
            max_size=self.message_queue_size,
        )
        self.running = True
        logging.info(
            f"WebSocket server started on ws://{self.host}:{self.port} "
            f"(max clients: {self.max_clients})"
        )

    async def stop(self):
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.running = False
            logging.info("WebSocket server stopped")

    async def get_status(self):
        """Get server status information."""
        return {
            "running": self.running,
            "client_count": len(self.clients),
            "max_clients": self.max_clients,
            "host": self.host,
            "port": self.port,
        }
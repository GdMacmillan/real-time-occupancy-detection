import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .camera import CameraDevice, RealSenseCamera, WebCamera
from .config import ConfigLoader, ServiceConfig
from .detector import PersonDetector, YOLODetector
from .websocket_server import DetectionServer
from .visualization import DebugVisualizer, VisualizationConfig


class DetectionService:
    def __init__(self, config: ServiceConfig):
        """Class for detection service. Used for orchestrating camera, detector, and websocket components."""
        # Initialize logging
        self.log_dir = config.log_dir
        self.log_dir.mkdir(
            parents=True, exist_ok=True
        )  # Create parent directories if they don't exist
        self._setup_logging()

        # Initialize components
        self.camera = self._create_camera(config.camera)
        self.detector = self._create_detector(config.detector)
        self.server = DetectionServer(
            host=config.host,
            port=config.port,
            max_clients=config.websocket.max_clients,
            message_queue_size=config.websocket.message_queue_size,
            ping_interval=config.websocket.ping_interval,
            ping_timeout=config.websocket.ping_timeout,
        )

        # Initialize visualization if enabled
        self.visualizer = None
        if config.service.get("visualization", {}).get("enabled", False):
            vis_config = VisualizationConfig(**config.service["visualization"])
            self.visualizer = DebugVisualizer(vis_config)

        # Service state
        self.running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def _create_camera(self, camera_config) -> CameraDevice:
        """Create camera instance based on configuration."""
        camera_type = camera_config.type.lower()
        if camera_type == "webcam":
            return WebCamera(**camera_config.params)
        elif camera_type == "realsense":
            return RealSenseCamera(**camera_config.params)
        else:
            raise ValueError(f"Unsupported camera type: {camera_type}")

    def _create_detector(self, detector_config) -> PersonDetector:
        """Create detector instance based on configuration."""
        detector_type = detector_config.type.lower()
        if detector_type == "yolo":
            return YOLODetector(
                model_path=detector_config.model["name"],
                confidence_threshold=detector_config.model["confidence_threshold"],
            )
        else:
            raise ValueError(f"Unsupported detector type: {detector_type}")

    def _setup_logging(self):
        """Configure logging for the service."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"detection_service_{timestamp}.log"

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        )

    async def process_frames(self):
        """Run frame processing loop."""
        while self.running:
            # Get frame from camera
            frame = self.camera.get_frame()
            if frame is None:
                logging.warning("Failed to get frame from camera")
                await asyncio.sleep(0.1)
                continue

            # Run detection
            detection = self.detector.detect(frame.frame)
            stats = self.detector.get_stats()

            # Update visualization if enabled
            if self.visualizer and detection.visualization_data:
                vis_data = detection.visualization_data
                self.visualizer.draw_detections(
                    vis_data["frame"],
                    vis_data["boxes"],
                    detection.confidence,
                    detection.fps
                )

            # Broadcast results
            await self.server.broadcast_detection(detection, stats)

            # Optional: Add small delay to prevent CPU overload
            await asyncio.sleep(0.001)

    async def start(self):
        """Start all components and begin processing."""
        logging.info("Starting Detection Service")

        # Start camera
        if not self.camera.start():
            logging.error("Failed to start camera")
            return False

        # Start websocket server
        await self.server.start()

        # Set running state and start processing
        self.running = True
        logging.info("Service started successfully")
        return True

    async def stop(self):
        """Stop all components gracefully."""
        logging.info("Stopping Detection Service")
        self.running = False

        # Close visualization
        if self.visualizer:
            self.visualizer.close()

        # Stop components
        self.camera.stop()
        await self.server.stop()

        logging.info("Service stopped successfully")

    def handle_signal(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        logging.info(f"Received signal {signum}")
        if self.loop is not None:
            self.loop.create_task(self.stop())


def main():
    """Entry point for running the service."""
    try:
        # Initialize configuration
        config_loader = ConfigLoader(Path("cv_module/config"))
        config = config_loader.load_config()

        # Create and start service
        service = DetectionService(config)

        # Set up signal handlers
        signal.signal(signal.SIGINT, service.handle_signal)
        signal.signal(signal.SIGTERM, service.handle_signal)

        # Get event loop
        loop = asyncio.get_event_loop()
        service.loop = loop

        # Start service and run processing loop
        loop.run_until_complete(service.start())
        if service.running:
            loop.run_until_complete(service.process_frames())
    except Exception as e:
        logging.error(f"Failed to start service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
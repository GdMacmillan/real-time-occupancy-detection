import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

import cv2
import numpy as np


@dataclass
class Resolution:
    width: int
    height: int

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "Resolution":
        return cls(width=data["width"], height=data["height"])


@dataclass
class CameraFrame:
    """Data class for camera frame information."""

    frame: np.ndarray
    timestamp: float
    frame_number: int
    resolution: Resolution
    fps: float
    color_frame: Optional[np.ndarray] = None
    depth_frame: Optional[np.ndarray] = None
    camera_info: dict = None


class FrameRateLimiter:
    def __init__(self, target_fps: float):
        """Class designed to cap the frames generated per second."""
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.last_frame_time = 0
        self.actual_fps = 0
        self.fps_update_time = 0
        self.frame_count = 0

    def wait(self) -> float:
        """Wait for next frame interval and return actual FPS."""
        current_time = time.monotonic()

        # Calculate time to wait
        elapsed = current_time - self.last_frame_time
        if elapsed < self.frame_interval:
            time.sleep(self.frame_interval - elapsed)

        # Update FPS calculation
        self.frame_count += 1
        if current_time - self.fps_update_time >= 1.0:
            self.actual_fps = self.frame_count / (current_time - self.fps_update_time)
            self.fps_update_time = current_time
            self.frame_count = 0

        self.last_frame_time = time.monotonic()
        return self.actual_fps


class CameraDevice(ABC):
    def __init__(self, resolution: Optional[Dict[str, int]] = None, fps: float = 30.0):
        """Abstract base class for camera devices."""
        self.is_running = False
        self.frame_count = 0
        self.resolution = (
            Resolution.from_dict(resolution) if resolution else Resolution(640, 480)
        )
        self.fps = fps
        self.frame_limiter = FrameRateLimiter(fps)

    @abstractmethod
    def start(self) -> bool:
        """Initialize and start the camera."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop and release the camera."""
        pass

    @abstractmethod
    def get_frame(self) -> Optional[CameraFrame]:
        """Get the next frame from the camera."""
        pass


class WebCamera(CameraDevice):

    def __init__(
        self,
        camera_id: int = 0,
        resolution: Optional[Dict[str, int]] = None,
        fps: float = 30.0,
    ):
        """Class designed to read from generic webcams."""
        super().__init__(resolution, fps)
        self.camera_id = camera_id
        self.capture = None

    def start(self) -> bool:
        self.capture = cv2.VideoCapture(self.camera_id)
        if not self.capture.isOpened():
            return False

        # Set resolution
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution.height)

        # Try to set FPS (may not be supported by all cameras)
        self.capture.set(cv2.CAP_PROP_FPS, self.fps)

        # Verify actual resolution and FPS
        actual_width = self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        actual_fps = self.capture.get(cv2.CAP_PROP_FPS)

        if (
            actual_width != self.resolution.width
            or actual_height != self.resolution.height
        ):
            print(
                f"Warning: Requested resolution {self.resolution.width}x{self.resolution.height} "
                f"not supported. Using {actual_width}x{actual_height}"
            )
            self.resolution = Resolution(int(actual_width), int(actual_height))

        if actual_fps != self.fps:
            print(
                f"Warning: Requested FPS {self.fps} not supported by camera. "
                f"Hardware reports {actual_fps} FPS. Using software FPS limiting."
            )

        self.is_running = True
        return True

    def stop(self) -> None:
        if self.capture:
            self.capture.release()
        self.is_running = False

    def get_frame(self) -> Optional[CameraFrame]:
        if not self.is_running:
            return None

        # Limit frame rate
        actual_fps = self.frame_limiter.wait()

        ret, frame = self.capture.read()
        if not ret:
            return None

        # Resize frame if it doesn't match the requested resolution
        if (frame.shape[1], frame.shape[0]) != (
            self.resolution.width,
            self.resolution.height,
        ):
            frame = cv2.resize(frame, (self.resolution.width, self.resolution.height))

        self.frame_count += 1
        return CameraFrame(
            frame=frame,
            timestamp=time.monotonic(),
            frame_number=self.frame_count,
            resolution=self.resolution,
            fps=actual_fps,
        )


class RealSenseCamera(CameraDevice):
    def __init__(
        self,
        resolution: Optional[Dict[str, int]] = None,
        fps: float = 30.0,
        enable_infrared: bool = False,
        align_depth: bool = True,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs,  # Accept and ignore any additional parameters
    ):
        """Intel RealSense camera implementation."""
        super().__init__(resolution, fps)
        try:
            import pyrealsense2 as rs

            self.pipeline = rs.pipeline()
            self.config = rs.config()
            self.enable_infrared = enable_infrared
            self.align_depth = align_depth
            self.filters = filters or {}

            # Create align object if depth alignment is requested
            self.align = rs.align(rs.stream.color) if align_depth else None

            # Initialize filter objects if requested
            self.rs_filters = {}
            if self.filters:
                self._setup_filters(rs)

        except ImportError as e:
            logging.error("Failed to import pyrealsense2. Is it installed correctly?")
            raise ImportError(
                "pyrealsense2 is required for RealSense camera support"
            ) from e

    def _setup_filters(self, rs):
        """Set up RealSense post-processing filters."""
        if self.filters.get("decimation"):
            self.rs_filters["decimation"] = rs.decimation_filter()
            self.rs_filters["decimation"].set_option(
                rs.option.filter_magnitude, self.filters["decimation"]
            )
        if self.filters.get("spatial"):
            self.rs_filters["spatial"] = rs.spatial_filter()
        if self.filters.get("temporal"):
            self.rs_filters["temporal"] = rs.temporal_filter()
        if self.filters.get("hole_filling"):
            self.rs_filters["hole_filling"] = rs.hole_filling_filter()

    def start(self) -> bool:
        try:
            import pyrealsense2 as rs

            # Configure streams
            self.config.enable_stream(
                rs.stream.color,
                self.resolution.width,
                self.resolution.height,
                rs.format.bgr8,
                self.fps,
            )

            self.config.enable_stream(
                rs.stream.depth,
                self.resolution.width,
                self.resolution.height,
                rs.format.z16,
                self.fps,
            )

            if self.enable_infrared:
                self.config.enable_stream(
                    rs.stream.infrared,
                    self.resolution.width,
                    self.resolution.height,
                    rs.format.y8,
                    self.fps,
                )

            try:
                # Start streaming
                self.pipeline.start(self.config)
                self.is_running = True
                logging.info("RealSense camera started successfully")
                return True
            except RuntimeError as e:
                logging.error(f"Failed to start RealSense camera: {e}")
                logging.error("Is the camera connected properly?")
                return False

        except Exception as e:
            logging.error(f"Error starting RealSense camera: {e}")
            return False

    def stop(self) -> None:
        if self.is_running:
            self.pipeline.stop()
        self.is_running = False

    def get_frame(self) -> Optional[CameraFrame]:
        if not self.is_running:
            return None

        try:
            # Limit frame rate
            actual_fps = self.frame_limiter.wait()

            # Wait for frames
            frames = self.pipeline.wait_for_frames()

            # Align frames if requested
            if self.align:
                frames = self.align.process(frames)

            # Get color and depth frames
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()

            # Apply filters to depth frame if configured
            if self.filters and depth_frame:
                for filter_name, filter_obj in self.rs_filters.items():
                    depth_frame = filter_obj.process(depth_frame)

            if not depth_frame or not color_frame:
                return None

            self.frame_count += 1
            return CameraFrame(
                frame=np.asanyarray(color_frame.get_data()),
                depth_frame=np.asanyarray(depth_frame.get_data()),
                timestamp=time.monotonic(),
                frame_number=self.frame_count,
                resolution=self.resolution,
                fps=actual_fps,
            )

        except Exception as e:
            logging.error(f"Error getting RealSense frame: {e}")
            return None

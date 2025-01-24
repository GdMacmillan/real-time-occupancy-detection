import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, List, Optional

import numpy as np
from ultralytics import YOLO


@dataclass
class DetectionResult:
    """Data class for detection results."""

    detected: bool
    count: int
    confidence: List[float]
    frame_number: int
    timestamp: float
    fps: float = 0.0
    visualization_data: Optional[Any] = None

    def __post_init__(self):
        """Set timestamp of detection result after data class init."""
        if not self.timestamp:
            self.timestamp = time.monotonic()


@dataclass
class PerformanceStats:
    """Data class for performance monitoring."""

    avg_fps: float
    min_fps: float
    max_fps: float
    total_detections: int
    total_frames: int
    uptime: float
    start_time: float


class PersonDetector(ABC):
    def __init__(self, confidence_threshold: float = 0.5, summary_interval: int = 30):
        """Abstract base class for person detection."""
        self.confidence_threshold = confidence_threshold
        self.fps_history: List[float] = []
        self.detection_history: List[DetectionResult] = []
        self.start_time = time.monotonic()
        self.last_summary_time = self.start_time
        self.summary_interval = summary_interval

    @abstractmethod
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Detect persons in the frame."""
        pass

    def get_stats(self) -> PerformanceStats:
        current_time = time.monotonic()
        if not self.fps_history:
            return PerformanceStats.empty(start_time=self.start_time)

        return PerformanceStats(
            avg_fps=float(np.mean(self.fps_history)),
            min_fps=float(np.min(self.fps_history)),
            max_fps=float(np.max(self.fps_history)),
            total_detections=sum(1 for d in self.detection_history if d.detected),
            total_frames=len(self.detection_history),
            uptime=current_time - self.start_time,
            start_time=self.start_time,
        )

    def _log_summary(self) -> None:
        """Log summary of detection activity."""
        current_time = time.monotonic()
        if current_time - self.last_summary_time >= self.summary_interval:
            elapsed_time = current_time - self.start_time
            recent_detections = [
                d
                for d in self.detection_history
                if (current_time - d.timestamp) <= self.summary_interval
            ]

            avg_fps = np.mean(self.fps_history[-100:]) if self.fps_history else 0
            detection_rate = (
                len([d for d in recent_detections if d.detected])
                / len(recent_detections)
                if recent_detections
                else 0
            )

            logging.info(
                f"Detection Summary (last {self.summary_interval}s) - "
                f"Uptime: {timedelta(seconds=int(elapsed_time))} | "
                f"FPS: {avg_fps:.1f} | "
                f"Detection Rate: {detection_rate:.1%} | "
                f"Total Frames: {len(self.detection_history)}"
            )

            self.last_summary_time = current_time


class YOLODetector(PersonDetector):

    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        summary_interval: int = 30,
        verbose: bool = False,
    ):
        """Ultralytics-based Yolo detector class implementation."""
        super().__init__(confidence_threshold, summary_interval)
        self.model = YOLO(model_path)
        self.verbose = verbose

    def detect(self, frame: np.ndarray) -> DetectionResult:
        start_time = time.monotonic()

        # Use configured verbose setting
        results = self.model(frame, verbose=self.verbose)
        persons = [
            box
            for box in results[0].boxes
            if box.cls == 0 and box.conf > self.confidence_threshold
        ]

        fps = 1.0 / (time.monotonic() - start_time)
        self.fps_history.append(fps)

        detection = DetectionResult(
            detected=len(persons) > 0,
            count=len(persons),
            confidence=[float(box.conf) for box in persons],
            frame_number=len(self.detection_history) + 1,
            timestamp=time.monotonic(),
            fps=fps,
            visualization_data=results[0],
        )

        self.detection_history.append(detection)

        # Log periodic summary
        self._log_summary()

        return detection

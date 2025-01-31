import cv2
import numpy as np
from typing import List, Optional, Any
from dataclasses import dataclass
import time

@dataclass
class VisualizationConfig:
    enabled: bool = True
    window_name: str = "CV Module Debug View"
    draw_confidence: bool = True
    draw_fps: bool = True
    scale: float = 1.0

class DebugVisualizer:
    """Debug visualization component for CV module."""
    
    def __init__(self, config: VisualizationConfig):
        self.config = config
        self.window_name = config.window_name
        if config.enabled:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            
    def draw_detections(self, frame: np.ndarray, boxes: List[Any], 
                       confidences: List[float], fps: float) -> np.ndarray:
        """Draw detection boxes, confidence scores and FPS on frame.
        
        Args:
            frame: Input frame to draw on
            boxes: List of detection boxes from YOLO
            confidences: List of confidence scores for each detection
            fps: Current frames per second
            
        Returns:
            Frame with visualizations drawn
        """
        if not self.config.enabled:
            return frame
            
        vis_frame = frame.copy()
        
        # Draw detection boxes and confidence scores
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = confidences[i]
            
            # Draw bounding box
            cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw confidence score
            if self.config.draw_confidence:
                conf_text = f"{conf:.2f}"
                cv2.putText(vis_frame, conf_text, (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw FPS
        if self.config.draw_fps:
            fps_text = f"FPS: {fps:.1f}"
            cv2.putText(vis_frame, fps_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Scale frame if needed
        if self.config.scale != 1.0:
            height, width = vis_frame.shape[:2]
            new_size = (int(width * self.config.scale), 
                       int(height * self.config.scale))
            vis_frame = cv2.resize(vis_frame, new_size)
            
        # Display frame
        cv2.imshow(self.window_name, vis_frame)
        cv2.waitKey(1)  # Required for display update
        
        return vis_frame
        
    def close(self):
        """Close visualization windows."""
        if self.config.enabled:
            cv2.destroyWindow(self.window_name) 
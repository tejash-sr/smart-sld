"""Line and connection detection for SLD graphs."""
from __future__ import annotations
import cv2
import numpy as np
from typing import NamedTuple

class DetectedLine(NamedTuple):
    x1: int; y1: int; x2: int; y2: int
    angle: float
    length: float
    layer: str = "default"

class LineDetector:
    """Detect electrical connection lines using morphological ops + Hough transform.

    Optimized for thin-line SLD drawings. Busbars appear as thick horizontal/vertical
    rectangles; feeder wires are thinner diagonal or orthogonal lines.
    """

    def __init__(
        self,
        min_line_length: int = 30,
        max_line_gap: int = 10,
        canny_low: int = 50,
        canny_high: int = 150,
        hough_threshold: int = 50,
        busbar_thickness: int = 8,
    ):
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.hough_threshold = hough_threshold
        self.busbar_thickness = busbar_thickness

    def detect_lines(self, binary_image: np.ndarray) -> list[DetectedLine]:
        """Detect lines from binary image. Returns oriented line segments."""
        edges = cv2.Canny(
            binary_image, self.canny_low, self.canny_high, apertureSize=3
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=1)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap,
        )
        if lines is None:
            return []
        result = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.hypot(x2 - x1, y2 - y1)
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            result.append(DetectedLine(x1, y1, x2, y2, angle, length))
        return result

    def detect_busbars(self, binary_image: np.ndarray) -> list[dict]:
        """Detect horizontal thick lines that are busbars."""
        horizontal_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (self.busbar_thickness * 5, self.busbar_thickness)
        )
        extracted = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, horizontal_kernel)
        contours, _ = cv2.findContours(
            extracted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        busbars = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / max(h, 1)
            if aspect > 3 and w > 100:
                busbars.append({"x": x, "y": y, "width": w, "height": h})
        return busbars

    def snap_to_grid(self, value: float, grid_size: int = 10) -> float:
        return round(value / grid_size) * grid_size

    def snap_endpoint_to_nearest_component(
        self,
        point: tuple[int, int],
        components: list[dict],
        snap_radius: int = 20,
    ) -> tuple[int, int] | None:
        """Given a line endpoint, snap to nearest component if within radius."""
        px, py = point
        best = None
        best_dist = snap_radius
        for comp in components:
            cx = comp["bbox"]["x_min"] + comp["bbox"]["width"] / 2
            cy = comp["bbox"]["y_min"] + comp["bbox"]["height"] / 2
            dist = np.hypot(cx - px, cy - py)
            if dist < best_dist:
                best_dist = dist
                best = (int(cx), int(cy))
        return best

    def build_connections(
        self,
        lines: list[DetectedLine],
        components: list[dict],
        snap_radius: int = 20,
    ) -> list[dict]:
        """Infer connections from line endpoints to component connection points."""
        connections = []
        for line in lines:
            start_snap = self.snap_endpoint_to_nearest_component(
                (line.x1, line.y1), components, snap_radius
            )
            end_snap = self.snap_endpoint_to_nearest_component(
                (line.x2, line.y2), components, snap_radius
            )
            if start_snap and end_snap and start_snap != end_snap:
                connections.append({
                    "from": start_snap,
                    "to": end_snap,
                    "type": "wired",
                    "angle": line.angle,
                })
        return connections
